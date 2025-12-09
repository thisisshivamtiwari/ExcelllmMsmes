"""
MongoDB-aware Excel Data Retriever Tool
Retrieves filtered data from Excel/CSV files stored in MongoDB GridFS.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
import json
from datetime import datetime
import re
import io
import asyncio
from bson import ObjectId

logger = logging.getLogger(__name__)


class MongoDBExcelRetriever:
    """Retrieves and preprocesses data from Excel/CSV files stored in MongoDB GridFS."""
    
    def __init__(self, user_id: str):
        """
        Initialize MongoDB Excel Retriever.
        
        Args:
            user_id: User ID for multi-tenant filtering
        """
        self.user_id = user_id
        self._db = None
        self._gridfs = None
        self._files_collection = None
    
    def _get_db(self):
        """Get MongoDB database instance (lazy initialization)."""
        if self._db is None:
            from database import get_database, get_gridfs
            self._db = get_database()
            self._gridfs = get_gridfs()
            self._files_collection = self._db["files"]
        return self._db, self._gridfs, self._files_collection
    
    async def list_all_files(self) -> List[Dict[str, Any]]:
        """List all uploaded files for the current user."""
        try:
            _, _, files_collection = self._get_db()
            
            # Find all files for this user
            cursor = files_collection.find({"user_id": ObjectId(self.user_id)})
            files = []
            
            async for file_doc in cursor:
                files.append({
                    "file_id": file_doc.get("file_id"),
                    "original_filename": file_doc.get("original_filename", "unknown"),
                    "file_type": file_doc.get("file_type", "csv"),
                    "metadata": file_doc.get("metadata", {})
                })
            
            return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def list_all_files_sync(self) -> List[Dict[str, Any]]:
        """Synchronous wrapper for list_all_files."""
        def run_async_in_thread(coro):
            """Run async coroutine in a new thread with its own event loop."""
            def _run():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_run)
                return future.result()
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return run_async_in_thread(self.list_all_files())
            else:
                return asyncio.run(self.list_all_files())
        except RuntimeError:
            return asyncio.run(self.list_all_files())
        except Exception as e:
            logger.error(f"Error in list_all_files_sync wrapper: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def find_file_by_name(self, query: str) -> Optional[str]:
        """
        Find file ID by matching filename or semantic meaning.
        
        Args:
            query: Query string (e.g., "production_logs", "production quantity")
            
        Returns:
            File ID if found, None otherwise
        """
        def run_async_in_thread(coro):
            """Run async coroutine in a new thread with its own event loop."""
            def _run():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_run)
                return future.result()
        
        try:
            coro = self._find_file_by_name_async(query)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return run_async_in_thread(coro)
            else:
                return asyncio.run(coro)
        except RuntimeError:
            return asyncio.run(self._find_file_by_name_async(query))
        except Exception as e:
            logger.error(f"Error finding file by name: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def _find_file_by_name_async(self, query: str) -> Optional[str]:
        """Async implementation of find_file_by_name."""
        # Edge case: Validate query
        if not query or not isinstance(query, str) or not query.strip():
            logger.warning(f"Invalid query for find_file_by_name: {query}")
            return None
        
        files = await self.list_all_files()
        if not files:
            logger.info(f"No files found for user {self.user_id}")
            return None
        
        # Normalize query
        query_lower = query.lower().strip()
        
        # Common file name patterns with priority
        file_patterns = {
            "quality": {
                "keywords": ["quality", "qc", "inspection", "defect", "defects", "failed", "passed", "inspected", "rework"],
                "filename_patterns": ["quality", "qc", "inspection"]
            },
            "maintenance": {
                "keywords": ["maintenance", "breakdown", "repair", "cost", "downtime", "issue", "technician"],
                "filename_patterns": ["maintenance", "breakdown"]
            },
            "inventory": {
                "keywords": ["inventory", "stock", "material", "consumption", "wastage", "received"],
                "filename_patterns": ["inventory", "stock", "material"]
            },
            "production": {
                "keywords": ["production", "prod", "quantity", "actual", "target", "oee", "efficiency", "line", "machine"],
                "filename_patterns": ["production", "prod"]
            }
        }
        
        # Try exact filename match first
        for file_info in files:
            filename = file_info.get("original_filename", "").lower()
            if query_lower in filename or filename in query_lower:
                return file_info.get("file_id")
        
        # Try pattern matching with priority
        matched_files = []
        for file_info in files:
            filename = file_info.get("original_filename", "").lower()
            for pattern_key, pattern_info in file_patterns.items():
                keywords = pattern_info["keywords"]
                filename_patterns = pattern_info["filename_patterns"]
                
                if any(kw in query_lower for kw in keywords) and any(fp in filename for fp in filename_patterns):
                    matched_files.append((pattern_key, file_info))
                    break
        
        if matched_files:
            priority_order = ["quality", "maintenance", "inventory", "production"]
            matched_files.sort(key=lambda x: priority_order.index(x[0]) if x[0] in priority_order else 999)
            return matched_files[0][1].get("file_id")
        
        # Try partial match
        query_words = set(re.findall(r'\w+', query_lower))
        for file_info in files:
            filename = file_info.get("original_filename", "").lower()
            filename_words = set(re.findall(r'\w+', filename))
            if len(query_words & filename_words) >= 2:
                return file_info.get("file_id")
        
        return None
    
    async def load_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Load metadata for a file from MongoDB."""
        try:
            _, _, files_collection = self._get_db()
            
            file_doc = await files_collection.find_one({
                "file_id": file_id,
                "user_id": ObjectId(self.user_id)
            })
            
            if not file_doc:
                logger.warning(f"File {file_id} not found for user {self.user_id}")
                return None
            
            # Convert MongoDB document to metadata format
            metadata = {
                "file_id": file_doc.get("file_id"),
                "original_filename": file_doc.get("original_filename", "unknown"),
                "file_type": file_doc.get("file_type", "csv"),
                "uploaded_at": file_doc.get("uploaded_at").isoformat() if file_doc.get("uploaded_at") else None,
                "schema": file_doc.get("metadata", {}).get("sheets", {}),
                "user_definitions": file_doc.get("metadata", {}).get("user_definitions", {})
            }
            
            return metadata
        except Exception as e:
            logger.error(f"Error loading metadata for {file_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def load_file_metadata_sync(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for load_file_metadata."""
        def run_async_in_thread(coro):
            """Run async coroutine in a new thread with its own event loop."""
            def _run():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_run)
                return future.result()
        
        try:
            coro = self.load_file_metadata(file_id)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return run_async_in_thread(coro)
            else:
                return asyncio.run(coro)
        except RuntimeError:
            return asyncio.run(self.load_file_metadata(file_id))
        except Exception as e:
            logger.error(f"Error in load_file_metadata_sync wrapper: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def get_file_content(self, file_id: str) -> Optional[bytes]:
        """Get file content from GridFS."""
        try:
            _, gridfs, files_collection = self._get_db()
            
            # Find file document
            file_doc = await files_collection.find_one({
                "file_id": file_id,
                "user_id": ObjectId(self.user_id)
            })
            
            if not file_doc:
                return None
            
            # Get GridFS ID
            gridfs_id = file_doc.get("storage", {}).get("gridfs_id")
            if not gridfs_id:
                return None
            
            # Download from GridFS
            grid_out = await gridfs.open_download_stream(gridfs_id)
            file_content = await grid_out.read()
            
            return file_content
        except Exception as e:
            logger.error(f"Error getting file content for {file_id}: {str(e)}")
            return None
    
    def preprocess_dataframe(self, df: pd.DataFrame, schema: Dict[str, Any]) -> pd.DataFrame:
        """Preprocess DataFrame based on schema information."""
        df = df.copy()
        
        # Get column type mappings from schema
        column_types = {}
        if 'sheets' in schema:
            for sheet_name, sheet_info in schema['sheets'].items():
                if 'columns' in sheet_info:
                    for col_name, col_info in sheet_info['columns'].items():
                        if isinstance(col_info, dict):
                            column_types[col_name] = col_info.get('type', 'unknown')
                        else:
                            column_types[col_name] = col_info
        
        # Preprocess each column based on detected type
        for col_name in df.columns:
            if col_name not in column_types:
                continue
            
            col_type = column_types[col_name]
            
            try:
                if col_type == 'date':
                    df[col_name] = pd.to_datetime(df[col_name], errors='coerce')
                elif col_type == 'numeric':
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                elif col_type == 'boolean':
                    df[col_name] = self._normalize_boolean(df[col_name])
                elif col_type == 'categorical':
                    df[col_name] = df[col_name].astype(str).str.strip()
            except Exception as e:
                logger.warning(f"Error preprocessing column {col_name}: {str(e)}")
                continue
        
        return df
    
    def _normalize_boolean(self, series: pd.Series) -> pd.Series:
        """Normalize boolean-like values to True/False."""
        bool_map = {
            'yes': True, 'no': False,
            'true': True, 'false': False,
            '1': True, '0': False,
            'y': True, 'n': False,
            't': True, 'f': False,
        }
        
        normalized = series.copy()
        if normalized.dtype == 'object':
            normalized = normalized.astype(str).str.lower().str.strip()
            normalized = normalized.map(bool_map).fillna(normalized)
        
        return normalized
    
    async def retrieve_data_async(
        self,
        file_id: str,
        sheet_name: Optional[str] = None,
        columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Retrieve filtered data from a file (async version).
        
        Args:
            file_id: File ID
            sheet_name: Specific sheet name (None for first sheet)
            columns: List of column names to retrieve (None for all)
            filters: Dictionary of filters to apply
            limit: Maximum number of rows to return
            
        Returns:
            Dictionary with data and metadata
        """
        try:
            # Load file metadata
            metadata = await self.load_file_metadata(file_id)
            if not metadata:
                return {
                    "success": False,
                    "error": f"File {file_id} not found or access denied"
                }
            
            # Get file content from GridFS
            file_content = await self.get_file_content(file_id)
            if not file_content:
                return {
                    "success": False,
                    "error": f"File content not found for {file_id}"
                }
            
            file_type = metadata.get("file_type", "csv").lower()
            file_ext = f".{file_type}" if not file_type.startswith('.') else file_type
            
            # Load file into DataFrame
            excel_file = None
            first_sheet_name = "Sheet1"
            
            if file_ext in ['.xlsx', '.xls']:
                excel_file = pd.ExcelFile(io.BytesIO(file_content))
                first_sheet_name = excel_file.sheet_names[0] if excel_file.sheet_names else "Sheet1"
                if sheet_name:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                else:
                    df = pd.read_excel(excel_file, sheet_name=first_sheet_name)
            elif file_ext == '.csv':
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                df = None
                for enc in encodings:
                    try:
                        df = pd.read_csv(io.BytesIO(file_content), encoding=enc)
                        break
                    except UnicodeDecodeError:
                        continue
                if df is None:
                    return {
                        "success": False,
                        "error": f"Could not read CSV file {file_id} with any encoding"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Unsupported file type: {file_ext}"
                }
            
            # Edge case: Handle empty DataFrame
            if df.empty:
                return {
                    "success": True,
                    "file_id": file_id,
                    "file_name": metadata.get("original_filename", "unknown"),
                    "sheet_name": sheet_name or first_sheet_name,
                    "row_count": 0,
                    "column_count": len(df.columns) if hasattr(df, 'columns') else 0,
                    "columns": list(df.columns) if hasattr(df, 'columns') else [],
                    "data": [],
                    "summary": {"row_count": 0, "column_count": len(df.columns) if hasattr(df, 'columns') else 0},
                    "note": "File contains no data rows"
                }
            
            # Get schema for preprocessing
            schema = metadata.get("schema", {})
            
            # Preprocess data
            df = self.preprocess_dataframe(df, schema)
            
            # Select columns
            if columns:
                available_cols = [col for col in columns if col in df.columns]
                if available_cols:
                    df = df[available_cols]
                else:
                    logger.warning(f"None of the requested columns found: {columns}. Using all available columns.")
            
            # Apply filters
            if filters:
                df = self._apply_filters(df, filters)
            
            # Apply limit
            if limit:
                df = df.head(limit)
            
            # Convert to records
            records = df.to_dict('records')
            
            # Convert non-serializable types
            serializable_records = []
            for record in records:
                serializable_record = {}
                for key, value in record.items():
                    if pd.isna(value):
                        serializable_record[key] = None
                    elif isinstance(value, (pd.Timestamp, datetime)):
                        serializable_record[key] = value.isoformat()
                    elif isinstance(value, (np.integer, np.floating)):
                        # Handle inf, -inf, nan
                        if np.isinf(value) or np.isnan(value):
                            serializable_record[key] = None
                        else:
                            serializable_record[key] = float(value)
                    elif isinstance(value, np.bool_):
                        serializable_record[key] = bool(value)
                    else:
                        serializable_record[key] = value
                serializable_records.append(serializable_record)
            
            # Get schema information
            schema_info = metadata.get("schema", {})
            column_types = {}
            if 'sheets' in schema_info:
                for sheet_name_key, sheet_info in schema_info['sheets'].items():
                    if 'columns' in sheet_info:
                        for col_name, col_info in sheet_info['columns'].items():
                            if isinstance(col_info, dict):
                                column_types[col_name] = col_info.get('type', 'unknown')
                        break
            
            result = {
                "success": True,
                "file_id": file_id,
                "file_name": metadata.get("original_filename", "unknown"),
                "sheet_name": sheet_name or first_sheet_name,
                "row_count": len(serializable_records),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "column_types": column_types,
                "schema_note": f"Available columns: {', '.join(df.columns)}. Use these EXACT names.",
                "data": serializable_records,
                "summary": self._calculate_summary(df)
            }
            
            # Close Excel file if opened
            if excel_file:
                excel_file.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }
    
    def retrieve_data(
        self,
        file_id: str,
        sheet_name: Optional[str] = None,
        columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Retrieve filtered data from a file (synchronous wrapper for async method).
        """
        def run_async_in_thread(coro):
            """Run async coroutine in a new thread with its own event loop."""
            def _run():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_run)
                return future.result()
        
        try:
            coro = self.retrieve_data_async(file_id, sheet_name, columns, filters, limit)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, run in a separate thread with new event loop
                return run_async_in_thread(coro)
            else:
                return asyncio.run(coro)
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self.retrieve_data_async(
                file_id, sheet_name, columns, filters, limit
            ))
        except Exception as e:
            logger.error(f"Error in retrieve_data wrapper: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }
    
    def _apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply filters to DataFrame."""
        filtered_df = df.copy()
        
        for column, filter_value in filters.items():
            if column not in filtered_df.columns:
                continue
            
            if isinstance(filter_value, dict):
                # Complex filter
                if 'equals' in filter_value:
                    if filtered_df[column].dtype == 'object':
                        mask = filtered_df[column].notna() & (filtered_df[column].str.lower() == str(filter_value['equals']).lower())
                        filtered_df = filtered_df[mask]
                    else:
                        filtered_df = filtered_df[filtered_df[column] == filter_value['equals']]
                elif 'not_equals' in filter_value:
                    if filtered_df[column].dtype == 'object':
                        mask = filtered_df[column].notna() & (filtered_df[column].str.lower() != str(filter_value['not_equals']).lower())
                        filtered_df = filtered_df[mask]
                    else:
                        filtered_df = filtered_df[filtered_df[column] != filter_value['not_equals']]
                elif 'greater_than' in filter_value:
                    filtered_df = filtered_df[filtered_df[column] > filter_value['greater_than']]
                elif 'less_than' in filter_value:
                    filtered_df = filtered_df[filtered_df[column] < filter_value['less_than']]
                elif 'in' in filter_value:
                    filtered_df = filtered_df[filtered_df[column].isin(filter_value['in'])]
                elif 'contains' in filter_value:
                    filtered_df = filtered_df[filtered_df[column].astype(str).str.contains(
                        str(filter_value['contains']), case=False, na=False
                    )]
                elif 'date_range' in filter_value:
                    date_range = filter_value['date_range']
                    if 'start' in date_range:
                        filtered_df = filtered_df[filtered_df[column] >= pd.to_datetime(date_range['start'])]
                    if 'end' in date_range:
                        filtered_df = filtered_df[filtered_df[column] <= pd.to_datetime(date_range['end'])]
            else:
                # Simple equality filter
                if filtered_df[column].dtype == 'object' and isinstance(filter_value, str):
                    mask = filtered_df[column].notna() & (filtered_df[column].str.lower() == filter_value.lower())
                    filtered_df = filtered_df[mask]
                else:
                    filtered_df = filtered_df[filtered_df[column] == filter_value]
        
        return filtered_df
    
    def _calculate_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate summary statistics for DataFrame."""
        summary = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "numeric_columns": {},
            "categorical_columns": {}
        }
        
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                col_data = df[col].dropna()
                if len(col_data) > 0:
                    summary["numeric_columns"][col] = {
                        "min": float(col_data.min()) if not col_data.empty else None,
                        "max": float(col_data.max()) if not col_data.empty else None,
                        "mean": float(col_data.mean()) if not col_data.empty else None,
                        "median": float(col_data.median()) if not col_data.empty else None,
                        "null_count": int(df[col].isna().sum())
                    }
            elif df[col].dtype == 'object':
                value_counts = df[col].value_counts().head(10)
                summary["categorical_columns"][col] = {
                    "unique_count": int(df[col].nunique()),
                    "top_values": {str(k): int(v) for k, v in value_counts.items()},
                    "null_count": int(df[col].isna().sum())
                }
        
        return summary

