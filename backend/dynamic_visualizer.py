"""
Dynamic Visualization Generator
Auto-generates charts for ANY CSV file based on detected schema
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta
import sys

# Import Gemini Column Finder
sys.path.insert(0, str(Path(__file__).parent))
from gemini_column_finder import GeminiColumnFinder

logger = logging.getLogger(__name__)


class DynamicVisualizer:
    """
    Generates visualizations dynamically based on data structure
    No hardcoded column names or file names
    """
    
    def __init__(self):
        # Initialize Gemini-powered column finder
        self.gemini_finder = GeminiColumnFinder()
        logger.info(f"Dynamic Visualizer initialized with Gemini support: {self.gemini_finder.model is not None}")
        
        # Fallback keywords (only used if Gemini not available)
        self.numeric_keywords = [
            'qty', 'quantity', 'count', 'total', 'sum', 'amount', 'value', 'price', 
            'cost', 'revenue', 'sales', 'hours', 'minutes', 'rate', 'percent', 
            'weight', 'kg', 'units', 'number', 'target', 'actual', 'planned'
        ]
        
        self.date_keywords = [
            'date', 'time', 'datetime', 'timestamp', 'day', 'month', 'year',
            'created', 'updated', 'modified', 'period'
        ]
        
        self.categorical_keywords = [
            'type', 'category', 'group', 'class', 'status', 'name', 'id',
            'product', 'item', 'machine', 'line', 'shift', 'department'
        ]
        
    def detect_column_types(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Automatically detect column types without hardcoding
        """
        column_types = {
            'numeric': [],
            'categorical': [],
            'date': [],
            'text': []
        }
        
        for col in df.columns:
            col_lower = col.lower()
            
            # Check if it's a date column
            if any(keyword in col_lower for keyword in self.date_keywords):
                try:
                    pd.to_datetime(df[col])
                    column_types['date'].append(col)
                    continue
                except:
                    pass
            
            # Check data type
            if pd.api.types.is_numeric_dtype(df[col]):
                column_types['numeric'].append(col)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                column_types['date'].append(col)
            elif df[col].nunique() < len(df) * 0.5 and df[col].nunique() < 50:
                # Categorical if less than 50% unique values and less than 50 unique
                column_types['categorical'].append(col)
            else:
                column_types['text'].append(col)
        
        return column_types
    
    def find_best_columns(self, df: pd.DataFrame, column_types: Dict, purpose: str) -> Dict[str, str]:
        """
        Use Gemini AI (or semantic search fallback) to find best columns for specific purposes
        """
        # Try Gemini first
        if self.gemini_finder.model:
            try:
                all_columns = list(df.columns)
                purpose_descriptions = {
                    'quantity': 'find quantity or amount columns',
                    'target_actual': 'find target and actual columns for comparison',
                    'efficiency': 'calculate efficiency (actual vs target)',
                    'cost': 'find cost or price columns',
                    'time': 'find time duration columns (hours, minutes)'
                }
                
                gemini_purpose = purpose_descriptions.get(purpose, purpose)
                result = self.gemini_finder.find_columns(all_columns, gemini_purpose)
                
                if result:
                    logger.info(f"✅ Gemini found columns for '{purpose}': {result}")
                    return result
            except Exception as e:
                logger.warning(f"Gemini column finding failed, using fallback: {e}")
        
        # Fallback to keyword-based search
        result = {}
        
        if purpose == 'quantity':
            # Find quantity/value columns
            for col in column_types['numeric']:
                col_lower = col.lower()
                if any(kw in col_lower for kw in ['qty', 'quantity', 'amount', 'total', 'count', 'units']):
                    result['quantity'] = col
                    break
            
            # Fallback: use first numeric column
            if 'quantity' not in result and column_types['numeric']:
                result['quantity'] = column_types['numeric'][0]
        
        elif purpose == 'target_actual':
            # Find target and actual columns
            for col in column_types['numeric']:
                col_lower = col.lower()
                if 'target' in col_lower or 'plan' in col_lower:
                    result['target'] = col
                if 'actual' in col_lower or 'real' in col_lower:
                    result['actual'] = col
        
        elif purpose == 'efficiency':
            # Find columns for efficiency calculation
            target_col = None
            actual_col = None
            
            for col in column_types['numeric']:
                col_lower = col.lower()
                if 'target' in col_lower or 'plan' in col_lower:
                    target_col = col
                if 'actual' in col_lower or 'achieve' in col_lower:
                    actual_col = col
            
            if target_col and actual_col:
                result['target'] = target_col
                result['actual'] = actual_col
        
        elif purpose == 'cost':
            # Find cost/price columns
            for col in column_types['numeric']:
                col_lower = col.lower()
                if any(kw in col_lower for kw in ['cost', 'price', 'amount', 'rupees', 'dollar']):
                    result['cost'] = col
                    break
        
        elif purpose == 'time':
            # Find time-related columns
            for col in column_types['numeric']:
                col_lower = col.lower()
                if any(kw in col_lower for kw in ['hour', 'minute', 'time', 'duration']):
                    result['time'] = col
                    break
        
        return result
    
    def generate_visualizations(self, file_content: bytes, file_name: str, file_type: str = "csv") -> Dict[str, Any]:
        """
        Generate appropriate visualizations for any CSV/Excel file dynamically
        
        Args:
            file_content: File content as bytes (from MongoDB GridFS)
            file_name: Original filename
            file_type: File type ('csv', 'xlsx', 'xls')
        """
        try:
            import io
            
            # Load DataFrame from file content
            if file_type.lower() in ['xlsx', 'xls']:
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                df = pd.read_csv(io.BytesIO(file_content))
            
            if df.empty:
                return {}
            
            # Detect column types
            column_types = self.detect_column_types(df)
            
            visualizations = {
                'file_name': file_name,
                'row_count': len(df),
                'column_count': len(df.columns),
                'column_types': column_types,
                'charts': []
            }
            
            # 1. CATEGORICAL ANALYSIS
            # For each categorical column, create distribution charts
            for cat_col in column_types['categorical'][:3]:  # Limit to top 3
                if df[cat_col].nunique() <= 20:  # Only if reasonable number of categories
                    distribution = df[cat_col].value_counts().head(10).to_dict()
                    
                    visualizations['charts'].append({
                        'type': 'bar',
                        'title': f'Distribution by {cat_col}',
                        'data': {
                            'labels': list(distribution.keys()),
                            'values': list(distribution.values())
                        },
                        'description': f'Count of records by {cat_col}'
                    })
            
            # 2. NUMERIC AGGREGATIONS
            # For numeric columns, aggregate by categorical columns
            if column_types['categorical'] and column_types['numeric']:
                cat_col = column_types['categorical'][0]
                num_col = column_types['numeric'][0]
                
                if df[cat_col].nunique() <= 20:
                    agg_data = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False).head(10).to_dict()
                    
                    visualizations['charts'].append({
                        'type': 'bar',
                        'title': f'{num_col} by {cat_col}',
                        'data': {
                            'labels': list(agg_data.keys()),
                            'values': list(agg_data.values())
                        },
                        'description': f'Total {num_col} grouped by {cat_col}'
                    })
            
            # 3. TIME SERIES ANALYSIS
            # If date column exists, create trend charts
            if column_types['date'] and column_types['numeric']:
                date_col = column_types['date'][0]
                num_col = column_types['numeric'][0]
                
                try:
                    df[date_col] = pd.to_datetime(df[date_col])
                    df_sorted = df.sort_values(date_col)
                    
                    # Daily aggregation (last 30 days)
                    daily_data = df_sorted.groupby(df_sorted[date_col].dt.date)[num_col].sum().tail(30)
                    
                    visualizations['charts'].append({
                        'type': 'line',
                        'title': f'{num_col} Trend Over Time',
                        'data': {
                            'labels': [str(d) for d in daily_data.index],
                            'values': daily_data.tolist()
                        },
                        'description': f'Daily {num_col} over last 30 days'
                    })
                except Exception as e:
                    logger.warning(f"Could not create time series chart: {e}")
            
            # 4. PROPORTIONAL CHARTS (Pie/Doughnut)
            # For categorical with numeric values
            if column_types['categorical'] and column_types['numeric']:
                cat_col = column_types['categorical'][0]
                num_col = column_types['numeric'][0]
                
                if df[cat_col].nunique() <= 8:  # Good for pie charts
                    prop_data = df.groupby(cat_col)[num_col].sum().head(8).to_dict()
                    
                    visualizations['charts'].append({
                        'type': 'pie',
                        'title': f'{num_col} Distribution by {cat_col}',
                        'data': {
                            'labels': list(prop_data.keys()),
                            'values': list(prop_data.values())
                        },
                        'description': f'Proportional distribution of {num_col}'
                    })
            
            # 5. COMPARISON CHARTS
            # Find target vs actual columns dynamically
            target_actual = self.find_best_columns(df, column_types, 'target_actual')
            if 'target' in target_actual and 'actual' in target_actual:
                target_col = target_actual['target']
                actual_col = target_actual['actual']
                
                comparison = {
                    'Target': int(df[target_col].sum()),
                    'Actual': int(df[actual_col].sum())
                }
                
                visualizations['charts'].append({
                    'type': 'bar',
                    'title': f'{target_col} vs {actual_col}',
                    'data': {
                        'labels': list(comparison.keys()),
                        'values': list(comparison.values())
                    },
                    'description': f'Comparison of {target_col} and {actual_col}'
                })
            
            # 6. CALCULATED METRICS (Dynamic)
            metrics = self.calculate_dynamic_metrics(df, column_types)
            if metrics:
                visualizations['metrics'] = metrics
            
            return visualizations
            
        except Exception as e:
            logger.error(f"Error generating visualizations for {file_name}: {e}")
            return {}
    
    def calculate_dynamic_metrics(self, df: pd.DataFrame, column_types: Dict) -> Dict[str, Any]:
        """
        Calculate metrics dynamically based on available columns
        """
        metrics = {}
        
        try:
            # 1. Find and calculate efficiency (if target and actual exist)
            efficiency_cols = self.find_best_columns(df, column_types, 'efficiency')
            if 'target' in efficiency_cols and 'actual' in efficiency_cols:
                target_col = efficiency_cols['target']
                actual_col = efficiency_cols['actual']
                
                efficiency = (df[actual_col].sum() / df[target_col].sum() * 100) if df[target_col].sum() > 0 else 0
                metrics['efficiency'] = {
                    'value': round(efficiency, 2),
                    'formula': f'{actual_col} / {target_col} * 100',
                    'unit': '%'
                }
            
            # 2. Find and sum quantity columns
            quantity_cols = self.find_best_columns(df, column_types, 'quantity')
            if 'quantity' in quantity_cols:
                qty_col = quantity_cols['quantity']
                metrics['total_quantity'] = {
                    'value': int(df[qty_col].sum()),
                    'formula': f'SUM({qty_col})',
                    'unit': 'units'
                }
            
            # 3. Find and sum cost columns
            cost_cols = self.find_best_columns(df, column_types, 'cost')
            if 'cost' in cost_cols:
                cost_col = cost_cols['cost']
                metrics['total_cost'] = {
                    'value': round(df[cost_col].sum(), 2),
                    'formula': f'SUM({cost_col})',
                    'unit': 'currency'
                }
            
            # 4. Find and sum time columns
            time_cols = self.find_best_columns(df, column_types, 'time')
            if 'time' in time_cols:
                time_col = time_cols['time']
                metrics['total_time'] = {
                    'value': round(df[time_col].sum(), 2),
                    'formula': f'SUM({time_col})',
                    'unit': 'hours'
                }
            
            # 5. Calculate averages for all numeric columns
            for num_col in column_types['numeric'][:3]:  # Top 3
                avg_val = df[num_col].mean()
                metrics[f'avg_{num_col.lower().replace(" ", "_")}'] = {
                    'value': round(avg_val, 2),
                    'formula': f'AVG({num_col})',
                    'unit': 'average'
                }
            
        except Exception as e:
            logger.error(f"Error calculating dynamic metrics: {e}")
        
        return metrics
    
    
    def _generate_visualizations_for_dataframe(self, df: pd.DataFrame, file_name: str) -> Dict[str, Any]:
        """
        Internal method to generate visualizations from a DataFrame
        """
        if df.empty:
            return {}
        
        # Detect column types
        column_types = self.detect_column_types(df)
        
        visualizations = {
            'file_name': file_name,
            'row_count': len(df),
            'column_count': len(df.columns),
            'column_types': column_types,
            'columns': list(df.columns),
            'charts': []
        }
        
        # 1. CATEGORICAL ANALYSIS
        for cat_col in column_types['categorical'][:3]:
            if df[cat_col].nunique() <= 20:
                distribution = df[cat_col].value_counts().head(10).to_dict()
                
                visualizations['charts'].append({
                    'type': 'bar',
                    'title': f'Distribution by {cat_col}',
                    'data': {
                        'labels': [str(k) for k in distribution.keys()],
                        'values': [float(v) for v in distribution.values()]
                    },
                    'description': f'Count of records by {cat_col}',
                    'x_axis': cat_col,
                    'y_axis': 'Count'
                })
        
        # 2. NUMERIC AGGREGATIONS
        if column_types['categorical'] and column_types['numeric']:
            cat_col = column_types['categorical'][0]
            num_col = column_types['numeric'][0]
            
            if df[cat_col].nunique() <= 20:
                agg_data = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False).head(10).to_dict()
                
                visualizations['charts'].append({
                    'type': 'bar',
                    'title': f'{num_col} by {cat_col}',
                    'data': {
                        'labels': [str(k) for k in agg_data.keys()],
                        'values': [float(v) for v in agg_data.values()]
                    },
                    'description': f'Total {num_col} grouped by {cat_col}',
                    'x_axis': cat_col,
                    'y_axis': num_col
                })
        
        # 3. TIME SERIES ANALYSIS
        if column_types['date'] and column_types['numeric']:
            date_col = column_types['date'][0]
            num_col = column_types['numeric'][0]
            
            try:
                df[date_col] = pd.to_datetime(df[date_col])
                df_sorted = df.sort_values(date_col)
                
                # Daily aggregation (last 30 days)
                daily_data = df_sorted.groupby(df_sorted[date_col].dt.date)[num_col].sum().tail(30)
                
                visualizations['charts'].append({
                    'type': 'line',
                    'title': f'{num_col} Trend Over Time',
                    'data': {
                        'labels': [str(d) for d in daily_data.index],
                        'values': [float(v) for v in daily_data.tolist()]
                    },
                    'description': f'Daily {num_col} over last 30 days',
                    'x_axis': date_col,
                    'y_axis': num_col
                })
            except Exception as e:
                logger.warning(f"Could not create time series chart: {e}")
        
        # 4. PROPORTIONAL CHARTS (Pie/Doughnut)
        if column_types['categorical'] and column_types['numeric']:
            cat_col = column_types['categorical'][0]
            num_col = column_types['numeric'][0]
            
            if df[cat_col].nunique() <= 8:
                prop_data = df.groupby(cat_col)[num_col].sum().head(8).to_dict()
                
                visualizations['charts'].append({
                    'type': 'pie',
                    'title': f'{num_col} Distribution by {cat_col}',
                    'data': {
                        'labels': [str(k) for k in prop_data.keys()],
                        'values': [float(v) for v in prop_data.values()]
                    },
                    'description': f'Proportional distribution of {num_col}',
                    'category_column': cat_col,
                    'value_column': num_col
                })
        
        # 5. COMPARISON CHARTS
        target_actual = self.find_best_columns(df, column_types, 'target_actual')
        if 'target' in target_actual and 'actual' in target_actual:
            target_col = target_actual['target']
            actual_col = target_actual['actual']
            
            comparison = {
                'Target': float(df[target_col].sum()),
                'Actual': float(df[actual_col].sum())
            }
            
            visualizations['charts'].append({
                'type': 'bar',
                'title': f'{target_col} vs {actual_col}',
                'data': {
                    'labels': list(comparison.keys()),
                    'values': list(comparison.values())
                },
                'description': f'Comparison of {target_col} and {actual_col}',
                'x_axis': 'Type',
                'y_axis': 'Value'
            })
        
        # 6. CALCULATED METRICS
        metrics = self.calculate_dynamic_metrics(df, column_types)
        if metrics:
            visualizations['metrics'] = metrics
        
        return visualizations
    
    async def generate_visualizations_for_file(self, file_id: str, file_info: Dict[str, Any], file_content: bytes) -> Dict[str, Any]:
        """
        Generate visualizations for a single file from MongoDB
        
        Args:
            file_id: File ID
            file_info: File metadata from MongoDB
            file_content: File content bytes from GridFS
        """
        try:
            import io
            
            file_name = file_info.get("original_filename", file_id)
            file_type = file_info.get("file_type", "csv")
            
            # Handle Excel files with multiple sheets
            if file_type.lower() in ['xlsx', 'xls']:
                excel_file = pd.ExcelFile(io.BytesIO(file_content))
                all_sheets_viz = {}
                
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    if not df.empty:
                        sheet_viz = self._generate_visualizations_for_dataframe(df, f"{file_name} - {sheet_name}")
                        if sheet_viz:
                            all_sheets_viz[sheet_name] = sheet_viz
                
                excel_file.close()
                
                return {
                    "file_id": file_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "sheets": all_sheets_viz,
                    "sheet_count": len(all_sheets_viz)
                }
            else:
                # CSV file
                df = pd.read_csv(io.BytesIO(file_content))
                viz_data = self._generate_visualizations_for_dataframe(df, file_name)
                if viz_data:
                    viz_data["file_id"] = file_id
                    viz_data["file_type"] = file_type
                return viz_data
                
        except Exception as e:
            logger.error(f"Error generating visualizations for file {file_id}: {e}")
            return {}
    
    def generate_all_file_visualizations(self, data_dir: Path) -> Dict[str, Any]:
        """
        Generate visualizations for ALL CSV files in a directory (legacy method)
        """
        all_visualizations = {}
        
        try:
            # Find all CSV files
            csv_files = list(data_dir.glob("*.csv"))
            
            logger.info(f"Found {len(csv_files)} CSV files to visualize")
            
            for csv_file in csv_files:
                file_name = csv_file.name
                logger.info(f"Generating visualizations for {file_name}")
                
                with open(csv_file, 'rb') as f:
                    file_content = f.read()
                
                viz_data = self.generate_visualizations(file_content, file_name, "csv")
                if viz_data:
                    # Use file name without extension as key
                    key = file_name.replace('.csv', '')
                    all_visualizations[key] = viz_data
            
            return all_visualizations
            
        except Exception as e:
            logger.error(f"Error generating visualizations for directory: {e}")
            return {}


def test_dynamic_visualizer():
    """Test the dynamic visualizer with sample data"""
    import sys
    from pathlib import Path
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    visualizer = DynamicVisualizer()
    
    # Test with generated data
    data_dir = Path(__file__).parent.parent / "datagenerator" / "generated_data"
    
    if data_dir.exists():
        print(f"Testing with data from: {data_dir}")
        results = visualizer.generate_all_file_visualizations(data_dir)
        
        print(f"\n✅ Generated visualizations for {len(results)} files:")
        for file_key, viz_data in results.items():
            print(f"\n📊 {file_key}:")
            print(f"   - Rows: {viz_data.get('row_count', 0)}")
            print(f"   - Columns: {viz_data.get('column_count', 0)}")
            print(f"   - Charts: {len(viz_data.get('charts', []))}")
            print(f"   - Metrics: {len(viz_data.get('metrics', {}))}")
            
            if viz_data.get('metrics'):
                print(f"   - Calculated Metrics:")
                for metric_name, metric_data in viz_data['metrics'].items():
                    print(f"     • {metric_name}: {metric_data['value']} ({metric_data['formula']})")
    else:
        print(f"❌ Data directory not found: {data_dir}")
        sys.exit(1)


if __name__ == "__main__":
    test_dynamic_visualizer()

