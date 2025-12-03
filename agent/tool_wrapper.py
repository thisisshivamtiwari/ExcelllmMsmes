"""
Tool wrappers for LangChain integration.
Wraps our custom tools to work with LangChain.
"""

from langchain.tools import Tool
from typing import Dict, Any, List, Optional
import logging
import json
import pandas as pd

logger = logging.getLogger(__name__)


def create_excel_retriever_tool(excel_retriever, semantic_retriever) -> Tool:
    """Create LangChain tool for Excel data retrieval."""
    
    def retrieve_data(query: str) -> str:
        """
        Retrieve data from Excel files based on semantic search and file name matching.
        
        Args:
            query: Natural language query describing what data to retrieve
            
        Returns:
            JSON string with retrieved data
        """
        try:
            # Normalize query for keyword detection
            query_lower = query.lower()
            
            # Step 1: Try to find file by name first (more reliable)
            file_id = excel_retriever.find_file_by_name(query)
            
            # Step 2: Use semantic search to find relevant columns
            columns = []
            if semantic_retriever:
                columns = semantic_retriever.retrieve_columns(query, n_results=10)
            
            # Step 2.5: If semantic search found columns from wrong file, prioritize file found by name
            if file_id and columns:
                # Filter columns to only those from the file we found by name
                columns = [col for col in columns if col.get("file_id") == file_id]
                # If no columns match, get all columns from the file we found
                if not columns:
                    columns = []  # Will trigger Step 3
            
            # Step 3: If we found a file by name but no columns, get all columns from that file
            if file_id and not columns:
                # Load metadata to get column names
                metadata = excel_retriever.load_file_metadata(file_id)
                if metadata and "schema" in metadata:
                    schema = metadata["schema"]
                    if "sheets" in schema:
                        for sheet_name, sheet_info in schema["sheets"].items():
                            if "columns" in sheet_info:
                                for col_name in sheet_info["columns"]:
                                    columns.append({
                                        "file_id": file_id,
                                        "file_name": metadata.get("original_filename", "unknown"),
                                        "column_name": col_name,
                                        "relevance_score": 0.5  # Default score
                                    })
                                break  # Use first sheet
            
            # Step 4: If no file found by name, use semantic search results
            if not file_id and columns:
                file_id = columns[0].get("file_id")
            
            # Step 5: If still no file found, return error
            if not file_id:
                return json.dumps({
                    "success": False,
                    "error": f"Could not find file matching query: '{query}'. Available files: {[f.get('original_filename') for f in excel_retriever.list_all_files()]}"
                })
            
            # Step 6: Determine which columns to retrieve
            columns_to_retrieve = None
            
            # Check if this is a trend/time-based query
            query_lower_for_trend = query.lower()
            trend_keywords = ["trend", "over time", "last month", "last week", "over the", "time series", "period", "daily", "weekly", "monthly"]
            is_trend_query = any(keyword in query_lower_for_trend for keyword in trend_keywords)
            
            if columns:
                # Extract column names from semantic search results that match the file we found
                matching_columns = [col.get("column_name") for col in columns[:10] if col.get("file_id") == file_id]
                # Only use semantic search columns if we found matching ones
                if matching_columns:
                    columns_to_retrieve = matching_columns
                    
                    # For trend queries, ensure date columns are included
                    if is_trend_query and file_id:
                        metadata = excel_retriever.load_file_metadata(file_id)
                        if metadata and "schema" in metadata:
                            schema = metadata["schema"]
                            if "sheets" in schema:
                                for sheet_name, sheet_info in schema["sheets"].items():
                                    if "columns" in sheet_info:
                                        all_columns = list(sheet_info["columns"].keys())
                                        # Find date columns
                                        date_columns = [col for col in all_columns if any(keyword in col.lower() for keyword in ["date", "time", "timestamp"])]
                                        # Add date columns if not already included
                                        for date_col in date_columns:
                                            if date_col not in columns_to_retrieve:
                                                columns_to_retrieve.append(date_col)
                                                logger.info(f"Added date column for trend query: {date_col}")
                                        break
            
            # If no columns from semantic search, get all columns from the file (for calculations/trends)
            # This ensures we have all data needed for accurate calculations and trend analysis
            if not columns_to_retrieve and file_id:
                metadata = excel_retriever.load_file_metadata(file_id)
                if metadata and "schema" in metadata:
                    schema = metadata["schema"]
                    if "sheets" in schema:
                        for sheet_name, sheet_info in schema["sheets"].items():
                            if "columns" in sheet_info:
                                # Get all column names from the file
                                columns_to_retrieve = list(sheet_info["columns"].keys())
                                logger.info(f"No semantic columns found, using all columns from file: {columns_to_retrieve[:5]}...")
                                break
            
            # Step 7: Retrieve data
            # Check if query is asking for a calculation (sum, total, average, etc.)
            query_lower = query.lower()
            calculation_keywords = [
                "total", "sum", "average", "avg", "mean", "count", "how many",
                "calculate", "what is", "what are", "how much", "aggregate"
            ]
            is_calculation_query = any(keyword in query_lower for keyword in calculation_keywords)
            
            # Also check if query asks for specific numeric operations
            numeric_operations = ["quantity", "amount", "cost", "defects", "failed", "passed", 
                                 "inspected", "consumption", "wastage", "downtime"]
            has_numeric_operation = any(op in query_lower for op in numeric_operations)
            
            # IMPORTANT: For large datasets, we need to retrieve all data to get accurate summary statistics
            # BUT we'll truncate the returned data to prevent JSON parsing errors
            # The summary statistics will have the accurate mean/count for calculations
            limit_value = None  # Always retrieve all data to get accurate summary stats
            
            logger.info(f"Query: '{query}' | Calculation query: {is_calculation_query} | Numeric operation: {has_numeric_operation} | Retrieving all data for summary stats")
            
            result = excel_retriever.retrieve_data(
                file_id=file_id,
                columns=columns_to_retrieve,
                limit=limit_value
            )
            
            # Step 8: For calculation queries, ALWAYS truncate data but keep summary statistics
            # This prevents JSON parsing errors when agent tries to pass data to calculator
            if result.get("success"):
                original_row_count = result.get("row_count", 0)
                data_rows = result.get("data", [])
                summary = result.get("summary", {})
                numeric_cols = summary.get("numeric_columns", {})
                
                if is_calculation_query or has_numeric_operation:
                    # For calculation queries, ALWAYS truncate to prevent JSON errors
                    # Use summary statistics for accurate calculations
                    max_rows_for_calculation = 100  # Safe limit to prevent JSON parsing errors
                    
                    if original_row_count > max_rows_for_calculation:
                        # Truncate data but keep summary statistics
                        result["data"] = data_rows[:max_rows_for_calculation]
                        result["truncated"] = True
                        result["total_rows_available"] = original_row_count
                        result["note"] = f"Retrieved {original_row_count} rows. Data truncated to {max_rows_for_calculation} rows to prevent JSON errors. Use summary statistics for accurate calculations: mean * count = total. Summary statistics: {numeric_cols}"
                        result["calculation_hint"] = f"For accurate calculations, use summary statistics: mean * count = total. Example: {numeric_cols.get(list(numeric_cols.keys())[0] if numeric_cols else {}, {}).get('mean', 0)} * {original_row_count} = total"
                        result["use_summary_stats"] = True
                    else:
                        # Small dataset - keep all data
                        result["note"] = f"Retrieved all {original_row_count} rows for calculation. Use data_calculator tool with this data."
                elif len(data_rows) > 50:
                    # Keep only first 50 rows for display
                    result["data"] = data_rows[:50]
                    result["truncated"] = True
                    result["total_rows_available"] = original_row_count
                    result["note"] = "Data truncated for display. Use summary statistics for full calculations."
            
            return json.dumps(result, default=str)
            
        except Exception as e:
            logger.error(f"Error in retrieve_data tool: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    return Tool(
        name="excel_data_retriever",
        description="Retrieve data from Excel/CSV files. Use this to get actual data rows. Input should be a natural language description of what data you need (e.g., 'production_logs', 'production quantity', 'quality control data'). The tool will automatically find the correct file and relevant columns.",
        func=retrieve_data
    )


def create_data_calculator_tool(data_calculator) -> Tool:
    """Create LangChain tool for data calculations."""
    
    def calculate(query: str) -> str:
        """
        Perform calculations on data.
        
        Args:
            query: Natural language query describing the calculation needed
            
        Returns:
            JSON string with calculation result
        """
        try:
            # Check input size to prevent JSON parsing errors with huge datasets
            if len(query) > 500000:  # ~500KB limit
                return json.dumps({
                    "success": False,
                    "error": f"Input data too large ({len(query)} chars). For large datasets, use summary statistics from excel_data_retriever instead of raw data. Try retrieving data with summary statistics or use a smaller subset."
                })
            
            # Parse query to extract parameters
            # For now, expect JSON input format: {"data": [...], "operation": "...", "column": "...", "group_by": "..."}
            # In production, this would use LLM to parse natural language
            
            # Try to parse as JSON first
            try:
                params = json.loads(query)
                data = params.get("data", [])
                operation = params.get("operation", "sum")
                column = params.get("column", "")
                group_by = params.get("group_by")
                
                # Check if data array is too large - reject immediately
                if isinstance(data, list) and len(data) > 100:
                    return json.dumps({
                        "success": False,
                        "error": f"Dataset too large ({len(data)} rows). For large datasets, use summary statistics from excel_data_retriever instead. The retriever provides 'mean' and 'count' in summary statistics - use mean * count = total for accurate calculations."
                    })
                
                group_by_list = None
                if group_by:
                    group_by_list = [col.strip() for col in group_by.split(",")] if isinstance(group_by, str) else group_by
                
                result = data_calculator.calculate(
                    data=data,
                    operation=operation,
                    column=column,
                    group_by=group_by_list
                )
                
                return json.dumps(result, default=str)
            except json.JSONDecodeError as e:
                # Provide more helpful error message
                error_msg = str(e)
                if "line 1 column" in error_msg:
                    # JSON parsing error at specific position - likely truncated or malformed
                    return json.dumps({
                        "success": False,
                        "error": f"JSON parsing error: {error_msg}. The data may be too large. Try using summary statistics from excel_data_retriever instead of passing all raw data. For calculations, you can use: mean * count from summary statistics."
                    })
                else:
                    return json.dumps({
                        "success": False,
                        "error": f"Invalid JSON format: {error_msg}. Expected JSON with 'data' (array), 'operation' (string), 'column' (string), and optional 'group_by' (comma-separated string)."
                    })
            
        except Exception as e:
            logger.error(f"Error in calculate tool: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    return Tool(
        name="data_calculator",
        description="Perform aggregations and calculations on data. Operations: sum, avg, count, min, max, median, std. Input should be JSON string with 'data' (array), 'operation' (string), 'column' (string), and optional 'group_by' (comma-separated string).",
        func=calculate
    )


def create_trend_analyzer_tool(trend_analyzer, excel_retriever=None, semantic_retriever=None) -> Tool:
    """Create LangChain tool for trend analysis."""
    
    def analyze_trend(query: str) -> str:
        """
        Analyze trends over time.
        
        Args:
            query: JSON string with parameters
            
        Returns:
            JSON string with trend analysis
        """
        try:
            try:
                params = json.loads(query)
            except json.JSONDecodeError as e:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid JSON format: {str(e)}. Expected JSON with 'data' (array or query string), 'date_column' (string), 'value_column' (string), 'period' (daily/weekly/monthly/quarterly/yearly), and optional 'group_by' (comma-separated string)."
                })
            
            data = params.get("data", [])
            date_column = params.get("date_column", "")
            value_column = params.get("value_column", "")
            period = params.get("period", "daily")
            group_by = params.get("group_by")
            
            # If data is a string (query), fetch data using excel_retriever
            if isinstance(data, str) and excel_retriever:
                logger.info(f"Data is a query string, fetching data: {data}")
                file_id = excel_retriever.find_file_by_name(data)
                if not file_id:
                    return json.dumps({
                        "success": False,
                        "error": f"Could not find file matching query: '{data}'. Use excel_data_retriever first to get the data."
                    })
                
                # Get columns - include date columns for trend analysis
                columns = []
                if semantic_retriever:
                    columns = semantic_retriever.retrieve_columns(data, n_results=10)
                    columns = [col.get("column_name") for col in columns if col.get("file_id") == file_id]
                
                # Ensure date column is included
                if not columns:
                    metadata = excel_retriever.load_file_metadata(file_id)
                    if metadata and "schema" in metadata:
                        schema = metadata["schema"]
                        if "sheets" in schema:
                            for sheet_name, sheet_info in schema["sheets"].items():
                                if "columns" in sheet_info:
                                    all_cols = list(sheet_info["columns"].keys())
                                    # Find date columns
                                    date_cols = [col for col in all_cols if any(kw in col.lower() for kw in ["date", "time", "timestamp"])]
                                    columns = date_cols + [col for col in all_cols if col not in date_cols]
                                    break
                
                # Retrieve data
                retrieve_result = excel_retriever.retrieve_data(
                    file_id=file_id,
                    columns=columns if columns else None,
                    limit=None  # Get all data for trend analysis
                )
                
                if not retrieve_result.get("success"):
                    return json.dumps({
                        "success": False,
                        "error": f"Failed to retrieve data: {retrieve_result.get('error', 'Unknown error')}"
                    })
                
                data = retrieve_result.get("data", [])
                
                # Auto-detect date column if not specified
                if not date_column and data:
                    df_temp = pd.DataFrame(data[:1]) if isinstance(data, list) else pd.DataFrame([data])
                    date_cols = [col for col in df_temp.columns if any(kw in col.lower() for kw in ["date", "time", "timestamp"])]
                    if date_cols:
                        date_column = date_cols[0]
                        logger.info(f"Auto-detected date column: {date_column}")
            
            # Validate data
            if not isinstance(data, list) or not data:
                return json.dumps({
                    "success": False,
                    "error": f"Data must be an array of objects. Got: {type(data).__name__}. Use excel_data_retriever first to get the data."
                })
            
            if not date_column:
                return json.dumps({
                    "success": False,
                    "error": "date_column is required. Common date column names: 'Date', 'Inspection_Date', 'Maintenance_Date'. Use excel_data_retriever to see available columns."
                })
            
            group_by_list = None
            if group_by:
                group_by_list = [col.strip() for col in group_by.split(",")] if isinstance(group_by, str) else group_by
            
            result = trend_analyzer.analyze_trend(
                data=data,
                date_column=date_column,
                value_column=value_column,
                period=period,
                group_by=group_by_list
            )
            
            return json.dumps(result, default=str)
            
        except Exception as e:
            logger.error(f"Error in analyze_trend tool: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    return Tool(
        name="trend_analyzer",
        description="Analyze trends over time periods. Input should be JSON string with 'data' (array from excel_data_retriever OR a query string like 'production_logs'), 'date_column' (string like 'Date'), 'value_column' (string like 'Actual_Qty'), 'period' (daily/weekly/monthly/quarterly/yearly), and optional 'group_by' (comma-separated string). If 'data' is a query string, the tool will fetch the data automatically and auto-detect the date column.",
        func=analyze_trend
    )


def create_comparative_analyzer_tool(comparative_analyzer, excel_retriever=None, semantic_retriever=None) -> Tool:
    """Create LangChain tool for comparative analysis."""
    
    def compare(query: str) -> str:
        """
        Compare entities.
        
        Args:
            query: JSON string with parameters
            
        Returns:
            JSON string with comparison results
        """
        try:
            # Check input size to prevent JSON parsing errors with huge datasets
            if len(query) > 500000:  # ~500KB limit
                return json.dumps({
                    "success": False,
                    "error": f"Input data too large ({len(query)} chars). For large datasets, use summary statistics from excel_data_retriever or retrieve a smaller subset of data."
                })
            
            try:
                params = json.loads(query)
            except json.JSONDecodeError as e:
                error_msg = str(e)
                if "line 1 column" in error_msg:
                    return json.dumps({
                        "success": False,
                        "error": f"JSON parsing error: {error_msg}. The data may be too large or truncated. Try using summary statistics or a smaller data subset."
                    })
                else:
                    return json.dumps({
                        "success": False,
                        "error": f"Invalid JSON format: {error_msg}. Expected JSON with 'data' (array or query string), 'compare_by' (string), 'value_column' (string), 'operation' (sum/avg/count/min/max), and optional 'top_n' (integer)."
                    })
            
            data = params.get("data", [])
            compare_by = params.get("compare_by", "")
            value_column = params.get("value_column", "")
            operation = params.get("operation", "sum")
            top_n = params.get("top_n")
            
            # If data is a string (query), fetch data using excel_retriever
            if isinstance(data, str) and excel_retriever:
                logger.info(f"Data is a query string, fetching data: {data}")
                # Use excel_retriever to fetch the data
                file_id = excel_retriever.find_file_by_name(data)
                if not file_id:
                    return json.dumps({
                        "success": False,
                        "error": f"Could not find file matching query: '{data}'. Use excel_data_retriever first to get the data, then pass the 'data' array to comparative_analyzer."
                    })
                
                # Get columns from semantic search if available
                columns = []
                if semantic_retriever:
                    columns = semantic_retriever.retrieve_columns(data, n_results=10)
                    columns = [col.get("column_name") for col in columns if col.get("file_id") == file_id]
                
                # Retrieve data - for comparisons, we need all data (no limit)
                # But we'll handle large datasets in the analyzer
                retrieve_result = excel_retriever.retrieve_data(
                    file_id=file_id,
                    columns=columns if columns else None,
                    limit=None  # Get all data for accurate comparisons
                )
                
                if not retrieve_result.get("success"):
                    return json.dumps({
                        "success": False,
                        "error": f"Failed to retrieve data: {retrieve_result.get('error', 'Unknown error')}"
                    })
                
                data = retrieve_result.get("data", [])
                original_row_count = retrieve_result.get("row_count", 0)
                
                # For large datasets, warn but proceed (comparative_analyzer can handle grouping efficiently)
                if original_row_count > 1000:
                    logger.warning(f"Large dataset for comparison: {original_row_count} rows. This may take longer.")
            
            # Validate data is a list
            if not isinstance(data, list):
                return json.dumps({
                    "success": False,
                    "error": f"Data must be an array of objects or a query string. Got: {type(data).__name__}. If you passed a query string, make sure excel_retriever is available."
                })
            
            if not data:
                return json.dumps({
                    "success": False,
                    "error": "No data provided. Use excel_data_retriever first to get data, then pass the 'data' array to comparative_analyzer."
                })
            
            # Check if data array is too large (but allow up to 2000 rows for comparisons)
            if len(data) > 2000:
                logger.warning(f"Very large dataset passed to comparative analyzer: {len(data)} rows. This may cause performance issues.")
            
            result = comparative_analyzer.compare(
                data=data,
                compare_by=compare_by,
                value_column=value_column,
                operation=operation,
                top_n=top_n
            )
            
            return json.dumps(result, default=str)
            
        except Exception as e:
            logger.error(f"Error in compare tool: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    return Tool(
        name="comparative_analyzer",
        description="Compare entities (products, lines, etc.) by a value column. Input should be JSON string with 'data' (array from excel_data_retriever OR a query string like 'quality control data'), 'compare_by' (string like 'Product'), 'value_column' (string like 'Failed_Qty'), 'operation' (sum/avg/count/min/max), and optional 'top_n' (integer). If 'data' is a query string, the tool will fetch the data automatically.",
        func=compare
    )


def create_kpi_calculator_tool(kpi_calculator) -> Tool:
    """Create LangChain tool for KPI calculation."""
    
    def calculate_kpi(query: str) -> str:
        """
        Calculate KPIs.
        
        Args:
            query: JSON string with parameters
            
        Returns:
            JSON string with KPI calculation
        """
        try:
            params = json.loads(query)
            kpi_name = params.get("kpi_name", "")
            data = params.get("data", [])
            
            if kpi_name.upper() == "OEE":
                result = kpi_calculator.calculate_oee(data=data, **{k: v for k, v in params.items() if k not in ["kpi_name", "data"]})
            elif kpi_name.upper() == "FPY":
                result = kpi_calculator.calculate_fpy(
                    data=data,
                    good_units_column=params.get("good_units_column"),
                    total_units_column=params.get("total_units_column")
                )
            elif kpi_name.lower() == "defect_rate":
                result = kpi_calculator.calculate_defect_rate(
                    data=data,
                    defect_column=params.get("defect_column"),
                    total_column=params.get("total_column")
                )
            else:
                result = {
                    "success": False,
                    "error": f"Unknown KPI: {kpi_name}"
                }
            
            return json.dumps(result, default=str)
            
        except Exception as e:
            logger.error(f"Error in calculate_kpi tool: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    return Tool(
        name="kpi_calculator",
        description="Calculate manufacturing KPIs (OEE, FPY, defect_rate). Input should be JSON string with 'kpi_name' (string), 'data' (array), and KPI-specific parameters.",
        func=calculate_kpi
    )

