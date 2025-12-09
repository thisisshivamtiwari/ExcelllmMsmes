"""
Data Generator Service
Handles industry-based data generation and MongoDB upload
"""

import os
import pandas as pd
import io
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from pathlib import Path

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from database import get_database, get_gridfs
from models.user import UserInDB
from services.file_service import upload_file_to_gridfs
from services.industry_service import get_industry_by_name

logger = logging.getLogger(__name__)

# Configure Gemini API if available
if GEMINI_AVAILABLE:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    else:
        GEMINI_AVAILABLE = False


async def get_industry_schema_preview(industry_name: str, use_ai: bool = True) -> Dict[str, Any]:
    """
    Get schema templates (files and columns) for an industry
    
    Args:
        industry_name: Name of the industry
        use_ai: Whether to use AI to generate dynamic schema templates (default: True)
        
    Returns:
        Dictionary with schema templates
    """
    industry = await get_industry_by_name(industry_name)
    if not industry:
        return {
            "success": False,
            "error": f"Industry '{industry_name}' not found"
        }
    
    schema_templates = industry.schema_templates or []
    
    # Convert Pydantic models to dicts for JSON serialization
    templates_for_json = []
    for template in schema_templates:
        if hasattr(template, 'dict'):
            templates_for_json.append(template.dict())
        elif hasattr(template, 'model_dump'):
            templates_for_json.append(template.model_dump())
        elif isinstance(template, dict):
            templates_for_json.append(template)
        else:
            templates_for_json.append({
                "name": getattr(template, "name", "unknown"),
                "columns": getattr(template, "columns", []),
                "description": getattr(template, "description", "")
            })
    
    # If AI is available and enabled, generate dynamic schema templates
    if use_ai and GEMINI_AVAILABLE and templates_for_json:
        try:
            model = genai.GenerativeModel("gemini-2.0-flash-exp")
            
            # Create a prompt to enhance/expand schema templates
            prompt = f"""You are a data schema expert for the {industry.display_name} industry.

Current schema templates:
{json.dumps(templates_for_json, indent=2)}

Based on the {industry.display_name} industry and the description "{industry.description}", 
suggest additional relevant data files and columns that would be useful for this industry.

Return a JSON array of schema templates. Each template should have:
- "name": File name (e.g., "Sales Data", "Inventory Logs")
- "columns": Array of column names (e.g., ["Date", "Product", "Quantity"])
- "description": Brief description of what this file contains

Include the existing templates and add 2-4 more relevant templates. Make sure column names are descriptive and industry-appropriate.

Return ONLY valid JSON, no markdown, no explanations:"""
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
            
            # Parse JSON response
            try:
                ai_templates = json.loads(response_text)
                if isinstance(ai_templates, list) and len(ai_templates) > 0:
                    # Merge with existing templates (AI templates take precedence for duplicates)
                    existing_names = {t.get("name") if isinstance(t, dict) else getattr(t, "name", "") for t in templates_for_json}
                    merged_templates = templates_for_json.copy()
                    
                    for ai_template in ai_templates:
                        if isinstance(ai_template, dict) and ai_template.get("name"):
                            if ai_template["name"] not in existing_names:
                                merged_templates.append(ai_template)
                                existing_names.add(ai_template["name"])
                    
                    templates_for_json = merged_templates
                    logger.info(f"Generated {len(ai_templates)} AI-enhanced schema templates for {industry_name}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse AI-generated schema templates: {e}. Using static templates.")
        except Exception as e:
            logger.warning(f"Error generating AI schema templates: {e}. Using static templates.")
    
    # Use templates_for_json (already converted to dicts) or convert schema_templates if AI wasn't used
    if 'templates_for_json' in locals() and templates_for_json:
        # AI was used or templates were converted, use templates_for_json
        final_templates = templates_for_json
    else:
        # AI not used, convert schema_templates to dicts
        final_templates = []
        for template in schema_templates:
            if isinstance(template, dict):
                final_templates.append(template)
            elif hasattr(template, 'dict'):
                final_templates.append(template.dict())
            elif hasattr(template, 'model_dump'):
                final_templates.append(template.model_dump())
            else:
                final_templates.append({
                    "name": getattr(template, "name", "unknown"),
                    "columns": getattr(template, "columns", []),
                    "description": getattr(template, "description", "")
                })
    
    return {
        "success": True,
        "industry": {
            "name": industry.name,
            "display_name": industry.display_name,
            "description": industry.description,
            "icon": industry.icon
        },
        "schema_templates": final_templates,
        "is_dynamic": use_ai and GEMINI_AVAILABLE
    }


async def check_existing_user_files(user: UserInDB) -> Dict[str, Any]:
    """
    Check existing files for the user with detailed sheet and column information
    
    Args:
        user: Current authenticated user
        
    Returns:
        Dictionary with existing files information including sheets and columns
    """
    db = get_database()
    files_collection = db["files"]
    
    # Find all files for user
    cursor = files_collection.find({"user_id": user.id})
    files = []
    
    async for doc in cursor:
        metadata = doc.get("metadata", {})
        sheets_data = metadata.get("sheets", {})
        sheet_names = metadata.get("sheet_names", [])
        
        # Extract sheets with columns
        sheets = []
        for sheet_name in sheet_names:
            sheet_info = sheets_data.get(sheet_name, {})
            sheets.append({
                "name": sheet_name,
                "columns": sheet_info.get("columns", []),
                "column_types": sheet_info.get("column_types", {}),
                "row_count": sheet_info.get("row_count", 0),
                "description": f"{sheet_info.get('row_count', 0)} rows, {len(sheet_info.get('columns', []))} columns"
            })
        
        files.append({
            "file_id": doc.get("file_id"),
            "original_filename": doc.get("original_filename"),
            "file_type": doc.get("file_type"),
            "file_size_bytes": doc.get("file_size_bytes"),
            "uploaded_at": doc.get("uploaded_at").isoformat() if doc.get("uploaded_at") else None,
            "row_count": sum(sheet.get("row_count", 0) for sheet in sheets_data.values()),
            "sheets": sheets,
            "sheet_count": len(sheets)
        })
    
    return {
        "success": True,
        "files": files,
        "count": len(files)
    }


async def generate_data_for_industry(
    user: UserInDB,
    industry_name: str,
    rows_per_file: Dict[str, int],
    add_to_existing: bool = False,
    generate_for_existing_sheets: Optional[Dict[str, Dict[str, int]]] = None
) -> Dict[str, Any]:
    """
    Generate data based on industry schema templates and upload to MongoDB
    
    Args:
        user: Current authenticated user
        industry_name: Name of the industry
        rows_per_file: Dictionary mapping file names to number of rows
        add_to_existing: Whether to add to existing files or create new ones
        generate_for_existing_sheets: Optional dict mapping file_id -> {sheet_name: num_rows}
                                      to generate data for existing sheets
        
    Returns:
        Dictionary with generation results
    """
    if not GEMINI_AVAILABLE:
        return {
            "success": False,
            "error": "Gemini API not available. Please set GEMINI_API_KEY environment variable."
        }
    
    # Get industry schema
    industry = await get_industry_by_name(industry_name)
    if not industry:
        return {
            "success": False,
            "error": f"Industry '{industry_name}' not found"
        }
    
    schema_templates = industry.schema_templates or []
    if not schema_templates:
        return {
            "success": False,
            "error": f"No schema templates found for industry '{industry_name}'"
        }
    
    # Convert Pydantic models to dicts if needed
    templates_list = []
    for template in schema_templates:
        if isinstance(template, dict):
            # Already a dict
            templates_list.append(template)
        elif hasattr(template, 'dict'):
            # Pydantic v1
            templates_list.append(template.dict())
        elif hasattr(template, 'model_dump'):
            # Pydantic v2
            templates_list.append(template.model_dump())
        else:
            # Access as attributes
            templates_list.append({
                "name": getattr(template, "name", "unknown"),
                "columns": getattr(template, "columns", []),
                "description": getattr(template, "description", "")
            })
    schema_templates = templates_list
    
    # Get existing files if adding to existing or generating for existing sheets
    existing_files = {}
    existing_files_by_id = {}
    if add_to_existing or generate_for_existing_sheets:
        existing_data = await check_existing_user_files(user)
        for file_info in existing_data.get("files", []):
            filename = file_info.get("original_filename")
            file_id = file_info.get("file_id")
            if filename:
                existing_files[filename] = file_info
            if file_id:
                existing_files_by_id[file_id] = file_info
    
    # Generate data for each schema template
    generated_files = []
    errors = []
    
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    
    # First, generate data for existing sheets if requested
    if generate_for_existing_sheets:
        from services.file_service import get_file_from_gridfs
        
        for file_id, sheets_config in generate_for_existing_sheets.items():
            if file_id not in existing_files_by_id:
                errors.append(f"File ID {file_id} not found")
                continue
            
            file_info = existing_files_by_id[file_id]
            filename = file_info.get("original_filename")
            sheets = file_info.get("sheets", [])
            
            try:
                # Get file content from GridFS
                file_content = await get_file_from_gridfs(file_id, user)
                if not file_content:
                    errors.append(f"Could not load file {filename}")
                    continue
                
                # Process each sheet
                file_ext = Path(filename).suffix.lower()
                if file_ext == '.csv':
                    # CSV file - single sheet
                    df = pd.read_csv(io.BytesIO(file_content))
                    
                    for sheet_name, num_rows in sheets_config.items():
                        if num_rows <= 0:
                            continue
                        
                        # Generate data matching existing columns
                        columns = list(df.columns)
                        prompt = f"""Generate realistic {industry.display_name} data for a CSV file with the following existing columns:

File: {filename}
Sheet: {sheet_name}
Existing columns: {', '.join(columns)}
Number of new rows to add: {num_rows}

Generate {num_rows} rows of realistic data that matches the existing schema. Return ONLY a valid CSV string with headers as the first row.
Do not include any explanations, markdown formatting, or code blocks - just the raw CSV data.

The data should be consistent with the existing data structure and appropriate for {industry.display_name} industry."""
                        
                        response = model.generate_content(prompt)
                        csv_data = response.text.strip()
                        
                        # Remove markdown code blocks if present
                        if csv_data.startswith("```"):
                            lines = csv_data.split("\n")
                            csv_data = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
                        
                        # Convert to DataFrame
                        new_df = pd.read_csv(io.StringIO(csv_data))
                        
                        # Ensure columns match
                        if list(new_df.columns) != columns:
                            # Reorder or add missing columns
                            for col in columns:
                                if col not in new_df.columns:
                                    new_df[col] = None
                            new_df = new_df[columns]
                        
                        # Append to existing data
                        combined_df = pd.concat([df, new_df], ignore_index=True)
                        
                        # Convert to CSV bytes
                        csv_bytes = combined_df.to_csv(index=False).encode('utf-8')
                        
                        # Get metadata from file_info
                        db = get_database()
                        files_collection = db["files"]
                        file_doc = await files_collection.find_one({"file_id": file_id})
                        metadata = file_doc.get("metadata", {}) if file_doc else {}
                        
                        # Update metadata
                        if "sheets" not in metadata:
                            metadata["sheets"] = {}
                        if "Sheet1" not in metadata["sheets"]:
                            metadata["sheets"]["Sheet1"] = {}
                        metadata["sheets"]["Sheet1"]["row_count"] = len(combined_df)
                        metadata["sheets"]["Sheet1"]["columns"] = list(combined_df.columns)
                        metadata["sheets"]["Sheet1"]["sample_data"] = combined_df.head(5).to_dict('records')
                        
                        # Delete old file and upload new one
                        gridfs = get_gridfs()
                        
                        if file_doc and file_doc.get("storage", {}).get("gridfs_id"):
                            try:
                                await gridfs.delete(file_doc["storage"]["gridfs_id"])
                            except Exception as e:
                                logger.warning(f"Could not delete GridFS file: {e}")
                        
                        await files_collection.delete_one({"file_id": file_id})
                        
                        # Upload updated file
                        result = await upload_file_to_gridfs(
                            user=user,
                            file_content=csv_bytes,
                            original_filename=filename,
                            file_metadata=metadata,
                            industry=industry_name
                        )
                        
                        generated_files.append({
                            "file_id": result["file_id"],
                            "filename": filename,
                            "sheet": sheet_name,
                            "rows_added": len(new_df),
                            "total_rows": len(combined_df),
                            "columns": list(combined_df.columns)
                        })
                        
                        logger.info(f"Generated and appended {len(new_df)} rows to {filename} ({sheet_name})")
                        
                else:
                    # Excel file - multiple sheets
                    excel_file = pd.ExcelFile(io.BytesIO(file_content))
                    
                    for sheet_name, num_rows in sheets_config.items():
                        if num_rows <= 0 or sheet_name not in excel_file.sheet_names:
                            continue
                        
                        # Load existing sheet
                        df = pd.read_excel(io.BytesIO(file_content), sheet_name=sheet_name)
                        columns = list(df.columns)
                        
                        # Generate data matching existing columns
                        prompt = f"""Generate realistic {industry.display_name} data for an Excel sheet with the following existing columns:

File: {filename}
Sheet: {sheet_name}
Existing columns: {', '.join(columns)}
Number of new rows to add: {num_rows}

Generate {num_rows} rows of realistic data that matches the existing schema. Return ONLY a valid CSV string with headers as the first row.
Do not include any explanations, markdown formatting, or code blocks - just the raw CSV data.

The data should be consistent with the existing data structure and appropriate for {industry.display_name} industry."""
                        
                        response = model.generate_content(prompt)
                        csv_data = response.text.strip()
                        
                        # Remove markdown code blocks if present
                        if csv_data.startswith("```"):
                            lines = csv_data.split("\n")
                            csv_data = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
                        
                        # Convert to DataFrame
                        new_df = pd.read_csv(io.StringIO(csv_data))
                        
                        # Ensure columns match
                        if list(new_df.columns) != columns:
                            for col in columns:
                                if col not in new_df.columns:
                                    new_df[col] = None
                            new_df = new_df[columns]
                        
                        # Append to existing data
                        combined_df = pd.concat([df, new_df], ignore_index=True)
                        
                        # Read all sheets and update the specific one
                        all_sheets = {}
                        for sheet in excel_file.sheet_names:
                            if sheet == sheet_name:
                                all_sheets[sheet] = combined_df
                            else:
                                all_sheets[sheet] = pd.read_excel(io.BytesIO(file_content), sheet_name=sheet)
                        
                        # Write to Excel bytes
                        try:
                            import openpyxl
                            excel_bytes = io.BytesIO()
                            with pd.ExcelWriter(excel_bytes, engine='openpyxl') as writer:
                                for sheet_name_excel, sheet_df in all_sheets.items():
                                    sheet_df.to_excel(writer, sheet_name=sheet_name_excel, index=False)
                            excel_bytes.seek(0)
                            excel_content = excel_bytes.read()
                        except ImportError:
                            # Fallback: if openpyxl not available, just update CSV
                            logger.warning("openpyxl not available, cannot update Excel file")
                            errors.append(f"Cannot update Excel file {filename}: openpyxl not installed")
                            continue
                        
                        # Get metadata from file_info
                        db = get_database()
                        files_collection = db["files"]
                        file_doc = await files_collection.find_one({"file_id": file_id})
                        metadata = file_doc.get("metadata", {}) if file_doc else {}
                        
                        # Update metadata
                        if "sheets" not in metadata:
                            metadata["sheets"] = {}
                        if sheet_name not in metadata["sheets"]:
                            metadata["sheets"][sheet_name] = {}
                        metadata["sheets"][sheet_name]["row_count"] = len(combined_df)
                        metadata["sheets"][sheet_name]["columns"] = list(combined_df.columns)
                        metadata["sheets"][sheet_name]["sample_data"] = combined_df.head(5).to_dict('records')
                        
                        # Delete old file and upload new one
                        gridfs = get_gridfs()
                        
                        if file_doc and file_doc.get("storage", {}).get("gridfs_id"):
                            try:
                                await gridfs.delete(file_doc["storage"]["gridfs_id"])
                            except Exception as e:
                                logger.warning(f"Could not delete GridFS file: {e}")
                        
                        await files_collection.delete_one({"file_id": file_id})
                        
                        # Upload updated file
                        result = await upload_file_to_gridfs(
                            user=user,
                            file_content=excel_content,
                            original_filename=filename,
                            file_metadata=metadata,
                            industry=industry_name
                        )
                        
                        generated_files.append({
                            "file_id": result["file_id"],
                            "filename": filename,
                            "sheet": sheet_name,
                            "rows_added": len(new_df),
                            "total_rows": len(combined_df),
                            "columns": list(combined_df.columns)
                        })
                        
                        logger.info(f"Generated and appended {len(new_df)} rows to {filename} ({sheet_name})")
                        
            except Exception as e:
                error_msg = f"Error generating data for existing file {filename}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
    
    for template in schema_templates:
        file_name = template.get("name", "unknown")
        columns = template.get("columns", [])
        description = template.get("description", "")
        
        if not columns:
            continue
        
        # Get number of rows for this file
        num_rows = rows_per_file.get(file_name, 100)
        if num_rows <= 0:
            continue
        
        try:
            # Generate data using Gemini
            prompt = f"""Generate realistic {industry.display_name} data for a CSV file with the following schema:

File: {file_name}
Description: {description}
Columns: {', '.join(columns)}
Number of rows: {num_rows}

Generate {num_rows} rows of realistic data. Return ONLY a valid CSV string with headers as the first row.
Do not include any explanations, markdown formatting, or code blocks - just the raw CSV data.

Example format:
{columns[0]},{columns[1]},{columns[2]}
value1,value2,value3
value4,value5,value6

Generate realistic, varied data appropriate for {industry.display_name} industry."""
            
            response = model.generate_content(prompt)
            csv_data = response.text.strip()
            
            # Remove markdown code blocks if present
            if csv_data.startswith("```"):
                lines = csv_data.split("\n")
                csv_data = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
            
            # Convert to DataFrame
            df = pd.read_csv(io.StringIO(csv_data))
            
            # If adding to existing, load and append
            if add_to_existing and file_name in existing_files:
                # Load existing file from GridFS
                from services.file_service import get_file_from_gridfs
                existing_file_id = existing_files[file_name].get("file_id")
                if existing_file_id:
                    try:
                        existing_content = await get_file_from_gridfs(existing_file_id, user)
                        existing_df = pd.read_csv(io.BytesIO(existing_content))
                        df = pd.concat([existing_df, df], ignore_index=True)
                    except Exception as e:
                        logger.warning(f"Could not load existing file {file_name}: {e}")
            
            # Convert DataFrame to CSV bytes
            csv_bytes = df.to_csv(index=False).encode('utf-8')
            
            # Generate filename
            filename = f"{file_name.lower().replace(' ', '_')}.csv"
            
            # Extract metadata
            metadata = {
                "file_name": filename,
                "file_type": "csv",
                "file_size_bytes": len(csv_bytes),
                "modified_date": datetime.utcnow().isoformat(),
                "sheet_names": ["Sheet1"],
                "sheets": {
                    "Sheet1": {
                        "row_count": len(df),
                        "column_count": len(df.columns),
                        "columns": list(df.columns),
                        "column_types": {col: str(df[col].dtype) for col in df.columns},
                        "null_counts": {col: int(df[col].isna().sum()) for col in df.columns},
                        "unique_counts": {col: int(df[col].nunique()) for col in df.columns},
                        "sample_data": df.head(5).to_dict('records')
                    }
                },
                "user_definitions": {}
            }
            
            # Upload to MongoDB GridFS
            if add_to_existing and file_name in existing_files:
                # Delete old file and upload new one
                db = get_database()
                files_collection = db["files"]
                gridfs = get_gridfs()
                
                # Get file doc before deleting
                file_doc = await files_collection.find_one({"file_id": existing_file_id})
                if file_doc and file_doc.get("storage", {}).get("gridfs_id"):
                    try:
                        # Delete from GridFS first
                        await gridfs.delete(file_doc["storage"]["gridfs_id"])
                    except Exception as e:
                        logger.warning(f"Could not delete GridFS file: {e}")
                
                # Then delete from files collection
                await files_collection.delete_one({"file_id": existing_file_id})
            
            result = await upload_file_to_gridfs(
                user=user,
                file_content=csv_bytes,
                original_filename=filename,
                file_metadata=metadata,
                industry=industry_name
            )
            
            generated_files.append({
                "file_id": result["file_id"],
                "filename": filename,
                "rows": len(df),
                "columns": list(df.columns)
            })
            
            logger.info(f"Generated and uploaded {filename} with {len(df)} rows")
            
        except Exception as e:
            error_msg = f"Error generating {file_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
    
    return {
        "success": len(generated_files) > 0,
        "generated_files": generated_files,
        "errors": errors,
        "total_files": len(generated_files),
        "total_rows": sum(f["rows"] for f in generated_files)
    }

