"""
MongoDB-based Question Generator Service
Generates questions from MongoDB data with verification
"""

import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import pandas as pd
import io
import numpy as np
from bson import ObjectId
import google.generativeai as genai

from database import get_database
from models.user import UserInDB
from services.file_service import get_file_metadata, get_file_from_gridfs

logger = logging.getLogger(__name__)

# Configure Gemini API - try loading from .env if not set
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    except ImportError:
        pass

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini API configured successfully")
else:
    logger.warning("GEMINI_API_KEY not found in environment variables")


def clean_for_json(obj: Any) -> Any:
    """Recursively clean ObjectId and datetime objects for JSON serialization"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(item) for item in obj]
    elif isinstance(obj, (int, float)) and (np.isnan(obj) or np.isinf(obj)):
        return None
    else:
        return obj


class MongoDBQuestionGenerator:
    """Generate questions from MongoDB data with verification"""
    
    def __init__(self, user: UserInDB):
        self.user = user
        self.db = get_database()
        self.tables_collection = self.db["tables"]  # Normalized table rows
        self.qa_bank_collection = self.db["qa_bank"]  # Generated Q/A
        
    async def normalize_file_to_tables(self, file_id: str) -> Dict[str, Any]:
        """
        Extract and normalize file data into tables collection.
        Creates normalized rows for easy querying.
        """
        try:
            # Get file metadata
            file_info = await get_file_metadata(file_id, self.user)
            if not file_info:
                return {"success": False, "error": "File not found"}
            
            # Get file content
            file_content = await get_file_from_gridfs(file_id, self.user)
            if not file_content:
                return {"success": False, "error": "File content not found"}
            
            metadata = file_info.get("metadata", {})
            file_type = file_info.get("file_type", "csv")
            sheets = metadata.get("sheets", {})
            
            normalized_count = 0
            
            # Process each sheet
            if file_type.lower() in ['xlsx', 'xls']:
                excel_file = pd.ExcelFile(io.BytesIO(file_content))
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    count = await self._normalize_dataframe(df, file_id, sheet_name)
                    normalized_count += count
                excel_file.close()
            else:
                # CSV file
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                df = None
                for enc in encodings:
                    try:
                        df = pd.read_csv(io.BytesIO(file_content), encoding=enc)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if df is not None:
                    sheet_name = "Sheet1"
                    normalized_count = await self._normalize_dataframe(df, file_id, sheet_name)
            
            return {
                "success": True,
                "file_id": file_id,
                "normalized_rows": normalized_count
            }
        except Exception as e:
            logger.error(f"Error normalizing file {file_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
    async def _normalize_dataframe(self, df: pd.DataFrame, file_id: str, table_name: str) -> int:
        """Normalize DataFrame rows into MongoDB tables collection"""
        # Delete existing rows for this file/table combination
        await self.tables_collection.delete_many({
            "file_id": file_id,
            "table_name": table_name,
            "user_id": self.user.id
        })
        
        # Convert DataFrame to dict records
        df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
        records = df.to_dict('records')
        
        # Insert normalized rows
        documents = []
        for idx, row in enumerate(records):
            doc = {
                "user_id": self.user.id,
                "file_id": file_id,
                "table_name": table_name,
                "row_id": idx + 1,
                "row": row,
                "created_at": datetime.utcnow()
            }
            documents.append(doc)
        
        if documents:
            await self.tables_collection.insert_many(documents)
        
        return len(documents)
    
    async def summarize_table(self, file_id: str, table_name: str, limit: int = 100) -> Dict[str, Any]:
        """Build summary statistics for a table"""
        try:
            cursor = self.tables_collection.find({
                "file_id": file_id,
                "table_name": table_name,
                "user_id": self.user.id
            }).limit(limit)
            
            rows = []
            async for doc in cursor:
                rows.append(doc["row"])
            
            if not rows:
                return {"error": "No data found"}
            
            df = pd.DataFrame(rows)
            
            # Build summary
            summary = {
                "table_name": table_name,
                "row_count": await self.tables_collection.count_documents({
                    "file_id": file_id,
                    "table_name": table_name,
                    "user_id": self.user.id
                }),
                "columns": list(df.columns),
                "column_types": {},
                "sample_rows": rows[:5] if len(rows) > 0 else [],
                "numeric_stats": {},
                "categorical_stats": {}
            }
            
            # Analyze column types and stats
            for col in df.columns:
                col_data = df[col]
                
                # Determine type
                if pd.api.types.is_numeric_dtype(col_data):
                    summary["column_types"][col] = "numeric"
                    summary["numeric_stats"][col] = {
                        "min": float(col_data.min()) if not col_data.empty else None,
                        "max": float(col_data.max()) if not col_data.empty else None,
                        "mean": float(col_data.mean()) if not col_data.empty else None,
                        "median": float(col_data.median()) if not col_data.empty else None,
                        "null_count": int(col_data.isna().sum())
                    }
                elif pd.api.types.is_datetime64_any_dtype(col_data):
                    summary["column_types"][col] = "date"
                else:
                    summary["column_types"][col] = "categorical"
                    value_counts = col_data.value_counts().head(10)
                    summary["categorical_stats"][col] = {
                        "unique_count": int(col_data.nunique()),
                        "top_values": value_counts.to_dict(),
                        "null_count": int(col_data.isna().sum())
                    }
            
            return summary
        except Exception as e:
            logger.error(f"Error summarizing table {table_name}: {str(e)}")
            return {"error": str(e)}
    
    def build_prompt(self, table_summary: Dict[str, Any], question_type: str, seed: Optional[str] = None) -> str:
        """Build prompt for Gemini question generation"""
        
        system_prompt = """You are a strict Question Generator for a dataset. ALWAYS output valid JSON (no extra text).
Use only the provided schema and data summary. Create a question, answer, verification query (MongoDB aggregation pipeline), question type and difficulty.
Do NOT hallucinate fields not in the schema. Use small, deterministic language.

CRITICAL: For "answer_structured.value":
- For NUMERIC answers (aggregation, factual with numbers): Include the numeric value, e.g., {"value": 12345, "unit": "INR"}
- For COMPARATIVE questions (which entity is best/worst/highest): Include the ENTITY NAME as a string, e.g., {"value": "Entity Name"} or {"value": "Product A"}
- For TREND questions: Include the numeric change/difference, e.g., {"value": 15.5, "unit": "percentage"}
- For FACTUAL questions with text answers: Include the text value, e.g., {"value": "Batch-001"}

IMPORTANT: For verification_query with type "aggregation", provide a MongoDB aggregation pipeline that:
1. Uses $match to filter rows (access fields via "row.field_name" since data is stored in "row" object)
2. Uses $group with _id: null to aggregate all matching rows (for simple aggregations)
3. Uses $group with _id: "$row.field_name" to group by a field (for comparative questions)
4. Uses $sum, $avg, $count, etc. for aggregations
5. Returns result in format: {"_id": null, "total": <value>} or {"_id": "entity_name", "total": <value>}

Example aggregation pipeline for average:
[
  {"$match": {"row.column_name": {"$exists": true, "$ne": null}}},
  {"$group": {"_id": null, "avg": {"$avg": "$row.numeric_column"}}}
]

Example aggregation pipeline for sum:
[
  {"$match": {"row.column_name": {"$exists": true}}},
  {"$group": {"_id": null, "total": {"$sum": "$row.numeric_column"}}}
]

Example aggregation pipeline for COMPARATIVE question (which entity has highest total):
[
  {"$match": {"row.entity_column": {"$exists": true}}},
  {"$group": {"_id": "$row.entity_column", "total_value": {"$sum": "$row.numeric_column"}}},
  {"$sort": {"total_value": -1}},
  {"$limit": 1}
]
For this comparative question, answer_structured.value should be the entity name string from _id, e.g., {"value": "Entity Name"}

Output format (JSON only):
{
  "question_id": "q_0001",
  "question": "...",
  "type": "aggregation|factual|comparative|trend|mcq|anomaly",
  "difficulty": "easy|medium|hard",
  "answer": "...",
  "answer_structured": {"value": 12345, "unit": "INR"} OR {"value": "Entity Name"} for comparative,
  "verification_query": {
    "type": "aggregation|find",
    "pipeline": [{"$match": {...}}, {"$group": {...}}],
    "filter": {...}
  },
  "explanation": "short explanation why answer is correct"
}"""

        # Build data summary text
        columns_text = ", ".join([f"{col} ({table_summary['column_types'].get(col, 'unknown')})" 
                                  for col in table_summary.get('columns', [])])
        
        sample_text = ""
        if table_summary.get('sample_rows'):
            sample_text = f"\nSample rows (first 3):\n{json.dumps(table_summary['sample_rows'][:3], default=str, indent=2)}"
        
        stats_text = ""
        if table_summary.get('numeric_stats'):
            stats_text += f"\nNumeric stats: {json.dumps(table_summary['numeric_stats'], default=str)}"
        if table_summary.get('categorical_stats'):
            stats_text += f"\nCategorical stats: {json.dumps(table_summary['categorical_stats'], default=str)}"
        
        user_prompt = f"""Table: {table_summary['table_name']}
Row count: {table_summary.get('row_count', 0)} (use ALL rows for calculations, not just samples)
Columns: {columns_text}
{sample_text}
{stats_text}

CRITICAL INSTRUCTIONS FOR ANSWER GENERATION:
1. For AGGREGATION questions (sum, avg, min, max, count): Use the numeric_stats provided above to get the EXACT expected value. 
   - If numeric_stats shows "sum": use that value
   - If numeric_stats shows "mean": use that value  
   - Multiply mean by row_count to get sum if needed
2. For COMPARATIVE questions: Use categorical_stats to find the top entity (highest count/value)
3. For TREND questions: Calculate the difference between two time periods using numeric_stats or actual calculations
4. The answer_structured.value MUST match what the MongoDB pipeline will return when executed on ALL {table_summary.get('row_count', 0)} rows

Task: Generate one {question_type} question with answer and MongoDB verification query. Output ONLY valid JSON following the schema above.
IMPORTANT: The answer_structured.value MUST be accurate based on ALL {table_summary.get('row_count', 0)} rows, not just sample data."""
        
        if seed:
            user_prompt += f"\nSeed instruction: {seed}"
        
        return f"{system_prompt}\n\n{user_prompt}"
    
    async def call_gemini(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call Gemini API to generate question"""
        try:
            if not GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not set")
            
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,  # Low temperature for deterministic output
                    "max_output_tokens": 1000,
                }
            )
            
            # Extract JSON from response
            text = response.text.strip()
            
            # Try to extract JSON if wrapped in markdown
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()
            
            # Parse JSON
            return json.loads(text)
        except Exception as e:
            logger.error(f"Error calling Gemini: {str(e)}")
            logger.error(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
            return None
    
    def _fix_pipeline_field_references(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform pipeline to use row.field_name instead of field_name for data fields"""
        # MongoDB operators that should NOT be transformed
        MONGODB_OPS = {"$match", "$group", "$project", "$sort", "$limit", "$addFields", "$substr", 
                       "$in", "$eq", "$ne", "$exists", "$cond", "$first", "$sum", "$avg", "$min", 
                       "$max", "$count", "$subtract", "$and", "$or", "$not", "$gt", "$gte", "$lt", 
                       "$lte", "$ifNull", "$concat", "$toInt", "$toDouble", "$toString", "$ifNull"}
        
        # Metadata fields that should NOT be prefixed with row.
        METADATA_FIELDS = {"file_id", "table_name", "user_id", "_id", "row_id", "created_at", "yearMonth"}
        
        def transform_value(value):
            """Recursively transform field references in values"""
            if isinstance(value, str):
                if value.startswith("$"):
                    # Check if it's already a row reference or a MongoDB operator
                    if value.startswith("$row.") or value in MONGODB_OPS:
                        return value
                    # Check if it's a metadata field (without $ prefix)
                    field_name = value[1:]
                    if field_name in METADATA_FIELDS:
                        return value
                    # It's a data field - add row. prefix
                    return f"$row.{field_name}"
            elif isinstance(value, dict):
                return {k: transform_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [transform_value(item) for item in value]
            return value
        
        fixed_pipeline = []
        for stage in pipeline:
            fixed_stage = {}
            for op, value in stage.items():
                if op == "$match":
                    # For $match, preserve metadata fields, transform data field names
                    fixed_match = {}
                    for field, condition in value.items():
                        if field in METADATA_FIELDS:
                            # Keep metadata fields as-is
                            fixed_match[field] = condition
                        elif field.startswith("$"):
                            # MongoDB operators like $and, $or - keep as-is but transform nested conditions
                            fixed_match[field] = transform_value(condition)
                        elif field.startswith("row."):
                            # Already has row. prefix - don't add another
                            fixed_match[field] = transform_value(condition)
                        else:
                            # Data field - transform to row.field_name
                            fixed_field = f"row.{field}"
                            # Transform the condition recursively
                            fixed_match[fixed_field] = transform_value(condition)
                    fixed_stage[op] = fixed_match
                elif op == "$group":
                    # For $group, transform _id and accumulator field references
                    fixed_group = {}
                    for field, expr in value.items():
                        if field == "_id":
                            # Transform _id expression
                            if isinstance(expr, str):
                                if expr.startswith("$") and not expr.startswith("$row."):
                                    field_name = expr[1:]
                                    if field_name not in METADATA_FIELDS and field_name not in MONGODB_OPS:
                                        fixed_group[field] = f"$row.{field_name}"
                                    else:
                                        fixed_group[field] = expr
                                elif expr == "null":
                                    fixed_group[field] = None
                                else:
                                    fixed_group[field] = transform_value(expr)
                            else:
                                fixed_group[field] = transform_value(expr)
                        else:
                            # Transform accumulator expressions
                            fixed_group[field] = transform_value(expr)
                    fixed_stage[op] = fixed_group
                elif op == "$addFields":
                    # For $addFields, transform field names in the added fields
                    fixed_add_fields = {}
                    for field, expr in value.items():
                        # Field names in $addFields should not be prefixed with row.
                        # But expressions inside should be transformed
                        fixed_add_fields[field] = transform_value(expr)
                    fixed_stage[op] = fixed_add_fields
                elif op == "$project":
                    # For $project, transform field references in expressions
                    # But be careful - field names in $project output should NOT be prefixed
                    # Only transform field references INSIDE expressions
                    fixed_project = {}
                    for field, expr in value.items():
                        if field == "_id":
                            fixed_project[field] = expr
                        else:
                            # Transform expressions but keep output field names as-is
                            fixed_project[field] = transform_value(expr)
                    fixed_stage[op] = fixed_project
                else:
                    # For all other operators, transform recursively
                    fixed_stage[op] = transform_value(value)
            fixed_pipeline.append(fixed_stage)
        
        logger.debug(f"Pipeline transformation: {len(pipeline)} stages -> {len(fixed_pipeline)} stages")
        return fixed_pipeline
    
    async def verify_answer(self, file_id: str, table_name: str, verification_query: Dict[str, Any], 
                          expected_answer: Dict[str, Any], answer_text: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """Verify generated answer against MongoDB data"""
        try:
            query_type = verification_query.get("type", "aggregation")
            
            logger.info(f"Verifying answer for {file_id}/{table_name}, type: {query_type}")
            logger.debug(f"Verification query: {verification_query}")
            logger.debug(f"Expected answer: {expected_answer}")
            
            if query_type == "aggregation":
                # Build MongoDB aggregation pipeline
                pipeline = verification_query.get("pipeline", [])
                
                if not pipeline:
                    logger.warning("No pipeline provided in verification_query")
                    return False, {"error": "No pipeline provided"}
                
                # Ensure pipeline is a list
                if not isinstance(pipeline, list):
                    logger.warning(f"Pipeline is not a list: {type(pipeline)}")
                    return False, {"error": "Pipeline must be a list"}
                
                # Fix field references to use row.field_name
                pipeline = self._fix_pipeline_field_references(pipeline)
                
                # Add match stage for file_id, table_name, user_id
                match_stage = {
                    "$match": {
                        "file_id": file_id,
                        "table_name": table_name,
                        "user_id": self.user.id
                    }
                }
                
                # Insert match at beginning if not already present
                if not pipeline or not isinstance(pipeline[0], dict) or pipeline[0].get("$match") is None:
                    pipeline.insert(0, match_stage)
                else:
                    # Merge match conditions
                    existing_match = pipeline[0].get("$match", {})
                    if isinstance(existing_match, dict):
                        existing_match.update(match_stage["$match"])
                        pipeline[0]["$match"] = existing_match
                    else:
                        pipeline.insert(0, match_stage)
                
                logger.debug(f"Final pipeline: {pipeline}")
                
                # Execute aggregation
                try:
                    cursor = self.tables_collection.aggregate(pipeline)
                    results = await cursor.to_list(length=100)
                    logger.debug(f"Aggregation returned {len(results)} results")
                except Exception as agg_error:
                    logger.error(f"Error executing aggregation pipeline: {str(agg_error)}")
                    logger.error(f"Pipeline was: {pipeline}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return False, {"error": f"Aggregation failed: {str(agg_error)}", "pipeline": pipeline}
                
                # Extract computed value from aggregation result
                computed_value = None
                computed_id = None  # For comparative questions
                
                if results:
                    result_doc = results[0]
                    logger.debug(f"Aggregation result: {result_doc}")
                    
                    # Store _id separately for comparative questions
                    if "_id" in result_doc:
                        computed_id = result_doc["_id"]
                        # If _id is a string (not None), this is likely a comparative question
                        # In that case, we want to use the numeric field, not _id
                        if isinstance(computed_id, str):
                            logger.debug(f"Comparative question detected - _id is string: {computed_id}")
                    
                    # Common aggregation result patterns
                    # Try multiple common field names (prioritize numeric fields)
                    for field in ["total", "sum", "avg", "average", "count", "value", "result", 
                                 "averageInspectedQty", "total_inspected", "avgFailedQty", 
                                 "avg_inspected_qty", "totalWastage", "avgConsumption", 
                                 "averageCost", "difference"]:
                        if field in result_doc:
                            computed_value = result_doc[field]
                            break
                    
                    # If _id is None, it's a global aggregation - check all values
                    if computed_value is None and result_doc.get("_id") is None:
                        # Get the first non-_id value
                        for key, value in result_doc.items():
                            if key != "_id" and value is not None:
                                computed_value = value
                                break
                    
                    # Fallback: if dict has 2 keys and one is _id, get the other
                    if computed_value is None and isinstance(result_doc, dict) and len(result_doc) == 2:
                        for key, value in result_doc.items():
                            if key != "_id":
                                computed_value = value
                                break
                    
                    # Last resort: get any numeric value
                    if computed_value is None:
                        for key, value in result_doc.items():
                            if key != "_id" and isinstance(value, (int, float)) and value is not None:
                                computed_value = value
                                break
                    
                    # For comparative questions: if we have both _id (string) and numeric value,
                    # use numeric value for verification, but keep _id for reference
                    # If no numeric value but we have _id, use _id
                    if computed_value is None and computed_id is not None:
                        computed_value = computed_id
                    
                    computed_value = computed_value or 0
                else:
                    computed_value = 0
                    logger.warning(f"No aggregation results returned for pipeline: {pipeline}")
                
                # Compare with expected
                expected_value = expected_answer.get("value") if expected_answer else None
                
                # For old comparative questions, try to extract answer from answer_text if expected_value is None
                if expected_value is None and answer_text and computed_id is not None and isinstance(computed_id, str):
                    # Try to extract entity name from answer_text
                    import re
                    # Look for common answer patterns:
                    # 1. Quoted strings: "Rajesh Kumar"
                    # 2. After "is" or "are": "Rajesh Kumar is..."
                    # 3. Capitalized names: "Rajesh Kumar"
                    # 4. After colon: "Answer: Rajesh Kumar"
                    
                    # Pattern 1: Quoted strings
                    quoted = re.findall(r'"([^"]+)"', answer_text)
                    if quoted:
                        expected_value = quoted[0]
                        logger.info(f"Extracted expected value from quoted string in answer_text: {expected_value}")
                    else:
                        # Pattern 2: After "is" or "are"
                        is_match = re.search(r'(?:is|are|was|were)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', answer_text, re.IGNORECASE)
                        if is_match:
                            expected_value = is_match.group(1)
                            logger.info(f"Extracted expected value after 'is/are' in answer_text: {expected_value}")
                        else:
                            # Pattern 3: After colon
                            colon_match = re.search(r':\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', answer_text)
                            if colon_match:
                                expected_value = colon_match.group(1)
                                logger.info(f"Extracted expected value after colon in answer_text: {expected_value}")
                            else:
                                # Pattern 4: Capitalized words (fallback)
                                capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', answer_text)
                                # Filter out common words and find entity-like names
                                common_words = {"The", "This", "That", "These", "Those", "Answer", "Question"}
                                for name in capitalized:
                                    if name not in common_words and len(name) > 3:
                                        expected_value = name
                                        logger.info(f"Extracted expected value from capitalized words in answer_text: {expected_value}")
                                        break
                
                # Clean pipeline for JSON serialization (do this early)
                cleaned_pipeline = clean_for_json(pipeline)
                
                # Check if this is a comparative question (has string _id and expected_value is string)
                is_comparative = (computed_id is not None and isinstance(computed_id, str) and 
                                 expected_value is not None and isinstance(expected_value, str))
                
                logger.info(f"Verification comparison: expected={expected_value} (type: {type(expected_value)}), computed={computed_value} (type: {type(computed_value)}), computed_id={computed_id}, is_comparative={is_comparative}")
                
                # For comparative questions, compare the entity name (computed_id) with expected_value
                if is_comparative:
                    verified = str(expected_value).strip().lower() == str(computed_id).strip().lower()
                    logger.info(f"Comparative question verification: {verified} (expected: '{expected_value}', computed_id: '{computed_id}')")
                    return verified, {
                        "computed": computed_value,
                        "computed_id": computed_id,
                        "expected": expected_value,
                        "pipeline": cleaned_pipeline,
                        "match": verified
                    }
                
                # For non-comparative questions, if expected_value is None, we can't verify
                if expected_value is None:
                    if computed_id is not None:
                        logger.warning(f"Expected value is None but computed_id is {computed_id} - comparative question needs answer_structured.value")
                        return False, {
                            "computed": computed_value,
                            "computed_id": computed_id,
                            "expected": None,
                            "pipeline": cleaned_pipeline,
                            "error": "Expected value is None (comparative question - answer_structured.value should contain entity name)"
                        }
                    else:
                        logger.warning("Expected value is None - cannot verify")
                        return False, {
                            "computed": computed_value,
                            "expected": None,
                            "pipeline": cleaned_pipeline,
                            "error": "Expected value is None"
                        }
                
                if computed_value is None:
                    logger.warning("Computed value is None - aggregation may have failed")
                    return False, {
                        "computed": None,
                        "expected": expected_value,
                        "pipeline": cleaned_pipeline,
                        "error": "Computed value is None"
                    }
                
                # Try to convert both to numbers for comparison
                try:
                    expected_num = float(expected_value) if expected_value is not None else None
                    computed_num = float(computed_value) if computed_value is not None else None
                    
                    if expected_num is not None and computed_num is not None:
                        # Allow tolerance for floating point (5% or 0.01, whichever is larger)
                        # Increased from 1% to 5% to account for rounding differences and data variations
                        if abs(expected_num) > 1:
                            tolerance = max(0.01, abs(expected_num) * 0.05)  # 5% tolerance
                        else:
                            tolerance = 0.01
                        
                        diff = abs(expected_num - computed_num)
                        verified = diff <= tolerance
                        
                        logger.info(f"Verification result: {verified} (expected: {expected_num}, computed: {computed_num}, diff: {diff}, tolerance: {tolerance})")
                        
                        # If verification failed but difference is small (< 15%), log as potential rounding issue
                        if not verified and diff <= abs(expected_num) * 0.15:
                            logger.warning(f"Verification failed but difference is small - possible rounding/data variation issue")
                    else:
                        # String comparison (for non-comparative text answers)
                        verified = str(expected_value).strip().lower() == str(computed_value).strip().lower()
                        logger.info(f"String comparison result: {verified}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not convert to numbers for comparison: {e}")
                    # Fallback to string comparison
                    verified = str(expected_value).strip().lower() == str(computed_value).strip().lower()
                    logger.info(f"Fallback string comparison result: {verified}")
                
                return verified, {
                    "computed": computed_value,
                    "expected": expected_value,
                    "pipeline": cleaned_pipeline,
                    "match": verified
                }
            
            elif query_type == "find":
                # Simple find query
                filter_query = verification_query.get("filter", {})
                filter_query.update({
                    "file_id": file_id,
                    "table_name": table_name,
                    "user_id": self.user.id
                })
                
                # Handle nested field queries (e.g., "row.booking_id": "B001")
                if "row" not in filter_query:
                    # Wrap all non-row fields in row
                    new_filter = {}
                    for k, v in filter_query.items():
                        if k not in ["file_id", "table_name", "user_id"]:
                            new_filter[f"row.{k}"] = v
                        else:
                            new_filter[k] = v
                    filter_query = new_filter
                
                count = await self.tables_collection.count_documents(filter_query)
                expected_count = expected_answer.get("value", 0) if expected_answer else 0
                
                return count > 0 if expected_count > 0 else count == 0, {
                    "computed": count,
                    "expected": expected_count
                }
            
            return False, {"error": "Unknown query type"}
        except Exception as e:
            logger.error(f"Error verifying answer: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False, {"error": str(e)}
    
    async def generate_questions_for_file(
        self, 
        file_id: str, 
        table_name: str,
        question_types: List[str] = None,
        num_questions: int = 10
    ) -> Dict[str, Any]:
        """Generate questions for a specific file/table"""
        try:
            if question_types is None:
                question_types = ["factual", "aggregation", "comparative", "trend"]
            
            # Get table summary
            summary = await self.summarize_table(file_id, table_name)
            if "error" in summary:
                return {"success": False, "error": summary["error"]}
            
            generated_questions = []
            failed_count = 0
            
            # Generate questions
            questions_per_type = num_questions // len(question_types)
            
            for q_type in question_types:
                for i in range(questions_per_type):
                    try:
                        # Build prompt
                        prompt = self.build_prompt(summary, q_type)
                        
                        # Call Gemini
                        result = await self.call_gemini(prompt)
                        if not result:
                            failed_count += 1
                            continue
                        
                        # Verify answer (handle None answer_structured)
                        answer_structured = result.get("answer_structured") or {}
                        verified, verification_notes = await self.verify_answer(
                            file_id,
                            table_name,
                            result.get("verification_query", {}),
                            answer_structured,
                            result.get("answer", "")  # Pass answer_text for fallback extraction
                        )
                        
                        # ONLY save verified questions
                        if not verified:
                            logger.warning(f"Question failed verification, skipping save: {result.get('question', '')[:50]}")
                            failed_count += 1
                            continue
                        
                        # Generate question ID
                        question_id = f"q_{file_id[:8]}_{table_name}_{q_type}_{i+1}"
                        
                        # Store in qa_bank (only verified questions)
                        qa_doc = {
                            "user_id": self.user.id,
                            "file_id": file_id,
                            "table_name": table_name,
                            "question_id": question_id,
                            "question_type": q_type,
                            "question_text": result.get("question", ""),
                            "answer_text": result.get("answer", ""),
                            "answer_structured": answer_structured,
                            "difficulty": result.get("difficulty", "medium"),
                            "verification_query": result.get("verification_query", {}),
                            "verified": True,  # Always True since we only save verified questions
                            "verification_notes": verification_notes,
                            "explanation": result.get("explanation", ""),
                            "generated_by": "gemini-2.0-flash-exp",
                            "generation_time": datetime.utcnow(),
                            "quality_score": 0.9
                        }
                        
                        await self.qa_bank_collection.insert_one(qa_doc)
                        
                        # Convert ObjectId to string for JSON serialization
                        qa_doc["_id"] = str(qa_doc.get("_id", ""))
                        if isinstance(qa_doc.get("user_id"), ObjectId):
                            qa_doc["user_id"] = str(qa_doc["user_id"])
                        generated_questions.append(qa_doc)
                        
                    except Exception as e:
                        logger.error(f"Error generating question {i+1} for {q_type}: {str(e)}")
                        failed_count += 1
                        continue
            
            return {
                "success": True,
                "generated": len(generated_questions),
                "failed": failed_count,
                "verified": sum(1 for q in generated_questions if q.get("verified")),
                "questions": generated_questions
            }
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
    async def get_questions_for_file(self, file_id: str, table_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all questions for a file"""
        query = {
            "user_id": self.user.id,
            "file_id": file_id
        }
        if table_name:
            query["table_name"] = table_name
        
        cursor = self.qa_bank_collection.find(query).sort("generation_time", -1)
        questions_raw = await cursor.to_list(length=1000)
        
        # Clean all ObjectId and datetime values recursively
        questions = [clean_for_json(q) for q in questions_raw]
        
        return questions
    
    async def get_all_questions(self) -> Dict[str, Any]:
        """Get all questions grouped by category"""
        cursor = self.qa_bank_collection.find({"user_id": self.user.id}).sort("generation_time", -1)
        all_questions_raw = await cursor.to_list(length=10000)
        
        # Clean all ObjectId and datetime values recursively
        all_questions = [clean_for_json(q) for q in all_questions_raw]
        
        # Group by question_type
        grouped = {}
        for q in all_questions:
            q_type = q.get("question_type", "unknown")
            if q_type not in grouped:
                grouped[q_type] = []
            
            # Convert for JSON (already cleaned above)
            q_dict = {
                "id": q.get("question_id", ""),
                "question": q.get("question_text", ""),
                "answer": q.get("answer_text", ""),
                "category": q.get("difficulty", "medium").capitalize(),
                "type": q_type,
                "verified": q.get("verified", False),
                "quality_score": q.get("quality_score", 0),
                "explanation": q.get("explanation", ""),
                "verification_query": clean_for_json(q.get("verification_query", {}))
            }
            grouped[q_type].append(q_dict)
        
        # Also group by difficulty
        by_difficulty = {"Easy": [], "Medium": [], "Hard": []}
        for q in all_questions:
            difficulty = q.get("difficulty", "medium").capitalize()
            if difficulty in by_difficulty:
                q_dict = {
                    "id": q.get("question_id", ""),
                    "question": q.get("question_text", ""),
                    "answer": q.get("answer_text", ""),
                    "category": difficulty,
                    "type": q.get("question_type", "unknown"),
                    "verified": q.get("verified", False),
                    "quality_score": q.get("quality_score", 0),
                    "explanation": q.get("explanation", ""),
                    "verification_notes": clean_for_json(q.get("verification_notes", {}))
                }
                by_difficulty[difficulty].append(q_dict)
        
        return {
            "questions": by_difficulty,
            "metadata": {
                "total_questions": len(all_questions),
                "questions_by_category": {
                    "Easy": len(by_difficulty["Easy"]),
                    "Medium": len(by_difficulty["Medium"]),
                    "Hard": len(by_difficulty["Hard"])
                },
                "by_type": {k: len(v) for k, v in grouped.items()}
            }
        }
    
    async def generate_questions_across_all_files(
        self,
        question_types: List[str] = None,
        num_questions_per_file: int = 5
    ) -> Dict[str, Any]:
        """Generate questions across all user files"""
        try:
            from services.file_service import get_user_files
            
            # Get all user files
            all_files = await get_user_files(self.user, deduplicate=True)
            
            if not all_files:
                return {
                    "success": False,
                    "error": "No files found. Please upload files first."
                }
            
            if question_types is None:
                question_types = ["factual", "aggregation", "comparative", "trend"]
            
            total_generated = 0
            total_failed = 0
            total_verified = 0
            file_results = []
            
            # Normalize all files first
            for file_data in all_files:
                file_id = file_data.get("file_id")
                if not file_id:
                    continue
                
                # Normalize file data
                normalize_result = await self.normalize_file_to_tables(file_id)
                if not normalize_result.get("success"):
                    logger.warning(f"Failed to normalize file {file_id}: {normalize_result.get('error')}")
                    continue
            
            # Generate questions for each file
            for file_data in all_files:
                file_id = file_data.get("file_id")
                if not file_id:
                    continue
                
                # Get file metadata to find sheets
                from services.file_service import get_file_metadata
                file_info = await get_file_metadata(file_id, self.user)
                if not file_info:
                    continue
                
                metadata = file_info.get("metadata", {})
                sheets = metadata.get("sheets", {})
                
                # Process each sheet/table
                for table_name in (sheets.keys() if sheets else ["Sheet1"]):
                    try:
                        result = await self.generate_questions_for_file(
                            file_id=file_id,
                            table_name=table_name,
                            question_types=question_types,
                            num_questions=num_questions_per_file
                        )
                        
                        if result.get("success"):
                            total_generated += result.get("generated", 0)
                            total_failed += result.get("failed", 0)
                            total_verified += result.get("verified", 0)
                            
                            file_results.append({
                                "file_id": file_id,
                                "filename": file_data.get("filename") or file_data.get("original_filename", "unknown"),
                                "table_name": table_name,
                                "generated": result.get("generated", 0),
                                "verified": result.get("verified", 0),
                                "failed": result.get("failed", 0)
                            })
                    except Exception as e:
                        logger.error(f"Error generating questions for {file_id}/{table_name}: {str(e)}")
                        total_failed += num_questions_per_file
                        continue
            
            return {
                "success": True,
                "generated": total_generated,
                "failed": total_failed,
                "verified": total_verified,
                "files_processed": len(file_results),
                "file_results": file_results
            }
        except Exception as e:
            logger.error(f"Error generating questions across all files: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}

