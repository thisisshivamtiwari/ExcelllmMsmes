"""
Graph Generator Tool
Generates chart data in JSON format for visualization.
Supports various chart types: line, bar, pie, scatter, area, etc.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class GraphGenerator:
    """Generates chart data for visualization."""
    
    def generate_line_chart(
        self,
        data: List[Dict[str, Any]],
        x_column: str,
        y_column: str,
        group_by: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate line chart data.
        
        Args:
            data: List of data records
            x_column: Column for x-axis (typically date/time)
            y_column: Column for y-axis (numeric values)
            group_by: Optional column to group by (creates multiple lines)
            title: Optional chart title
            
        Returns:
            Dictionary with chart data in JSON format
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided"
                }
            
            df = pd.DataFrame(data)
            
            # Validate columns
            if x_column not in df.columns:
                return {
                    "success": False,
                    "error": f"X-axis column '{x_column}' not found"
                }
            
            if y_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Y-axis column '{y_column}' not found"
                }
            
            # Convert date column if needed
            if pd.api.types.is_datetime64_any_dtype(df[x_column]):
                df[x_column] = pd.to_datetime(df[x_column])
            else:
                # Try to parse as date
                try:
                    df[x_column] = pd.to_datetime(df[x_column], errors='coerce')
                except:
                    pass
            
            # Ensure y_column is numeric
            df[y_column] = pd.to_numeric(df[y_column], errors='coerce')
            
            # Sort by x_column
            df = df.sort_values(x_column)
            
            chart_data = {
                "type": "line",
                "title": title or f"{y_column} over {x_column}",
                "x_axis": {
                    "label": x_column,
                    "data": []
                },
                "y_axis": {
                    "label": y_column,
                    "data": []
                },
                "series": []
            }
            
            if group_by and group_by in df.columns:
                # Multiple series (one per group)
                groups = df.groupby(group_by)
                for group_name, group_df in groups:
                    series_data = []
                    for _, row in group_df.iterrows():
                        x_val = row[x_column]
                        y_val = row[y_column]
                        if pd.notna(x_val) and pd.notna(y_val):
                            series_data.append({
                                "x": x_val.isoformat() if isinstance(x_val, pd.Timestamp) else str(x_val),
                                "y": float(y_val)
                            })
                    
                    chart_data["series"].append({
                        "name": str(group_name),
                        "data": series_data
                    })
            else:
                # Single series
                series_data = []
                for _, row in df.iterrows():
                    x_val = row[x_column]
                    y_val = row[y_column]
                    if pd.notna(x_val) and pd.notna(y_val):
                        series_data.append({
                            "x": x_val.isoformat() if isinstance(x_val, pd.Timestamp) else str(x_val),
                            "y": float(y_val)
                        })
                
                chart_data["series"].append({
                    "name": y_column,
                    "data": series_data
                })
            
            return {
                "success": True,
                "chart": chart_data,
                "metadata": {
                    "data_points": len(df),
                    "x_column": x_column,
                    "y_column": y_column,
                    "group_by": group_by
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating line chart: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_bar_chart(
        self,
        data: List[Dict[str, Any]],
        x_column: str,
        y_column: str,
        group_by: Optional[str] = None,
        aggregation: str = "sum",
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate bar chart data.
        
        Args:
            data: List of data records
            x_column: Column for x-axis (categories)
            y_column: Column for y-axis (numeric values)
            group_by: Optional column to group by (stacked/grouped bars)
            aggregation: Aggregation function (sum, avg, count, max, min)
            title: Optional chart title
            
        Returns:
            Dictionary with chart data
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided"
                }
            
            df = pd.DataFrame(data)
            
            if x_column not in df.columns or y_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Columns not found: {x_column}, {y_column}"
                }
            
            # Ensure y_column is numeric
            df[y_column] = pd.to_numeric(df[y_column], errors='coerce')
            
            # Aggregate data
            if group_by and group_by in df.columns:
                # Group by both x_column and group_by
                grouped = df.groupby([x_column, group_by])[y_column]
            else:
                grouped = df.groupby(x_column)[y_column]
            
            # Apply aggregation
            if aggregation == "sum":
                aggregated = grouped.sum()
            elif aggregation == "avg" or aggregation == "mean":
                aggregated = grouped.mean()
            elif aggregation == "count":
                aggregated = grouped.count()
            elif aggregation == "max":
                aggregated = grouped.max()
            elif aggregation == "min":
                aggregated = grouped.min()
            else:
                aggregated = grouped.sum()
            
            chart_data = {
                "type": "bar",
                "title": title or f"{y_column} by {x_column}",
                "x_axis": {
                    "label": x_column,
                    "categories": []
                },
                "y_axis": {
                    "label": y_column,
                    "data": []
                },
                "series": []
            }
            
            if group_by and group_by in df.columns:
                # Multiple series (grouped/stacked bars)
                categories = sorted(df[x_column].unique())
                chart_data["x_axis"]["categories"] = [str(cat) for cat in categories]
                
                groups = sorted(df[group_by].unique())
                for group_name in groups:
                    series_data = []
                    for cat in categories:
                        key = (cat, group_name)
                        value = aggregated.get(key, 0)
                        series_data.append(float(value) if pd.notna(value) else 0.0)
                    
                    chart_data["series"].append({
                        "name": str(group_name),
                        "data": series_data
                    })
            else:
                # Single series
                categories = []
                values = []
                for idx, val in aggregated.items():
                    categories.append(str(idx))
                    values.append(float(val) if pd.notna(val) else 0.0)
                
                chart_data["x_axis"]["categories"] = categories
                chart_data["series"].append({
                    "name": y_column,
                    "data": values
                })
            
            return {
                "success": True,
                "chart": chart_data,
                "metadata": {
                    "data_points": len(df),
                    "x_column": x_column,
                    "y_column": y_column,
                    "group_by": group_by,
                    "aggregation": aggregation
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating bar chart: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_pie_chart(
        self,
        data: List[Dict[str, Any]],
        label_column: str,
        value_column: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate pie chart data.
        
        Args:
            data: List of data records
            label_column: Column for labels (categories)
            value_column: Column for values (numeric)
            title: Optional chart title
            
        Returns:
            Dictionary with chart data
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided"
                }
            
            df = pd.DataFrame(data)
            
            if label_column not in df.columns or value_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Columns not found: {label_column}, {value_column}"
                }
            
            # Ensure value_column is numeric
            df[value_column] = pd.to_numeric(df[value_column], errors='coerce')
            
            # Aggregate by label
            aggregated = df.groupby(label_column)[value_column].sum()
            
            chart_data = {
                "type": "pie",
                "title": title or f"Distribution of {value_column} by {label_column}",
                "data": []
            }
            
            total = aggregated.sum()
            for label, value in aggregated.items():
                percentage = (value / total * 100) if total > 0 else 0
                chart_data["data"].append({
                    "label": str(label),
                    "value": float(value) if pd.notna(value) else 0.0,
                    "percentage": round(percentage, 2)
                })
            
            # Sort by value descending
            chart_data["data"].sort(key=lambda x: x["value"], reverse=True)
            
            return {
                "success": True,
                "chart": chart_data,
                "metadata": {
                    "data_points": len(df),
                    "label_column": label_column,
                    "value_column": value_column,
                    "total": float(total)
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating pie chart: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_scatter_chart(
        self,
        data: List[Dict[str, Any]],
        x_column: str,
        y_column: str,
        size_column: Optional[str] = None,
        color_column: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate scatter chart data.
        
        Args:
            data: List of data records
            x_column: Column for x-axis
            y_column: Column for y-axis
            size_column: Optional column for point sizes
            color_column: Optional column for point colors
            title: Optional chart title
            
        Returns:
            Dictionary with chart data
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided"
                }
            
            df = pd.DataFrame(data)
            
            if x_column not in df.columns or y_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Columns not found: {x_column}, {y_column}"
                }
            
            # Ensure numeric columns
            df[x_column] = pd.to_numeric(df[x_column], errors='coerce')
            df[y_column] = pd.to_numeric(df[y_column], errors='coerce')
            
            chart_data = {
                "type": "scatter",
                "title": title or f"{y_column} vs {x_column}",
                "x_axis": {
                    "label": x_column
                },
                "y_axis": {
                    "label": y_column
                },
                "data": []
            }
            
            for _, row in df.iterrows():
                x_val = row[x_column]
                y_val = row[y_column]
                
                if pd.notna(x_val) and pd.notna(y_val):
                    point = {
                        "x": float(x_val),
                        "y": float(y_val)
                    }
                    
                    if size_column and size_column in df.columns:
                        size_val = row[size_column]
                        if pd.notna(size_val):
                            point["size"] = float(size_val)
                    
                    if color_column and color_column in df.columns:
                        color_val = row[color_column]
                        if pd.notna(color_val):
                            point["color"] = str(color_val)
                    
                    chart_data["data"].append(point)
            
            return {
                "success": True,
                "chart": chart_data,
                "metadata": {
                    "data_points": len(chart_data["data"]),
                    "x_column": x_column,
                    "y_column": y_column,
                    "size_column": size_column,
                    "color_column": color_column
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating scatter chart: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_area_chart(
        self,
        data: List[Dict[str, Any]],
        x_column: str,
        y_column: str,
        group_by: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate area chart data (similar to line chart but filled).
        
        Args:
            data: List of data records
            x_column: Column for x-axis
            y_column: Column for y-axis
            group_by: Optional column to group by
            title: Optional chart title
            
        Returns:
            Dictionary with chart data
        """
        # Area chart is similar to line chart, just different type
        result = self.generate_line_chart(data, x_column, y_column, group_by, title)
        if result.get("success"):
            result["chart"]["type"] = "area"
        return result
    
    def generate_heatmap(
        self,
        data: List[Dict[str, Any]],
        x_column: str,
        y_column: str,
        value_column: str,
        aggregation: str = "sum",
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate heatmap data.
        
        Args:
            data: List of data records
            x_column: Column for x-axis
            y_column: Column for y-axis
            value_column: Column for values (intensity)
            aggregation: Aggregation function
            title: Optional chart title
            
        Returns:
            Dictionary with chart data
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided"
                }
            
            df = pd.DataFrame(data)
            
            if not all(col in df.columns for col in [x_column, y_column, value_column]):
                return {
                    "success": False,
                    "error": f"Columns not found: {x_column}, {y_column}, {value_column}"
                }
            
            # Ensure value_column is numeric
            df[value_column] = pd.to_numeric(df[value_column], errors='coerce')
            
            # Aggregate
            grouped = df.groupby([x_column, y_column])[value_column]
            
            if aggregation == "sum":
                aggregated = grouped.sum()
            elif aggregation == "avg" or aggregation == "mean":
                aggregated = grouped.mean()
            elif aggregation == "count":
                aggregated = grouped.count()
            elif aggregation == "max":
                aggregated = grouped.max()
            elif aggregation == "min":
                aggregated = grouped.min()
            else:
                aggregated = grouped.sum()
            
            # Create matrix
            x_categories = sorted(df[x_column].unique())
            y_categories = sorted(df[y_column].unique())
            
            matrix = []
            for y_cat in y_categories:
                row = []
                for x_cat in x_categories:
                    key = (x_cat, y_cat)
                    value = aggregated.get(key, 0)
                    row.append(float(value) if pd.notna(value) else 0.0)
                matrix.append(row)
            
            chart_data = {
                "type": "heatmap",
                "title": title or f"{value_column} Heatmap",
                "x_axis": {
                    "label": x_column,
                    "categories": [str(cat) for cat in x_categories]
                },
                "y_axis": {
                    "label": y_column,
                    "categories": [str(cat) for cat in y_categories]
                },
                "data": matrix,
                "value_range": {
                    "min": float(aggregated.min()) if len(aggregated) > 0 else 0.0,
                    "max": float(aggregated.max()) if len(aggregated) > 0 else 0.0
                }
            }
            
            return {
                "success": True,
                "chart": chart_data,
                "metadata": {
                    "data_points": len(df),
                    "x_column": x_column,
                    "y_column": y_column,
                    "value_column": value_column,
                    "aggregation": aggregation
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating heatmap: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

