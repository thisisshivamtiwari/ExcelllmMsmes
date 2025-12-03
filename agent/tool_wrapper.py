"""
Tool wrappers for LangChain integration.
Wraps our custom tools to work with LangChain.
"""

from langchain.tools import Tool
from typing import Dict, Any, List, Optional
import logging
import json

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
            if columns:
                # Extract column names from semantic search results that match the file we found
                matching_columns = [col.get("column_name") for col in columns[:10] if col.get("file_id") == file_id]
                # Only use semantic search columns if we found matching ones
                if matching_columns:
                    columns_to_retrieve = matching_columns
            
            # If no columns from semantic search, get all columns from the file (for calculations)
            # This ensures we have all data needed for accurate calculations
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
            # If so, don't limit data - we need all rows for accurate calculations
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
            
            # For calculation queries OR numeric operations, get all data (no limit)
            # For display queries, limit to 50 rows to prevent token overflow
            limit_value = None if (is_calculation_query or has_numeric_operation) else 50
            
            logger.info(f"Query: '{query}' | Calculation query: {is_calculation_query} | Numeric operation: {has_numeric_operation} | Limit: {limit_value}")
            
            result = excel_retriever.retrieve_data(
                file_id=file_id,
                columns=columns_to_retrieve,
                limit=limit_value
            )
            
            # Step 8: For calculation queries, provide summary statistics for large datasets
            # For display queries, truncate to 50 rows
            if result.get("success"):
                original_row_count = result.get("row_count", 0)
                data_rows = result.get("data", [])
                
                if is_calculation_query or has_numeric_operation:
                    # For large datasets, provide summary statistics instead of all data
                    # This prevents JSON parsing errors when passing to calculator
                    if original_row_count > 500:
                        # Keep summary statistics and first 100 rows for reference
                        summary = result.get("summary", {})
                        numeric_cols = summary.get("numeric_columns", {})
                        
                        result["data"] = data_rows[:100]  # Keep first 100 rows for reference
                        result["truncated"] = True
                        result["total_rows_available"] = original_row_count
                        result["note"] = f"Retrieved {original_row_count} rows. For calculations, use summary statistics below or data_calculator with summary.mean * summary.count. Summary: {numeric_cols}"
                        result["calculation_hint"] = "For large datasets, use summary statistics: mean * count = total"
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
                
                # Check if data array is too large
                if isinstance(data, list) and len(data) > 1000:
                    logger.warning(f"Large dataset passed to calculator: {len(data)} rows. This may cause performance issues.")
                
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


def create_trend_analyzer_tool(trend_analyzer) -> Tool:
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
            params = json.loads(query)
            data = params.get("data", [])
            date_column = params.get("date_column", "")
            value_column = params.get("value_column", "")
            period = params.get("period", "daily")
            group_by = params.get("group_by")
            
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
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    return Tool(
        name="trend_analyzer",
        description="Analyze trends over time periods. Input should be JSON string with 'data' (array), 'date_column' (string), 'value_column' (string), 'period' (daily/weekly/monthly/quarterly/yearly), and optional 'group_by' (comma-separated string).",
        func=analyze_trend
    )


def create_comparative_analyzer_tool(comparative_analyzer) -> Tool:
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
                        "error": f"Invalid JSON format: {error_msg}. Expected JSON with 'data' (array), 'compare_by' (string), 'value_column' (string), 'operation' (sum/avg/count/min/max), and optional 'top_n' (integer)."
                    })
            
            data = params.get("data", [])
            compare_by = params.get("compare_by", "")
            value_column = params.get("value_column", "")
            operation = params.get("operation", "sum")
            top_n = params.get("top_n")
            
            # Check if data array is too large
            if isinstance(data, list) and len(data) > 1000:
                logger.warning(f"Large dataset passed to comparative analyzer: {len(data)} rows. This may cause performance issues.")
            
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
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    return Tool(
        name="comparative_analyzer",
        description="Compare entities (products, lines, etc.) by a value column. Input should be JSON string with 'data' (array), 'compare_by' (string), 'value_column' (string), 'operation' (sum/avg/count/min/max), and optional 'top_n' (integer).",
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

