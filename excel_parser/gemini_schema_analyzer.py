"""
Gemini Schema Analyzer
Uses Google Gemini API for semantic schema understanding and column meaning inference.
"""

from typing import Dict, Any, List, Optional
import logging
import os
import json
import requests

logger = logging.getLogger(__name__)


class GeminiSchemaAnalyzer:
    """Uses Gemini API for advanced schema analysis."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini analyzer.
        
        Args:
            api_key: Gemini API key (if None, will try to load from environment)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            logger.warning("Gemini API key not found. Semantic analysis will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                
                # Try to list available models first
                available_model_names = []
                try:
                    available_models = genai.list_models()
                    available_model_names = [m.name.split('/')[-1] for m in available_models if 'generateContent' in m.supported_generation_methods]
                    logger.info(f"Available Gemini models: {available_model_names}")
                except Exception as list_error:
                    logger.warning(f"Could not list models (this is OK): {str(list_error)}")
                    # Continue with direct initialization
                
                # Try models in order of preference
                # Note: For v1beta API, we might need to use different model names
                preferred_models = []
                
                # If we have available models, use those first
                if available_model_names:
                    # Prioritize newer models
                    for preferred in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']:
                        if preferred in available_model_names:
                            preferred_models.append(preferred)
                    # Add any other available models
                    for model in available_model_names:
                        if model not in preferred_models:
                            preferred_models.append(model)
                else:
                    # Fallback: try common model names
                    preferred_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
                
                model_initialized = False
                last_error = None
                
                for model_name in preferred_models:
                    try:
                        # Initialize model
                        test_model = genai.GenerativeModel(model_name)
                        
                        # Test with a simple call - this is CRITICAL to ensure it works
                        try:
                            test_response = test_model.generate_content("test")
                            if test_response and hasattr(test_response, 'text'):
                                self.model = test_model
                                logger.info(f"✓ Gemini API successfully initialized and tested with {model_name}")
                                model_initialized = True
                                break
                        except Exception as test_error:
                            error_msg = str(test_error)
                            last_error = error_msg
                            if "404" in error_msg or "not found" in error_msg.lower() or "v1beta" in error_msg.lower():
                                logger.debug(f"Model {model_name} not available in current API version: {error_msg[:100]}")
                            else:
                                logger.warning(f"Model {model_name} test failed: {error_msg[:100]}")
                            continue
                    except Exception as init_error:
                        last_error = str(init_error)
                        logger.debug(f"Failed to initialize {model_name}: {last_error[:100]}")
                        continue
                
                if not model_initialized:
                    # Try REST API as fallback - this will definitely work
                    logger.warning("SDK initialization failed, trying REST API fallback...")
                    try:
                        # Test REST API with a simple call
                        rest_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.api_key}"
                        test_payload = {
                            "contents": [{
                                "parts": [{"text": "test"}]
                            }]
                        }
                        test_resp = requests.post(rest_url, json=test_payload, timeout=10)
                        if test_resp.status_code == 200:
                            logger.info("✓ Gemini REST API works! Using REST API fallback")
                            self.use_rest_api = True
                            self.rest_api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
                            model_initialized = True
                        elif test_resp.status_code == 404:
                            # Try gemini-1.5-flash
                            rest_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
                            test_resp = requests.post(rest_url, json=test_payload, timeout=10)
                            if test_resp.status_code == 200:
                                logger.info("✓ Gemini REST API works with gemini-1.5-flash! Using REST API fallback")
                                self.use_rest_api = True
                                self.rest_api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
                                model_initialized = True
                    except Exception as rest_error:
                        logger.error(f"REST API fallback also failed: {str(rest_error)}")
                    
                    if not model_initialized:
                        error_msg = f"Could not initialize any working Gemini model. Last error: {last_error}"
                        logger.error(error_msg)
                        logger.error("Please check:")
                        logger.error("1. Your GEMINI_API_KEY is valid and has proper permissions")
                        logger.error("2. The API key has access to Generative AI models")
                        logger.error("3. Try upgrading google-generativeai: pip install --upgrade google-generativeai")
                        raise Exception(error_msg)
                else:
                    self.use_rest_api = False
                        
            except ImportError:
                logger.error("google-generativeai package not installed. Install with: pip install google-generativeai")
                self.enabled = False
            except Exception as e:
                logger.error(f"Error initializing Gemini API: {str(e)}")
                logger.error("Gemini API is REQUIRED but failed to initialize. Please check your API key and model availability.")
                self.enabled = False
                raise  # Re-raise to make it clear Gemini failed
    
    def analyze_column_semantics(
        self,
        column_name: str,
        sample_values: List[Any],
        detected_type: str,
        user_definition: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use Gemini to analyze column semantics.
        
        Args:
            column_name: Name of the column
            sample_values: Sample values from the column
            detected_type: Detected type from statistical analysis
            user_definition: User-provided definition
            
        Returns:
            Dictionary with semantic analysis results
        """
        if not self.enabled:
            return {
                'semantic_type': 'unknown',
                'description': None,
                'confidence': 0.0,
                'suggested_normalized_name': column_name.lower()
            }
        
        try:
            # Prepare prompt
            sample_str = ', '.join([str(v) for v in sample_values[:20]])
            
            prompt = f"""You are a data schema expert analyzing a database column. Provide detailed semantic understanding.

Column Name: {column_name}
Detected Type: {detected_type}
Sample Values: {sample_str}
User Definition: {user_definition if user_definition else 'None'}

Analyze and provide:
1. Semantic type - Be specific (e.g., 'product_id', 'product_name', 'production_date', 'quantity_kg', 'unit_cost_rupees', 'machine_line', 'quality_score', 'supplier_code', etc.)
2. Detailed description - Explain what this column represents in business/domain terms
3. Suggested normalized column name - Use lowercase snake_case (e.g., 'product_id', 'production_date', 'unit_cost')
4. Confidence level - 0.0 to 1.0 based on how certain you are
5. Domain category - One of: 'identifier', 'date_time', 'measurement', 'categorical', 'textual', 'financial', 'quality', 'location', 'temporal', 'other'
6. Potential relationships - List other column names this might relate to (e.g., if this is 'product_id', it might relate to 'product_name', 'product_category')

Respond ONLY in valid JSON format (no markdown, no extra text):
{{
    "semantic_type": "specific_semantic_type",
    "description": "detailed description",
    "suggested_normalized_name": "normalized_name",
    "confidence": 0.85,
    "domain_category": "category",
    "potential_relationships": ["column1", "column2"]
}}"""

            # Use REST API if SDK failed, otherwise use SDK
            if hasattr(self, 'use_rest_api') and self.use_rest_api:
                # Use REST API directly
                rest_url = f"{self.rest_api_url}?key={self.api_key}"
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                }
                response_obj = requests.post(rest_url, json=payload, timeout=30)
                if response_obj.status_code != 200:
                    raise Exception(f"REST API error {response_obj.status_code}: {response_obj.text[:200]}")
                response_data = response_obj.json()
                if 'candidates' not in response_data or not response_data['candidates']:
                    raise Exception("Invalid REST API response")
                response_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
            else:
                # Use SDK
                response = self.model.generate_content(prompt)
                if not response or not hasattr(response, 'text') or not response.text:
                    raise Exception("Invalid response from Gemini SDK")
                response_text = response.text.strip()
            
            # Try to extract JSON
            import json
            try:
                # Remove markdown code blocks if present
                if '```json' in response_text:
                    response_text = response_text.split('```json')[1].split('```')[0].strip()
                elif '```' in response_text:
                    response_text = response_text.split('```')[1].split('```')[0].strip()
                
                result = json.loads(response_text)
                return {
                    'semantic_type': result.get('semantic_type', 'unknown'),
                    'description': result.get('description', ''),
                    'suggested_normalized_name': result.get('suggested_normalized_name', column_name.lower()),
                    'confidence': float(result.get('confidence', 0.5))
                }
            except json.JSONDecodeError:
                # Fallback: try to extract information from text
                return {
                    'semantic_type': 'unknown',
                    'description': response_text[:200] if response_text else None,
                    'suggested_normalized_name': column_name.lower(),
                    'confidence': 0.5
                }
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in Gemini analysis for column {column_name}: {error_msg}")
            
            # If SDK fails, try switching to REST API
            if ("404" in error_msg or "not found" in error_msg.lower() or "v1beta" in error_msg.lower()) and not (hasattr(self, 'use_rest_api') and self.use_rest_api):
                try:
                    logger.info("Attempting to switch to REST API for column analysis...")
                    rest_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
                    test_payload = {"contents": [{"parts": [{"text": "test"}]}]}
                    test_resp = requests.post(rest_url, json=test_payload, timeout=5)
                    if test_resp.status_code == 200:
                        logger.info("Switched to REST API successfully")
                        self.use_rest_api = True
                        self.rest_api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
                        # Retry the call
                        return self.analyze_column_semantics(column_name, sample_values, detected_type, user_definition)
                except Exception as rest_error:
                    logger.error(f"REST API switch also failed: {str(rest_error)}")
            
            return {
                'semantic_type': 'unknown',
                'description': None,
                'confidence': 0.0,
                'suggested_normalized_name': column_name.lower(),
                'error': error_msg
            }
    
    def analyze_relationships(
        self,
        columns: List[Dict[str, Any]],
        sample_data: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Use Gemini to detect relationships between columns.
        
        Args:
            columns: List of column schemas
            sample_data: Sample rows of data
            
        Returns:
            List of detected relationships
        """
        if not self.enabled or not hasattr(self, 'model') or self.model is None:
            return []
        
        # Wrap in try-except to handle API errors gracefully
        try:
            # Prepare column information with full context
            col_info = []
            for col in columns:
                col_name = col.get('name', col.get('column_name', ''))
                # Extract file, sheet, column from format "file::sheet::column"
                parts = col_name.split('::') if '::' in col_name else ['', '', col_name]
                col_info.append({
                    'name': col_name,
                    'file': parts[0] if len(parts) > 0 else '',
                    'sheet': parts[1] if len(parts) > 1 else '',
                    'column': parts[2] if len(parts) > 2 else col_name,
                    'type': col.get('type', col.get('detected_type', 'unknown')),
                    'user_definition': col.get('user_definition', '')
                })
            
            # Extract file names from column names (format: "file::sheet::column")
            file_names = set()
            for col in columns:
                col_name = col.get('name', col.get('column_name', ''))
                if '::' in col_name:
                    file_names.add(col_name.split('::')[0])
            
            prompt = f"""You are an expert data architect and relationship analyst. Analyze these database columns across multiple files and identify ALL meaningful relationships with detailed insights.

CONTEXT:
- You are analyzing columns from {len(file_names)} file(s): {', '.join(file_names) if file_names else 'multiple files'}
- Focus on CROSS-FILE relationships, within-file relationships, and data flow patterns
- Consider business logic, data dependencies, and semantic connections

COLUMNS INFORMATION:
{json.dumps(col_info, indent=2)}

SAMPLE DATA (for context and pattern detection):
{json.dumps(sample_data[:10] if sample_data else [], indent=2) if sample_data else 'None'}

ANALYZE AND IDENTIFY ALL RELATIONSHIPS:

1. FOREIGN KEY: Direct references between tables/files
   - Example: Material_Code in inventory_logs.csv → Material_Code in production_logs.csv
   - Include cardinality: one-to-one, one-to-many, many-to-many

2. HIERARCHICAL: Parent-child, organizational, or classification relationships
   - Example: Production_Line → Machine_ID → Station_Number
   - Example: Category → Subcategory → Product_Type

3. TEMPORAL: Time-based sequences and dependencies
   - Example: Start_Date → End_Date, Created_Date → Updated_Date
   - Example: Production_Date → Quality_Check_Date → Shipment_Date

4. CALCULATED/DERIVED: Mathematical or computational relationships
   - Example: Opening_Stock + Received - Consumption - Wastage = Closing_Stock
   - Example: Unit_Cost × Quantity = Total_Cost
   - Include the formula if possible

5. AGGREGATION: Summary or rollup relationships
   - Example: Daily_Production → Weekly_Production → Monthly_Production
   - Example: Item_Level → Category_Level → Department_Level

6. COMPOSITION: Part-of relationships
   - Example: Order_ID contains Order_Items, Batch_ID contains Batch_Details

7. DEPENDENCY: Data flow and process dependencies
   - Example: Raw_Material_Received → Production_Started → Quality_Checked → Shipped
   - Example: Material_Code must exist before Production can start

8. SEMANTIC: Business/conceptual relationships
   - Example: Supplier → Material → Production → Quality_Control
   - Example: Date → Batch_ID → Production_Run → Quality_Score

9. CATEGORICAL: Classification and status relationships
   - Example: Status → Status_Code → Status_Description
   - Example: Type → Category → Subcategory

10. CROSS-FILE FLOWS: Data movement between files
    - Example: Material inventory → Production consumption → Quality control → Final output

FOR EACH RELATIONSHIP, PROVIDE:
- type: One of: foreign_key, hierarchical, temporal, calculated, aggregation, composition, dependency, semantic, categorical, cross_file_flow
- source_column: Full column identifier (file::sheet::column)
- target_column: Full column identifier (file::sheet::column)  
- direction: "source_to_target", "bidirectional", or "many_to_many"
- cardinality: "one-to-one", "one-to-many", "many-to-one", "many-to-many" (if applicable)
- description: Detailed 2-3 sentence explanation of the relationship, business meaning, and importance
- confidence: 0.0-1.0 (be conservative - higher only if strongly supported by data patterns)
- evidence: Specific evidence from column names, data patterns, or business logic
- strength: "strong", "medium", or "weak" (relationship strength)
- impact: "critical", "important", or "informational" (business impact)
- formula: If calculated type, include the mathematical formula
- business_meaning: What this relationship means in business terms

PRIORITIZE:
- Cross-file relationships (most valuable)
- High-confidence relationships (>0.7)
- Critical business relationships
- Data flow and dependency chains

Respond ONLY in valid JSON format (no markdown, no extra text):
{{
    "relationships": [
        {{
            "type": "foreign_key",
            "source_column": "inventory_logs.csv::Sheet1::Material_Code",
            "target_column": "production_logs.csv::Sheet1::Material_Code",
            "direction": "source_to_target",
            "cardinality": "one-to-many",
            "description": "Material codes in inventory logs reference materials used in production. Each material can be used in multiple production runs, creating a one-to-many relationship.",
            "confidence": 0.92,
            "evidence": "Column names match exactly, both are ID types, production logically depends on inventory",
            "strength": "strong",
            "impact": "critical",
            "business_meaning": "Tracks which materials from inventory are consumed in production processes"
        }}
    ]
}}"""

            # Make API call - use REST API if SDK failed, otherwise use SDK
            try:
                if hasattr(self, 'use_rest_api') and self.use_rest_api:
                    # Use REST API directly
                    rest_url = f"{self.rest_api_url}?key={self.api_key}"
                    payload = {
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }]
                    }
                    response_obj = requests.post(rest_url, json=payload, timeout=30)
                    if response_obj.status_code != 200:
                        raise Exception(f"REST API error {response_obj.status_code}: {response_obj.text[:200]}")
                    response_data = response_obj.json()
                    if 'candidates' not in response_data or not response_data['candidates']:
                        raise Exception("Invalid REST API response")
                    response_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
                else:
                    # Use SDK
                    response = self.model.generate_content(prompt)
                    if not response or not hasattr(response, 'text'):
                        raise Exception("Invalid response from Gemini API")
                    response_text = response.text.strip()
                    if not response_text:
                        raise Exception("Empty response from Gemini API")
            except Exception as api_error:
                error_msg = str(api_error)
                logger.error(f"Gemini API call failed: {error_msg}")
                
                # Don't disable - let it retry, but log the error
                if "404" in error_msg or "not found" in error_msg.lower() or "v1beta" in error_msg.lower():
                    logger.error("CRITICAL: Gemini model not found. Trying to switch to REST API...")
                    # Try to switch to REST API
                    try:
                        rest_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
                        test_payload = {"contents": [{"parts": [{"text": "test"}]}]}
                        test_resp = requests.post(rest_url, json=test_payload, timeout=5)
                        if test_resp.status_code == 200:
                            logger.info("Switched to REST API successfully")
                            self.use_rest_api = True
                            self.rest_api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
                            # Retry the call
                            return self.analyze_relationships(columns, sample_data)
                    except:
                        pass
                return []
            
            # Parse JSON (json imported at top of file)
            try:
                if '```json' in response_text:
                    response_text = response_text.split('```json')[1].split('```')[0].strip()
                elif '```' in response_text:
                    response_text = response_text.split('```')[1].split('```')[0].strip()
                
                result = json.loads(response_text)
                return result.get('relationships', [])
            except json.JSONDecodeError:
                logger.warning("Could not parse Gemini relationship analysis response")
                return []
        
        except Exception as e:
            logger.error(f"Error in Gemini relationship analysis: {str(e)}")
            return []

