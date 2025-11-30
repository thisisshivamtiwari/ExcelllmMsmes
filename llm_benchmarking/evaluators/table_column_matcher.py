#!/usr/bin/env python3
"""
Table and Column Matcher
Evaluates LLM's ability to identify correct tables and columns for a query
"""

import re
import json
from typing import Dict, List, Set, Optional, Tuple


class TableColumnMatcher:
    """Matches and scores table/column selection from LLM responses."""
    
    # Known schema
    SCHEMA = {
        'production_logs': [
            'Date', 'Shift', 'Line_Machine', 'Product', 'Target_Qty', 
            'Actual_Qty', 'Downtime_Minutes', 'Operator'
        ],
        'quality_control': [
            'Inspection_Date', 'Batch_ID', 'Product', 'Line', 'Inspected_Qty',
            'Passed_Qty', 'Failed_Qty', 'Defect_Type', 'Rework_Count', 'Inspector_Name'
        ],
        'maintenance_logs': [
            'Maintenance_Date', 'Machine', 'Maintenance_Type', 'Breakdown_Date',
            'Downtime_Hours', 'Issue_Description', 'Technician', 'Parts_Replaced', 'Cost_Rupees'
        ],
        'inventory_logs': [
            'Date', 'Material_Code', 'Material_Name', 'Opening_Stock_Kg',
            'Consumption_Kg', 'Received_Kg', 'Closing_Stock_Kg', 'Wastage_Kg',
            'Supplier', 'Unit_Cost_Rupees'
        ]
    }
    
    # Normalized column names for matching
    COLUMN_ALIASES = {
        'date': ['date', 'inspection_date', 'maintenance_date', 'breakdown_date'],
        'product': ['product'],
        'machine': ['machine', 'line_machine'],
        'line': ['line', 'line_machine'],
        'qty': ['target_qty', 'actual_qty', 'inspected_qty', 'passed_qty', 'failed_qty'],
        'cost': ['cost_rupees', 'unit_cost_rupees'],
        'downtime': ['downtime_minutes', 'downtime_hours'],
    }
    
    def __init__(self):
        # Build flat column list for matching
        self.all_columns = set()
        for cols in self.SCHEMA.values():
            self.all_columns.update(col.lower() for col in cols)
        
        self.all_tables = set(self.SCHEMA.keys())
    
    def normalize_name(self, name: str) -> str:
        """Normalize table/column name for matching."""
        name = name.lower().strip()
        # Remove common prefixes/suffixes
        name = re.sub(r'^(tbl_|table_)', '', name)
        name = re.sub(r'_table$', '', name)
        # Replace spaces/hyphens with underscores
        name = re.sub(r'[\s\-]', '_', name)
        return name
    
    def extract_from_response(self, response: str) -> Dict[str, List[str]]:
        """Extract tables and columns from LLM response."""
        result = {'tables': [], 'columns': []}
        
        if not response:
            return result
        
        # Try to parse as JSON first
        try:
            # Look for JSON block in code fence
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                result['tables'] = [self.normalize_name(t) for t in data.get('tables', [])]
                result['columns'] = [self.normalize_name(c) for c in data.get('columns', [])]
                return result
            
            # Look for raw JSON object
            json_match = re.search(r'\{[^{}]*"tables"\s*:\s*\[[^\]]*\][^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                result['tables'] = [self.normalize_name(t) for t in data.get('tables', [])]
                result['columns'] = [self.normalize_name(c) for c in data.get('columns', [])]
                return result
        except (json.JSONDecodeError, Exception):
            pass
        
        # Fallback: extract by pattern matching
        response_lower = response.lower()
        
        # Find tables
        for table in self.all_tables:
            if table in response_lower:
                result['tables'].append(table)
        
        # Find columns
        for col in self.all_columns:
            if col in response_lower:
                result['columns'].append(col)
        
        return result
    
    def match(self, expected_tables: List[str], expected_columns: List[str],
              response: str) -> Dict:
        """
        Match expected tables/columns against LLM response.
        
        Args:
            expected_tables: List of expected table names
            expected_columns: List of expected column names
            response: LLM response (raw text or JSON)
        
        Returns:
            Dict with scores and details
        """
        # Normalize expected values
        expected_tables_norm = set(self.normalize_name(t) for t in expected_tables)
        expected_columns_norm = set(self.normalize_name(c) for c in expected_columns)
        
        # Extract from response
        extracted = self.extract_from_response(response)
        generated_tables = set(extracted['tables'])
        generated_columns = set(extracted['columns'])
        
        # Calculate table metrics
        table_correct = expected_tables_norm & generated_tables
        table_missing = expected_tables_norm - generated_tables
        table_extra = generated_tables - expected_tables_norm
        
        table_precision = len(table_correct) / len(generated_tables) if generated_tables else 0
        table_recall = len(table_correct) / len(expected_tables_norm) if expected_tables_norm else 1
        table_f1 = 2 * (table_precision * table_recall) / (table_precision + table_recall) if (table_precision + table_recall) > 0 else 0
        
        # Calculate column metrics
        column_correct = expected_columns_norm & generated_columns
        column_missing = expected_columns_norm - generated_columns
        column_extra = generated_columns - expected_columns_norm
        
        column_precision = len(column_correct) / len(generated_columns) if generated_columns else 0
        column_recall = len(column_correct) / len(expected_columns_norm) if expected_columns_norm else 1
        column_f1 = 2 * (column_precision * column_recall) / (column_precision + column_recall) if (column_precision + column_recall) > 0 else 0
        
        # Overall score (weighted average)
        overall_score = (table_f1 * 0.4 + column_f1 * 0.6) * 100
        
        return {
            'overall_score': overall_score,
            'table_score': table_f1 * 100,
            'column_score': column_f1 * 100,
            'table_precision': table_precision * 100,
            'table_recall': table_recall * 100,
            'column_precision': column_precision * 100,
            'column_recall': column_recall * 100,
            'tables_correct': list(table_correct),
            'tables_missing': list(table_missing),
            'tables_extra': list(table_extra),
            'columns_correct': list(column_correct),
            'columns_missing': list(column_missing),
            'columns_extra': list(column_extra),
            'expected_tables': list(expected_tables_norm),
            'generated_tables': list(generated_tables),
            'expected_columns': list(expected_columns_norm),
            'generated_columns': list(generated_columns)
        }
    
    def batch_match(self, matches: List[Tuple[List[str], List[str], str]]) -> List[Dict]:
        """
        Match multiple table/column expectations against responses.
        
        Args:
            matches: List of (expected_tables, expected_columns, response) tuples
        
        Returns:
            List of match results
        """
        return [
            self.match(tables, columns, response) 
            for tables, columns, response in matches
        ]
    
    def validate_schema_coverage(self, tables: List[str], columns: List[str]) -> Dict:
        """
        Validate that tables and columns exist in schema.
        
        Returns:
            Dict with valid/invalid lists
        """
        tables_norm = [self.normalize_name(t) for t in tables]
        columns_norm = [self.normalize_name(c) for c in columns]
        
        valid_tables = [t for t in tables_norm if t in self.all_tables]
        invalid_tables = [t for t in tables_norm if t not in self.all_tables]
        
        valid_columns = [c for c in columns_norm if c in self.all_columns]
        invalid_columns = [c for c in columns_norm if c not in self.all_columns]
        
        return {
            'valid_tables': valid_tables,
            'invalid_tables': invalid_tables,
            'valid_columns': valid_columns,
            'invalid_columns': invalid_columns,
            'all_valid': len(invalid_tables) == 0 and len(invalid_columns) == 0
        }

