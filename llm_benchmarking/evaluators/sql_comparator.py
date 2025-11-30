#!/usr/bin/env python3
"""
SQL Query Comparator
Compares SQL queries using token matching and structural analysis
"""

import re
from typing import Dict, List, Set, Tuple, Optional
from collections import Counter

try:
    import sqlparse
    HAS_SQLPARSE = True
except ImportError:
    HAS_SQLPARSE = False

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False


class SQLComparator:
    """Compares SQL queries for structural and semantic similarity."""
    
    # SQL keywords for matching
    AGGREGATE_FUNCTIONS = {'SUM', 'AVG', 'COUNT', 'MIN', 'MAX', 'TOTAL'}
    CLAUSES = {'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'JOIN', 'LEFT JOIN', 'INNER JOIN'}
    OPERATORS = {'=', '>', '<', '>=', '<=', '<>', '!=', 'LIKE', 'IN', 'BETWEEN', 'AND', 'OR', 'NOT'}
    
    # Known table names in our schema
    KNOWN_TABLES = {'production_logs', 'quality_control', 'maintenance_logs', 'inventory_logs'}
    
    def __init__(self):
        self.use_sqlparse = HAS_SQLPARSE
        self.use_rapidfuzz = HAS_RAPIDFUZZ
    
    def normalize_sql(self, sql: str) -> str:
        """Normalize SQL query for comparison."""
        if not sql:
            return ""
        
        # Convert to uppercase
        sql = sql.upper()
        
        # Remove extra whitespace
        sql = re.sub(r'\s+', ' ', sql).strip()
        
        # Remove quotes around identifiers
        sql = re.sub(r"['\"`]", "", sql)
        
        # Standardize operators
        sql = sql.replace('<>', '!=')
        
        return sql
    
    def extract_sql_from_response(self, response: str) -> str:
        """Extract SQL query from LLM response."""
        if not response:
            return ""
        
        # Try to find SQL in code blocks
        patterns = [
            r'```sql\s*(.*?)\s*```',
            r'```\s*(SELECT.*?)\s*```',
            r'(SELECT\s+.*?(?:;|$))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # If no code block, look for SELECT statement
        if 'SELECT' in response.upper():
            lines = response.split('\n')
            sql_lines = []
            in_sql = False
            for line in lines:
                if 'SELECT' in line.upper():
                    in_sql = True
                if in_sql:
                    sql_lines.append(line)
                    if ';' in line or line.strip() == '':
                        break
            if sql_lines:
                return '\n'.join(sql_lines).strip()
        
        return ""
    
    def extract_tokens(self, sql: str) -> Dict[str, Set[str]]:
        """Extract meaningful tokens from SQL query."""
        normalized = self.normalize_sql(sql)
        
        tokens = {
            'tables': set(),
            'columns': set(),
            'aggregates': set(),
            'clauses': set(),
            'conditions': set()
        }
        
        # Extract tables (FROM clause)
        for table in self.KNOWN_TABLES:
            if table.upper() in normalized:
                tokens['tables'].add(table.lower())
        
        # Extract aggregate functions
        for agg in self.AGGREGATE_FUNCTIONS:
            if agg in normalized:
                tokens['aggregates'].add(agg)
                # Try to extract column from aggregate
                match = re.search(rf'{agg}\s*\(\s*(\w+)\s*\)', normalized)
                if match:
                    tokens['columns'].add(match.group(1).lower())
        
        # Extract clauses
        for clause in self.CLAUSES:
            if clause in normalized:
                tokens['clauses'].add(clause)
        
        # Extract column names (simplified approach)
        # Look for patterns like table.column or standalone columns
        column_patterns = [
            r'SELECT\s+(.*?)\s+FROM',
            r'GROUP\s+BY\s+(\w+)',
            r'ORDER\s+BY\s+(\w+)',
            r'WHERE\s+(\w+)\s*[=<>]',
        ]
        
        for pattern in column_patterns:
            matches = re.findall(pattern, normalized)
            for match in matches:
                # Split by comma and clean
                cols = match.split(',')
                for col in cols:
                    col = col.strip()
                    # Remove aliases
                    col = re.sub(r'\s+AS\s+\w+', '', col)
                    # Remove aggregate functions to get column name
                    col = re.sub(r'(SUM|AVG|COUNT|MIN|MAX)\s*\(', '', col)
                    col = col.replace(')', '').replace('(', '')
                    col = col.strip()
                    if col and col not in {'*', 'DISTINCT'}:
                        # Handle table.column
                        if '.' in col:
                            col = col.split('.')[-1]
                        tokens['columns'].add(col.lower())
        
        return tokens
    
    def compare(self, expected_sql: str, generated_sql: str) -> Dict:
        """
        Compare expected and generated SQL queries.
        
        Returns:
            Dict with scores and details:
            - overall_score: 0-100
            - table_match: 0-100
            - column_match: 0-100
            - aggregate_match: 0-100
            - clause_match: 0-100
            - fuzzy_score: 0-100 (string similarity)
        """
        # Extract SQL from response if needed
        if '```' in generated_sql or '\n' in generated_sql:
            generated_sql = self.extract_sql_from_response(generated_sql)
        
        expected_tokens = self.extract_tokens(expected_sql)
        generated_tokens = self.extract_tokens(generated_sql)
        
        # Calculate individual scores
        scores = {}
        
        # Table matching
        scores['table_match'] = self._jaccard_similarity(
            expected_tokens['tables'], 
            generated_tokens['tables']
        ) * 100
        
        # Column matching
        scores['column_match'] = self._jaccard_similarity(
            expected_tokens['columns'], 
            generated_tokens['columns']
        ) * 100
        
        # Aggregate function matching
        scores['aggregate_match'] = self._jaccard_similarity(
            expected_tokens['aggregates'], 
            generated_tokens['aggregates']
        ) * 100
        
        # Clause matching
        scores['clause_match'] = self._jaccard_similarity(
            expected_tokens['clauses'], 
            generated_tokens['clauses']
        ) * 100
        
        # Fuzzy string similarity
        if self.use_rapidfuzz:
            scores['fuzzy_score'] = fuzz.token_sort_ratio(
                self.normalize_sql(expected_sql),
                self.normalize_sql(generated_sql)
            )
        else:
            # Simple fallback
            scores['fuzzy_score'] = self._simple_similarity(
                self.normalize_sql(expected_sql),
                self.normalize_sql(generated_sql)
            ) * 100
        
        # Calculate overall score (weighted)
        weights = {
            'table_match': 0.25,
            'column_match': 0.25,
            'aggregate_match': 0.20,
            'clause_match': 0.15,
            'fuzzy_score': 0.15
        }
        
        scores['overall_score'] = sum(
            scores[key] * weight for key, weight in weights.items()
        )
        
        # Add details
        scores['expected_tables'] = list(expected_tokens['tables'])
        scores['generated_tables'] = list(generated_tokens['tables'])
        scores['expected_columns'] = list(expected_tokens['columns'])
        scores['generated_columns'] = list(generated_tokens['columns'])
        scores['has_valid_sql'] = bool(generated_sql and 'SELECT' in generated_sql.upper())
        
        return scores
    
    def _jaccard_similarity(self, set1: Set, set2: Set) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def _simple_similarity(self, str1: str, str2: str) -> float:
        """Simple word-based similarity (fallback when rapidfuzz not available)."""
        if not str1 and not str2:
            return 1.0
        if not str1 or not str2:
            return 0.0
        
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        return self._jaccard_similarity(words1, words2)
    
    def batch_compare(self, comparisons: List[Tuple[str, str]]) -> List[Dict]:
        """
        Compare multiple SQL pairs.
        
        Args:
            comparisons: List of (expected_sql, generated_sql) tuples
        
        Returns:
            List of comparison results
        """
        return [self.compare(expected, generated) for expected, generated in comparisons]
