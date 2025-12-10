"""
Dynamic Example Questions Service
Generates example questions based on user's actual data
"""

import logging
from typing import List, Dict, Any
from database import get_database
from models.user import UserInDB
from bson import ObjectId

logger = logging.getLogger(__name__)


class DynamicExamplesGenerator:
    """Generates dynamic example questions based on user's data"""
    
    def __init__(self, user: UserInDB):
        self.user = user
        self.db = get_database()
        self.files_collection = self.db["files"]
        self.tables_collection = self.db["tables"]
    
    async def generate_examples(self, limit: int = 10) -> List[str]:
        """
        Generate example questions based on user's uploaded files.
        
        Args:
            limit: Maximum number of examples to generate
        
        Returns:
            List of example question strings
        """
        examples = []
        
        try:
            # Get user's files
            cursor = self.files_collection.find({"user_id": self.user.id})
            files = await cursor.to_list(length=10)
            
            if not files:
                # Return generic examples if no files
                return [
                    "What is the total production quantity?",
                    "Which product has the most defects?",
                    "Show me production trends over the last month",
                    "Compare production efficiency across different lines",
                    "Calculate average quality metrics"
                ]
            
            # Analyze each file to generate relevant questions
            for file_info in files[:3]:  # Limit to 3 files for variety
                file_id = file_info.get("file_id")
                filename = file_info.get("original_filename", "data")
                metadata = file_info.get("metadata", {})
                sheets = metadata.get("sheets", {})
                
                if not sheets:
                    continue
                
                # Get column information from first sheet
                first_sheet = list(sheets.keys())[0]
                sheet_info = sheets[first_sheet]
                columns = sheet_info.get("columns", [])
                column_types = sheet_info.get("column_types", {})
                
                # Find numeric columns
                numeric_cols = [col for col, dtype in column_types.items() 
                               if dtype in ["int64", "float64", "numeric"]]
                
                # Find categorical columns
                categorical_cols = [col for col, dtype in column_types.items() 
                                  if dtype == "object" and col not in numeric_cols]
                
                # Find date columns
                date_cols = [col for col in columns if any(word in col.lower() 
                          for word in ["date", "time", "day", "month", "year"])]
                
                # Generate calculation questions
                if numeric_cols:
                    for col in numeric_cols[:2]:  # Limit to 2 numeric columns
                        col_name = col.replace("_", " ").title()
                        examples.append(f"What is the total {col_name.lower()}?")
                        examples.append(f"What is the average {col_name.lower()}?")
                
                # Generate comparative questions
                if categorical_cols and numeric_cols:
                    cat_col = categorical_cols[0]
                    num_col = numeric_cols[0]
                    cat_name = cat_col.replace("_", " ").title()
                    num_name = num_col.replace("_", " ").title()
                    
                    examples.append(f"Which {cat_name.lower()} has the highest {num_name.lower()}?")
                    examples.append(f"Which {cat_name.lower()} has the most {num_name.lower()}?")
                
                # Generate trend questions
                if date_cols and numeric_cols:
                    date_col = date_cols[0]
                    num_col = numeric_cols[0]
                    date_name = date_col.replace("_", " ").title()
                    num_name = num_col.replace("_", " ").title()
                    
                    examples.append(f"Show me {num_name.lower()} trends over time")
                    examples.append(f"How has {num_name.lower()} changed over the last month?")
                
                # Generate chart questions
                if numeric_cols:
                    num_col = numeric_cols[0]
                    num_name = num_col.replace("_", " ").title()
                    
                    examples.append(f"Show me {num_name.lower()} as a line chart")
                    if categorical_cols:
                        cat_col = categorical_cols[0]
                        cat_name = cat_col.replace("_", " ").title()
                        examples.append(f"Display {num_name.lower()} by {cat_name.lower()} as a bar chart")
            
            # Remove duplicates and limit
            unique_examples = []
            seen = set()
            for ex in examples:
                if ex not in seen and len(ex) > 10:  # Filter out very short examples
                    unique_examples.append(ex)
                    seen.add(ex)
                    if len(unique_examples) >= limit:
                        break
            
            # If we don't have enough, add generic ones
            while len(unique_examples) < limit:
                generic = [
                    "What is the total production quantity?",
                    "Which product has the most defects?",
                    "Show me production trends over the last month",
                    "Compare production efficiency across different lines",
                    "Calculate average quality metrics",
                    "Display maintenance frequency as a chart",
                    "What is the trend in quality over time?",
                    "Which line has the best performance?",
                    "Show me inventory levels as a bar chart",
                    "What is the average downtime?"
                ]
                for g in generic:
                    if g not in unique_examples:
                        unique_examples.append(g)
                        break
                if len(unique_examples) >= limit:
                    break
            
            return unique_examples[:limit]
            
        except Exception as e:
            logger.error(f"Error generating dynamic examples: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Return generic examples on error
            return [
                "What is the total production quantity?",
                "Which product has the most defects?",
                "Show me production trends over the last month",
                "Compare production efficiency across different lines",
                "Calculate average quality metrics"
            ]


