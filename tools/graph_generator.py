"""
Graph Generator Tool
Generates various types of charts and visualizations for data analysis.
Supports Chart.js format for frontend rendering.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class GraphGenerator:
    """Generates charts and visualizations in Chart.js format."""
    
    SUPPORTED_CHART_TYPES = [
        'bar', 'line', 'pie', 'doughnut', 'radar', 'polarArea',
        'scatter', 'bubble', 'area', 'stacked_bar', 'grouped_bar',
        'multi_line', 'combo'
    ]
    
    def __init__(self):
        """Initialize Graph Generator."""
        pass
    
    def generate_chart(
        self,
        data: List[Dict[str, Any]],
        chart_type: str,
        x_column: Optional[str] = None,
        y_columns: Optional[List[str]] = None,
        title: Optional[str] = None,
        group_by: Optional[str] = None,
        aggregate_function: str = 'sum',
        limit: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc'
    ) -> Dict[str, Any]:
        """
        Generate a chart from data.
        
        Args:
            data: List of data records
            chart_type: Type of chart (bar, line, pie, etc.)
            x_column: Column for X-axis (labels)
            y_columns: Columns for Y-axis (values) - can be multiple for multi-series
            title: Chart title
            group_by: Column to group data by
            aggregate_function: Function to aggregate data (sum, avg, count, min, max)
            limit: Limit number of data points
            sort_by: Column to sort by
            sort_order: Sort order (asc/desc)
            
        Returns:
            Dictionary with chart configuration in Chart.js format
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided"
                }
            
            if chart_type not in self.SUPPORTED_CHART_TYPES:
                return {
                    "success": False,
                    "error": f"Unsupported chart type: {chart_type}. Supported types: {', '.join(self.SUPPORTED_CHART_TYPES)}"
                }
            
            # Set default limit to prevent response truncation (max 50 data points for charts)
            # For time-series, 50 points is reasonable for visualization
            if limit is None or limit > 50:
                limit = 50
                logger.info(f"Applied default limit of {limit} data points to prevent large responses")
            
            df = pd.DataFrame(data)
            
            # Handle different chart types
            if chart_type in ['pie', 'doughnut', 'polarArea']:
                return self._generate_pie_chart(df, chart_type, x_column, y_columns[0] if y_columns else None, 
                                                title, group_by, aggregate_function, limit, sort_by, sort_order)
            elif chart_type in ['bar', 'stacked_bar', 'grouped_bar']:
                return self._generate_bar_chart(df, chart_type, x_column, y_columns, title, 
                                               group_by, aggregate_function, limit, sort_by, sort_order)
            elif chart_type in ['line', 'area', 'multi_line']:
                return self._generate_line_chart(df, chart_type, x_column, y_columns, title,
                                                group_by, aggregate_function, limit, sort_by, sort_order)
            elif chart_type == 'scatter':
                return self._generate_scatter_chart(df, x_column, y_columns, title, limit)
            elif chart_type == 'radar':
                return self._generate_radar_chart(df, x_column, y_columns, title, group_by, aggregate_function)
            elif chart_type == 'combo':
                return self._generate_combo_chart(df, x_column, y_columns, title, group_by, aggregate_function)
            else:
                return {
                    "success": False,
                    "error": f"Chart type {chart_type} not yet implemented"
                }
                
        except Exception as e:
            logger.error(f"Error generating chart: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _prepare_data(self, df: pd.DataFrame, x_column: str, y_columns: List[str], 
                     group_by: Optional[str], aggregate_function: str,
                     limit: Optional[int], sort_by: Optional[str], sort_order: str) -> pd.DataFrame:
        """Prepare and aggregate data for charting."""
        
        # Group and aggregate if needed
        if group_by:
            agg_dict = {}
            for col in y_columns:
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                    if aggregate_function == 'sum':
                        agg_dict[col] = 'sum'
                    elif aggregate_function in ['avg', 'mean']:
                        agg_dict[col] = 'mean'
                    elif aggregate_function == 'count':
                        agg_dict[col] = 'count'
                    elif aggregate_function == 'min':
                        agg_dict[col] = 'min'
                    elif aggregate_function == 'max':
                        agg_dict[col] = 'max'
            
            if agg_dict:
                df = df.groupby(group_by).agg(agg_dict).reset_index()
                if x_column == group_by or not x_column:
                    x_column = group_by
        
        # Sort data
        if sort_by and sort_by in df.columns:
            df = df.sort_values(by=sort_by, ascending=(sort_order == 'asc'))
        elif x_column in df.columns:
            df = df.sort_values(by=x_column, ascending=True)
        
        # Limit data points
        if limit and limit > 0:
            df = df.head(limit)
        
        return df
    
    def _generate_bar_chart(self, df: pd.DataFrame, chart_type: str, x_column: str, 
                           y_columns: List[str], title: str, group_by: Optional[str],
                           aggregate_function: str, limit: Optional[int], 
                           sort_by: Optional[str], sort_order: str) -> Dict[str, Any]:
        """Generate bar chart configuration."""
        
        if not x_column or not y_columns:
            return {"success": False, "error": "x_column and y_columns required for bar chart"}
        
        # Prepare data
        df = self._prepare_data(df, x_column, y_columns, group_by, aggregate_function, limit, sort_by, sort_order)
        
        if x_column not in df.columns:
            return {"success": False, "error": f"Column {x_column} not found"}
        
        labels = df[x_column].astype(str).tolist()
        datasets = []
        
        colors = self._get_color_palette(len(y_columns))
        
        for idx, y_col in enumerate(y_columns):
            if y_col not in df.columns:
                continue
            
            values = df[y_col].fillna(0).tolist()
            
            dataset = {
                "label": y_col.replace('_', ' ').title(),
                "data": values,
                "backgroundColor": colors[idx] if chart_type != 'grouped_bar' else colors[idx],
                "borderColor": self._darken_color(colors[idx]),
                "borderWidth": 1
            }
            
            if chart_type == 'stacked_bar':
                dataset['stack'] = 'Stack 0'
            
            datasets.append(dataset)
        
        options = {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "title": {
                    "display": True,
                    "text": title or f"{', '.join(y_columns)} by {x_column}",
                    "font": {"size": 16}
                },
                "legend": {
                    "display": len(y_columns) > 1,
                    "position": "top"
                }
            },
            "scales": {
                "x": {
                    "stacked": chart_type == 'stacked_bar',
                    "title": {"display": True, "text": x_column.replace('_', ' ').title()}
                },
                "y": {
                    "stacked": chart_type == 'stacked_bar',
                    "beginAtZero": True,
                    "title": {"display": True, "text": "Value"}
                }
            }
        }
        
        return {
            "success": True,
            "chart_type": "bar",
            "title": title or f"{', '.join(y_columns)} by {x_column}",
            "data": {
                "labels": labels,
                "datasets": datasets
            },
            "options": options
        }
    
    def _generate_line_chart(self, df: pd.DataFrame, chart_type: str, x_column: str,
                            y_columns: List[str], title: str, group_by: Optional[str],
                            aggregate_function: str, limit: Optional[int],
                            sort_by: Optional[str], sort_order: str) -> Dict[str, Any]:
        """Generate line chart configuration."""
        
        if not x_column or not y_columns:
            return {"success": False, "error": "x_column and y_columns required for line chart"}
        
        # Prepare data
        df = self._prepare_data(df, x_column, y_columns, group_by, aggregate_function, limit, sort_by, sort_order)
        
        if x_column not in df.columns:
            return {"success": False, "error": f"Column {x_column} not found"}
        
        labels = df[x_column].astype(str).tolist()
        datasets = []
        
        colors = self._get_color_palette(len(y_columns))
        
        for idx, y_col in enumerate(y_columns):
            if y_col not in df.columns:
                continue
            
            values = df[y_col].fillna(0).tolist()
            
            dataset = {
                "label": y_col.replace('_', ' ').title(),
                "data": values,
                "borderColor": colors[idx],
                "backgroundColor": colors[idx] + '33' if chart_type == 'area' else 'transparent',
                "borderWidth": 2,
                "fill": chart_type == 'area',
                "tension": 0.4,
                "pointRadius": 3,
                "pointHoverRadius": 5
            }
            
            datasets.append(dataset)
        
        options = {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "title": {
                    "display": True,
                    "text": title or f"{', '.join(y_columns)} over {x_column}",
                    "font": {"size": 16}
                },
                "legend": {
                    "display": len(y_columns) > 1,
                    "position": "top"
                }
            },
            "scales": {
                "x": {
                    "title": {"display": True, "text": x_column.replace('_', ' ').title()}
                },
                "y": {
                    "beginAtZero": True,
                    "title": {"display": True, "text": "Value"}
                }
            }
        }
        
        return {
            "success": True,
            "chart_type": "line",
            "title": title or f"{', '.join(y_columns)} over {x_column}",
            "data": {
                "labels": labels,
                "datasets": datasets
            },
            "options": options
        }
    
    def _generate_pie_chart(self, df: pd.DataFrame, chart_type: str, x_column: str,
                           y_column: str, title: str, group_by: Optional[str],
                           aggregate_function: str, limit: Optional[int],
                           sort_by: Optional[str], sort_order: str) -> Dict[str, Any]:
        """Generate pie/doughnut chart configuration."""
        
        if not x_column or not y_column:
            return {"success": False, "error": "x_column and y_column required for pie chart"}
        
        # Prepare data
        df = self._prepare_data(df, x_column, [y_column], group_by, aggregate_function, limit, sort_by, sort_order)
        
        if x_column not in df.columns or y_column not in df.columns:
            return {"success": False, "error": f"Columns {x_column} or {y_column} not found"}
        
        labels = df[x_column].astype(str).tolist()
        values = df[y_column].fillna(0).tolist()
        
        colors = self._get_color_palette(len(labels))
        
        options = {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "title": {
                    "display": True,
                    "text": title or f"{y_column} by {x_column}",
                    "font": {"size": 16}
                },
                "legend": {
                    "display": True,
                    "position": "right"
                }
            }
        }
        
        return {
            "success": True,
            "chart_type": chart_type,
            "title": title or f"{y_column} by {x_column}",
            "data": {
                "labels": labels,
                "datasets": [{
                    "data": values,
                    "backgroundColor": colors,
                    "borderColor": [self._darken_color(c) for c in colors],
                    "borderWidth": 1
                }]
            },
            "options": options
        }
    
    def _generate_scatter_chart(self, df: pd.DataFrame, x_column: str, y_columns: List[str],
                               title: str, limit: Optional[int]) -> Dict[str, Any]:
        """Generate scatter chart configuration."""
        
        if not x_column or not y_columns or len(y_columns) < 1:
            return {"success": False, "error": "x_column and at least one y_column required"}
        
        y_column = y_columns[0]
        
        if x_column not in df.columns or y_column not in df.columns:
            return {"success": False, "error": f"Columns {x_column} or {y_column} not found"}
        
        # Limit data points
        if limit:
            df = df.head(limit)
        
        data_points = []
        for _, row in df.iterrows():
            if pd.notna(row[x_column]) and pd.notna(row[y_column]):
                data_points.append({
                    "x": float(row[x_column]) if pd.api.types.is_numeric_dtype(df[x_column]) else hash(str(row[x_column])) % 1000,
                    "y": float(row[y_column])
                })
        
        color = self._get_color_palette(1)[0]
        
        options = {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "title": {
                    "display": True,
                    "text": title or f"{y_column} vs {x_column}",
                    "font": {"size": 16}
                },
                "legend": {"display": False}
            },
            "scales": {
                "x": {
                    "title": {"display": True, "text": x_column.replace('_', ' ').title()}
                },
                "y": {
                    "title": {"display": True, "text": y_column.replace('_', ' ').title()}
                }
            }
        }
        
        return {
            "success": True,
            "chart_type": "scatter",
            "title": title or f"{y_column} vs {x_column}",
            "data": {
                "datasets": [{
                    "label": f"{y_column} vs {x_column}",
                    "data": data_points,
                    "backgroundColor": color,
                    "borderColor": self._darken_color(color),
                    "pointRadius": 4
                }]
            },
            "options": options
        }
    
    def _generate_radar_chart(self, df: pd.DataFrame, x_column: str, y_columns: List[str],
                             title: str, group_by: Optional[str], aggregate_function: str) -> Dict[str, Any]:
        """Generate radar chart configuration."""
        
        if not x_column or not y_columns:
            return {"success": False, "error": "x_column and y_columns required for radar chart"}
        
        # Prepare data
        df = self._prepare_data(df, x_column, y_columns, group_by, aggregate_function, None, None, 'asc')
        
        if x_column not in df.columns:
            return {"success": False, "error": f"Column {x_column} not found"}
        
        labels = df[x_column].astype(str).tolist()
        datasets = []
        
        colors = self._get_color_palette(len(y_columns))
        
        for idx, y_col in enumerate(y_columns):
            if y_col not in df.columns:
                continue
            
            values = df[y_col].fillna(0).tolist()
            
            datasets.append({
                "label": y_col.replace('_', ' ').title(),
                "data": values,
                "backgroundColor": colors[idx] + '33',
                "borderColor": colors[idx],
                "borderWidth": 2,
                "pointBackgroundColor": colors[idx]
            })
        
        options = {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "title": {
                    "display": True,
                    "text": title or f"Radar Chart: {', '.join(y_columns)}",
                    "font": {"size": 16}
                },
                "legend": {
                    "display": True,
                    "position": "top"
                }
            },
            "scales": {
                "r": {
                    "beginAtZero": True
                }
            }
        }
        
        return {
            "success": True,
            "chart_type": "radar",
            "title": title or f"Radar Chart: {', '.join(y_columns)}",
            "data": {
                "labels": labels,
                "datasets": datasets
            },
            "options": options
        }
    
    def _generate_combo_chart(self, df: pd.DataFrame, x_column: str, y_columns: List[str],
                             title: str, group_by: Optional[str], aggregate_function: str) -> Dict[str, Any]:
        """Generate combination chart (bar + line)."""
        
        if not x_column or not y_columns or len(y_columns) < 2:
            return {"success": False, "error": "x_column and at least 2 y_columns required for combo chart"}
        
        # Prepare data
        df = self._prepare_data(df, x_column, y_columns, group_by, aggregate_function, None, None, 'asc')
        
        if x_column not in df.columns:
            return {"success": False, "error": f"Column {x_column} not found"}
        
        labels = df[x_column].astype(str).tolist()
        datasets = []
        
        colors = self._get_color_palette(len(y_columns))
        
        # First column as bar, rest as lines
        for idx, y_col in enumerate(y_columns):
            if y_col not in df.columns:
                continue
            
            values = df[y_col].fillna(0).tolist()
            
            if idx == 0:
                # Bar chart for first column
                datasets.append({
                    "type": "bar",
                    "label": y_col.replace('_', ' ').title(),
                    "data": values,
                    "backgroundColor": colors[idx],
                    "borderColor": self._darken_color(colors[idx]),
                    "borderWidth": 1,
                    "yAxisID": "y"
                })
            else:
                # Line chart for other columns
                datasets.append({
                    "type": "line",
                    "label": y_col.replace('_', ' ').title(),
                    "data": values,
                    "borderColor": colors[idx],
                    "backgroundColor": 'transparent',
                    "borderWidth": 2,
                    "tension": 0.4,
                    "yAxisID": "y1" if idx > 1 else "y"
                })
        
        options = {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "title": {
                    "display": True,
                    "text": title or f"Combo Chart: {', '.join(y_columns)}",
                    "font": {"size": 16}
                },
                "legend": {
                    "display": True,
                    "position": "top"
                }
            },
            "scales": {
                "x": {
                    "title": {"display": True, "text": x_column.replace('_', ' ').title()}
                },
                "y": {
                    "type": "linear",
                    "display": True,
                    "position": "left",
                    "beginAtZero": True
                },
                "y1": {
                    "type": "linear",
                    "display": len(y_columns) > 2,
                    "position": "right",
                    "beginAtZero": True,
                    "grid": {"drawOnChartArea": False}
                }
            }
        }
        
        return {
            "success": True,
            "chart_type": "bar",  # Chart.js uses 'bar' type for combo
            "title": title or f"Combo Chart: {', '.join(y_columns)}",
            "data": {
                "labels": labels,
                "datasets": datasets
            },
            "options": options
        }
    
    def _get_color_palette(self, count: int) -> List[str]:
        """Get a color palette with specified number of colors."""
        base_colors = [
            '#3B82F6',  # Blue
            '#10B981',  # Green
            '#F59E0B',  # Amber
            '#EF4444',  # Red
            '#8B5CF6',  # Purple
            '#EC4899',  # Pink
            '#14B8A6',  # Teal
            '#F97316',  # Orange
            '#6366F1',  # Indigo
            '#84CC16',  # Lime
        ]
        
        colors = []
        for i in range(count):
            colors.append(base_colors[i % len(base_colors)])
        
        return colors
    
    def _darken_color(self, color: str) -> str:
        """Darken a hex color by 20%."""
        # Simple darkening by adjusting hex values
        if color.startswith('#'):
            color = color[1:]
        
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
        
        r = max(0, int(r * 0.8))
        g = max(0, int(g * 0.8))
        b = max(0, int(b * 0.8))
        
        return f"#{r:02x}{g:02x}{b:02x}"
