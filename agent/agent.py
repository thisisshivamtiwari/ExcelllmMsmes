"""
LangChain Agent for Excel Data Analysis.
Supports both Gemini and Groq APIs with optimized prompts from prompt_engineering.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
import json

# Try to use langchain-groq
try:
    from langchain_groq import ChatGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    ChatGroq = None

# Try to use langchain-google-genai for Gemini
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    ChatGoogleGenerativeAI = None

# Add prompt_engineering to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

logger = logging.getLogger(__name__)

try:
    from prompt_engineering.llama4_maverick_optimizer import EnhancedPromptEngineer
    PROMPT_ENGINEERING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Prompt engineering module not available: {e}")
    PROMPT_ENGINEERING_AVAILABLE = False
    EnhancedPromptEngineer = None


class ExcelAgent:
    """LangChain agent for Excel data analysis."""
    
    def __init__(
        self,
        tools: List[Tool],
        provider: str = "groq",  # "groq" or "gemini"
        model_name: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None
    ):
        """
        Initialize Excel Agent with Gemini or Groq API.
        
        Args:
            tools: List of LangChain tools
            provider: "groq" or "gemini"
            model_name: Model name (optional, uses defaults if not provided)
            groq_api_key: Groq API key (if not in env)
            gemini_api_key: Gemini API key (if not in env)
        """
        self.tools = tools
        self.provider = provider.lower()
        
        # Initialize Enhanced Prompt Engineer
        self.prompt_engineer = None
        if PROMPT_ENGINEERING_AVAILABLE:
            try:
                self.prompt_engineer = EnhancedPromptEngineer(model_id=model_name or "default")
                logger.info("✓ Enhanced Prompt Engineer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Enhanced Prompt Engineer: {e}")
        
        # Initialize LLM based on provider
        if self.provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ImportError("langchain-google-genai not installed. Install with: pip install langchain-google-genai")
            
            gemini_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
            if not gemini_key:
                raise ValueError("GEMINI_API_KEY not found. Please set it in .env file")
            
            # Default Gemini model
            self.model_name = model_name or "gemini-2.5-flash"
            
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=gemini_key,
                temperature=0.1,
                max_tokens=2048
            )
            logger.info(f"✓ Initialized Gemini LLM: {self.model_name}")
            
        elif self.provider == "groq":
            if not GROQ_AVAILABLE:
                raise ImportError("langchain-groq not installed. Install with: pip install langchain-groq")
            
            groq_key = groq_api_key or os.getenv("GROQ_API_KEY")
            if not groq_key:
                raise ValueError("GROQ_API_KEY not found. Please set it in .env file")
            
            # Validate API key format (Groq keys typically start with 'gsk_')
            if not groq_key.startswith('gsk_'):
                logger.warning(f"API key doesn't start with 'gsk_' - this might not be a valid Groq API key")
            
            # Default Groq model
            self.model_name = model_name or "meta-llama/llama-4-maverick-17b-128e-instruct"
            
            self.llm = ChatGroq(
                model=self.model_name,
                groq_api_key=groq_key,
                temperature=0.1,
                max_tokens=2048
            )
            logger.info(f"✓ Initialized Groq LLM: {self.model_name}")
        else:
            raise ValueError(f"Unknown provider: {provider}. Must be 'groq' or 'gemini'")
        
        # Create ReAct prompt
        self.prompt = self._create_react_prompt()
        
        # Create agent
        self.agent = create_react_agent(self.llm, tools, self.prompt)
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10
        )
    
    def _create_react_prompt(self) -> PromptTemplate:
        """Create ReAct prompt template with enhanced prompts from prompt_engineering."""
        # Use enhanced prompt if available
        if self.prompt_engineer:
            try:
                # Get enhanced methodology prompt structure
                enhanced_template = """You are an expert data analyst assistant for MSME manufacturing Excel data analysis.

You have access to the following tools:
{tools}

## Your Capabilities:
- Semantic search to find relevant columns and files
- Data retrieval with preprocessing (dates, numbers, etc.)
- Calculations (sum, avg, count, min, max, median, std)
- Trend analysis over time periods
- Comparative analysis between entities
- KPI calculations (OEE, FPY, defect rates)
- Graph/chart generation (line, bar, pie, scatter, area, heatmap)

## Database Schema Context:
You are working with manufacturing data including:
- production_logs: Daily production records with targets, actuals, downtime
- quality_control: Quality inspections, defects, rework counts
- maintenance_logs: Machine maintenance, breakdowns, costs
- inventory_logs: Material stock, consumption, wastage

## Instructions:
Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do (use chain-of-thought reasoning)
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action (use JSON format for structured inputs)
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

## Best Practices:
1. **Start with semantic search** to find relevant columns/files for the query
2. **Retrieve actual data** using the excel_data_retriever tool with appropriate filters
3. **For large datasets (>100 rows)**: Use summary statistics (mean * count = total) instead of passing all data to calculator
4. **Perform calculations** using data_calculator ONLY for small datasets (<100 rows). For large datasets, use summary statistics from excel_data_retriever response
5. **Analyze trends** using trend_analyzer for time-based questions
6. **Compare entities** using comparative_analyzer for "which is best/worst" questions
7. **Calculate KPIs** using kpi_calculator for manufacturing metrics
8. **Generate visualizations** using graph_generator for chart/graph requests:
   - Line charts: time series (production over time, trends)
   - Bar charts: comparisons (production by line, defects by product)
   - Pie charts: distributions (defect types, product distribution)
   - Scatter charts: correlations (production vs downtime)
   - Area charts: filled trends (cumulative production)
   - Heatmaps: 2D matrices (production by line and shift)
9. **Provide clear reasoning** - show your thought process
10. **Include specific numbers** - always provide quantitative answers when possible
11. **Handle edge cases** - if data is missing or insufficient, explain clearly

## IMPORTANT: Large Dataset Handling
- If excel_data_retriever returns "truncated": true and "use_summary_stats": true, DO NOT pass all data to calculator
- Instead, use the summary statistics: mean * count = total
- Example: If summary shows mean=272.39 and count=872, calculate: 272.39 * 872 = 237,525
- This prevents JSON parsing errors and provides accurate results

## Response Format:
- Be concise but complete
- Include relevant numbers and units
- Explain your reasoning
- If you cannot find the answer, explain why

Begin!

Question: {input}
Thought: {agent_scratchpad}"""
                return PromptTemplate.from_template(enhanced_template)
            except Exception as e:
                logger.warning(f"Failed to use enhanced prompt: {e}, using default")
        
        # Fallback to default prompt
        template = """You are an expert data analyst assistant for manufacturing Excel data.

You have access to the following tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

When answering:
1. Use semantic search to find relevant columns/files first
2. Retrieve data using the retrieved column/file information
3. Perform calculations or analysis as needed
4. Provide clear, structured answers with reasoning
5. Include relevant numbers and context
6. If you cannot find the answer, say so clearly

Begin!

Question: {input}
Thought: {agent_scratchpad}"""
        
        return PromptTemplate.from_template(template)
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        Process a query using the agent.
        
        Args:
            question: Natural language question
            
        Returns:
            Dictionary with answer and metadata
        """
        try:
            result = self.agent_executor.invoke({"input": question})
            
            return {
                "success": True,
                "question": question,
                "answer": result.get("output", ""),
                "intermediate_steps": [
                    {
                        "action": str(step[0].tool) if step[0] else None,
                        "action_input": str(step[0].tool_input) if step[0] else None,
                        "observation": str(step[1]) if len(step) > 1 else None
                    }
                    for step in result.get("intermediate_steps", [])
                ]
            }
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                "success": False,
                "question": question,
                "error": str(e),
                "answer": f"I encountered an error while processing your query: {str(e)}"
            }

