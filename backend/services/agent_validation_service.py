"""
Agent Answer Validation Service - DISABLED
Agent and tools directories have been removed - will be rebuilt from scratch
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from models.user import UserInDB

logger = logging.getLogger(__name__)


class AgentAnswerValidator:
    """DISABLED - Agent validator removed. Will be rebuilt from scratch."""
    
    def __init__(self, user: UserInDB):
        raise NotImplementedError("AgentAnswerValidator has been removed - agent and tools directories deleted. Will be rebuilt from scratch.")
    
    def extract_numeric_value(self, text: str) -> Optional[float]:
        """Extract numeric value from text"""
        if not text:
            return None
        
        # Try direct parsing
        try:
            return float(text.strip())
        except:
            pass
        
        # Extract numbers with commas, decimals, etc.
        patterns = [
            r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',  # 1,234.56
            r'(\d+\.\d+)',  # 123.45
            r'(\d+)',  # 123
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text.replace(',', ''))
            if matches:
                try:
                    return float(matches[0].replace(',', ''))
                except:
                    continue
        
        return None
    
    def extract_chart_data(self, answer: str) -> Optional[Dict[str, Any]]:
        """Extract chart JSON from answer"""
        if isinstance(answer, dict):
            if (answer.get("chart_type") or answer.get("type")) and answer.get("data"):
                return answer
        
        if isinstance(answer, str):
            # Try to parse JSON
            try:
                parsed = json.loads(answer)
                if (parsed.get("chart_type") or parsed.get("type")) and parsed.get("data"):
                    return parsed
            except:
                pass
            
            # Look for JSON in markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', answer, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(1))
                    if (parsed.get("chart_type") or parsed.get("type")) and parsed.get("data"):
                        return parsed
                except:
                    pass
        
        return None
    
    async def verify_calculation_answer(
        self, 
        question: str, 
        answer: str,
        file_id: Optional[str] = None,
        table_name: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify a calculation answer against MongoDB data.
        
        Returns:
            (is_valid, verification_details)
        """
        try:
            # Extract expected value from answer
            expected_value = self.extract_numeric_value(answer)
            
            if expected_value is None:
                return False, {
                    "error": "Could not extract numeric value from answer",
                    "answer": answer
                }
            
            # Parse question to determine what to calculate
            question_lower = question.lower()
            
            # Determine calculation type and column
            calc_type = None
            column_name = None
            
            # Check for aggregation keywords
            if any(word in question_lower for word in ["total", "sum", "add"]):
                calc_type = "sum"
            elif any(word in question_lower for word in ["average", "avg", "mean"]):
                calc_type = "avg"
            elif any(word in question_lower for word in ["minimum", "min", "lowest"]):
                calc_type = "min"
            elif any(word in question_lower for word in ["maximum", "max", "highest"]):
                calc_type = "max"
            elif any(word in question_lower for word in ["count", "number of"]):
                calc_type = "count"
            
            # Find numeric columns in the data
            if file_id and table_name:
                # Get sample data to find columns
                cursor = self.tables_collection.find({
                    "file_id": file_id,
                    "table_name": table_name,
                    "user_id": self.user.id
                }).limit(100)
                
                rows = []
                async for doc in cursor:
                    rows.append(doc.get("row", {}))
                
                if rows:
                    df = pd.DataFrame(rows)
                    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                    
                    # Try to match column from question
                    for col in numeric_cols:
                        if col.lower() in question_lower:
                            column_name = col
                            break
                    
                    if not column_name and numeric_cols:
                        # Use first numeric column as fallback
                        column_name = numeric_cols[0]
                    
                    # Calculate actual value
                    if column_name and calc_type:
                        # Build aggregation pipeline
                        if calc_type == "count":
                            pipeline = [
                                {
                                    "$match": {
                                        "file_id": file_id,
                                        "table_name": table_name,
                                        "user_id": self.user.id
                                    }
                                },
                                {
                                    "$group": {
                                        "_id": None,
                                        "result": {"$sum": 1}
                                    }
                                }
                            ]
                        else:
                            # Build aggregation expression
                            agg_expr = {
                                "sum": f"$row.{column_name}",
                                "avg": f"$row.{column_name}",
                                "min": f"$row.{column_name}",
                                "max": f"$row.{column_name}"
                            }[calc_type]
                            
                            agg_op = {
                                "sum": "$sum",
                                "avg": "$avg",
                                "min": "$min",
                                "max": "$max"
                            }[calc_type]
                            
                            pipeline = [
                                {
                                    "$match": {
                                        "file_id": file_id,
                                        "table_name": table_name,
                                        "user_id": self.user.id,
                                        f"row.{column_name}": {"$exists": True, "$ne": None}
                                    }
                                },
                                {
                                    "$group": {
                                        "_id": None,
                                        "result": {agg_op: agg_expr}
                                    }
                                }
                            ]
                        
                        # Execute pipeline
                        result_cursor = self.tables_collection.aggregate(pipeline)
                        results = await result_cursor.to_list(length=1)
                        
                        if results and "result" in results[0]:
                            computed_value = results[0]["result"]
                            
                            # Compare with tolerance
                            tolerance = abs(expected_value * 0.05)  # 5% tolerance
                            diff = abs(expected_value - computed_value)
                            
                            is_valid = diff <= tolerance
                            
                            return is_valid, {
                                "expected": expected_value,
                                "computed": computed_value,
                                "difference": diff,
                                "tolerance": tolerance,
                                "calculation_type": calc_type,
                                "column": column_name,
                                "match": is_valid
                            }
            
            return False, {
                "error": "Could not verify calculation - insufficient data",
                "expected": expected_value
            }
            
        except Exception as e:
            logger.error(f"Error verifying calculation: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, {
                "error": str(e),
                "answer": answer
            }
    
    async def verify_comparative_answer(
        self,
        question: str,
        answer: str,
        file_id: Optional[str] = None,
        table_name: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Verify a comparative answer (which entity is best/worst)"""
        try:
            # Extract entity name from answer
            answer_lower = answer.lower()
            
            # Get data to find entities
            if file_id and table_name:
                cursor = self.tables_collection.find({
                    "file_id": file_id,
                    "table_name": table_name,
                    "user_id": self.user.id
                }).limit(1000)
                
                rows = []
                async for doc in cursor:
                    rows.append(doc.get("row", {}))
                
                if rows:
                    df = pd.DataFrame(rows)
                    
                    # Find categorical columns (potential entity columns)
                    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                    
                    # Check if answer contains any entity value
                    for col in categorical_cols:
                        unique_values = df[col].dropna().unique().tolist()
                        for value in unique_values:
                            if str(value).lower() in answer_lower:
                                return True, {
                                    "entity_found": str(value),
                                    "column": col,
                                    "match": True
                                }
            
            return False, {
                "error": "Could not verify comparative answer",
                "answer": answer
            }
            
        except Exception as e:
            logger.error(f"Error verifying comparative answer: {e}")
            return False, {
                "error": str(e),
                "answer": answer
            }
    
    async def verify_chart_answer(
        self,
        question: str,
        answer: str,
        chart_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Verify that chart data is valid and matches question"""
        try:
            chart_data = chart_config or self.extract_chart_data(answer)
            
            if not chart_data:
                return False, {
                    "error": "No chart configuration found in answer"
                }
            
            # Check chart structure
            if not chart_data.get("data") or not chart_data.get("data").get("labels"):
                return False, {
                    "error": "Invalid chart structure - missing labels or data"
                }
            
            # Check if chart has data points
            datasets = chart_data.get("data", {}).get("datasets", [])
            if not datasets or not datasets[0].get("data"):
                return False, {
                    "error": "Chart has no data points"
                }
            
            # Check if data values are numeric
            data_values = datasets[0].get("data", [])
            if not all(isinstance(v, (int, float)) for v in data_values if v is not None):
                return False, {
                    "error": "Chart data contains non-numeric values"
                }
            
            return True, {
                "chart_type": chart_data.get("chart_type") or chart_data.get("type"),
                "data_points": len(data_values),
                "labels_count": len(chart_data.get("data", {}).get("labels", [])),
                "valid": True
            }
            
        except Exception as e:
            logger.error(f"Error verifying chart: {e}")
            return False, {
                "error": str(e),
                "answer": answer[:200] if isinstance(answer, str) else str(answer)
            }
    
    async def verify_answer(
        self,
        question: str,
        answer: str,
        question_type: str = "auto",
        file_id: Optional[str] = None,
        table_name: Optional[str] = None,
        chart_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify agent answer based on question type.
        
        Args:
            question: User's question
            answer: Agent's answer
            question_type: "calculation", "comparative", "chart", "trend", or "auto"
            file_id: Optional file ID for data verification
            table_name: Optional table name
            chart_config: Optional chart configuration (if answer contains chart)
        
        Returns:
            (is_valid, verification_details)
        """
        # Auto-detect question type
        if question_type == "auto":
            question_lower = question.lower()
            
            if any(word in question_lower for word in ["chart", "graph", "plot", "show", "visualize", "display"]):
                question_type = "chart"
            elif any(word in question_lower for word in ["which", "who", "best", "worst", "highest", "lowest", "most", "least"]):
                question_type = "comparative"
            elif any(word in question_lower for word in ["total", "sum", "average", "avg", "count", "min", "max"]):
                question_type = "calculation"
            elif any(word in question_lower for word in ["trend", "change", "over time", "increase", "decrease"]):
                question_type = "trend"
            else:
                question_type = "factual"
        
        # Verify based on type
        if question_type == "chart":
            return await self.verify_chart_answer(question, answer, chart_config)
        elif question_type == "comparative":
            return await self.verify_comparative_answer(question, answer, file_id, table_name)
        elif question_type == "calculation":
            return await self.verify_calculation_answer(question, answer, file_id, table_name)
        else:
            # For factual/trend questions, just check if answer is not empty
            is_valid = bool(answer and len(str(answer).strip()) > 0)
            return is_valid, {
                "valid": is_valid,
                "answer_length": len(str(answer)) if answer else 0
            }

