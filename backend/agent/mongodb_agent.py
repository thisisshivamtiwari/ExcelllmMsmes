"""
MongoDB-based LangChain Agent
Orchestrates deterministic tools for user queries
"""

import os
import json
import logging
import uuid
import colorsys
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from langchain_core.language_models import BaseLanguageModel

# Import tools
from tools.mongodb_tools import (
    table_loader,
    agg_helper,
    timeseries_analyzer,
    compare_entities,
    calc_eval,
    statistical_summary,
    list_user_files,
    rank_entities
)

logger = logging.getLogger(__name__)


def create_tool_wrappers(user_id: str, file_id: Optional[str] = None) -> List[Tool]:
    """
    Create LangChain Tool wrappers for MongoDB tools.
    
    Args:
        user_id: User ID for multi-tenant filtering
        file_id: Optional file ID (can be None for multi-file queries)
    
    Returns:
        List of LangChain Tool objects
    """
    
    def wrap_table_loader(query: str) -> str:
        """Load table sample and schema. Use format: file_id|table_name|filters_json|fields_json|limit"""
        try:
            parts = query.split("|")
            file_id_param = parts[0].strip() if len(parts) > 0 and parts[0].strip() else file_id
            table_name = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "Sheet1"
            filters = json.loads(parts[2]) if len(parts) > 2 and parts[2].strip() else None
            fields = json.loads(parts[3]) if len(parts) > 3 and parts[3].strip() else None
            limit = int(parts[4]) if len(parts) > 4 and parts[4].strip() else 100
            
            if not file_id_param:
                return json.dumps({"ok": False, "error": "file_id required"})
            
            result = table_loader(user_id, file_id_param, table_name, filters, fields, limit)
            return json.dumps(result, default=str)
        except json.JSONDecodeError as e:
            return json.dumps({"ok": False, "error": f"JSON decode error: {str(e)}"})
        except ValueError as e:
            return json.dumps({"ok": False, "error": f"Value error: {str(e)}"})
        except Exception as e:
            import traceback
            logger.error(f"Error in wrap_table_loader: {str(e)}\n{traceback.format_exc()}")
            return json.dumps({"ok": False, "error": str(e)})
    
    def wrap_agg_helper(query: str) -> str:
        """Run aggregations. Use format: file_id|table_name|filters_json|metrics_json"""
        try:
            parts = query.split("|")
            file_id_param = parts[0] if len(parts) > 0 else file_id
            table_name = parts[1] if len(parts) > 1 else "Sheet1"
            filters = json.loads(parts[2]) if len(parts) > 2 and parts[2] else None
            metrics = json.loads(parts[3]) if len(parts) > 3 else []
            
            if not file_id_param:
                return json.dumps({"error": "file_id required"})
            
            result = agg_helper(user_id, file_id_param, table_name, filters, metrics)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
    
    def wrap_timeseries_analyzer(query: str) -> str:
        """Analyze time series. Use format: file_id|table_name|time_col|metric_col|freq|agg|start|end"""
        try:
            parts = query.split("|")
            file_id_param = parts[0] if len(parts) > 0 else file_id
            table_name = parts[1] if len(parts) > 1 else "Sheet1"
            time_col = parts[2] if len(parts) > 2 else None
            metric_col = parts[3] if len(parts) > 3 else None
            freq = parts[4] if len(parts) > 4 else "month"
            agg = parts[5] if len(parts) > 5 else "sum"
            start = datetime.fromisoformat(parts[6]) if len(parts) > 6 and parts[6] else None
            end = datetime.fromisoformat(parts[7]) if len(parts) > 7 and parts[7] else None
            
            if not file_id_param or not time_col or not metric_col:
                return json.dumps({"error": "file_id, time_col, and metric_col required"})
            
            result = timeseries_analyzer(user_id, file_id_param, table_name, time_col, metric_col, freq, agg, start, end)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
    
    def wrap_compare_entities(query: str) -> str:
        """Compare two entities. Use format: file_id|table_name|key_col|metric_col|entity_a|entity_b|agg|filters_json"""
        try:
            parts = query.split("|")
            file_id_param = parts[0] if len(parts) > 0 else file_id
            table_name = parts[1] if len(parts) > 1 else "Sheet1"
            key_col = parts[2] if len(parts) > 2 else None
            metric_col = parts[3] if len(parts) > 3 else None
            entity_a = parts[4] if len(parts) > 4 else None
            entity_b = parts[5] if len(parts) > 5 else None
            agg = parts[6] if len(parts) > 6 else "sum"
            filters = json.loads(parts[7]) if len(parts) > 7 and parts[7] else None
            
            if not file_id_param or not key_col or not metric_col or not entity_a or not entity_b:
                return json.dumps({"error": "file_id, key_col, metric_col, entity_a, and entity_b required"})
            
            result = compare_entities(user_id, file_id_param, table_name, key_col, metric_col, entity_a, entity_b, agg, filters)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
    
    def wrap_calc_eval(query: str) -> str:
        """Evaluate mathematical expression. Use format: expression_string"""
        try:
            result = calc_eval(query)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
    
    def wrap_statistical_summary(query: str) -> str:
        """Get statistical summary. Use format: file_id|table_name|columns_json|filters_json"""
        try:
            parts = query.split("|")
            file_id_param = parts[0] if len(parts) > 0 else file_id
            table_name = parts[1] if len(parts) > 1 else "Sheet1"
            columns = json.loads(parts[2]) if len(parts) > 2 and parts[2] else []
            filters = json.loads(parts[3]) if len(parts) > 3 and parts[3] else None
            
            if not file_id_param or not columns:
                return json.dumps({"error": "file_id and columns required"})
            
            result = statistical_summary(user_id, file_id_param, table_name, columns, filters)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
    
    def wrap_list_user_files(query: str) -> str:
        """List all files available for the user. No parameters needed."""
        try:
            result = list_user_files(user_id)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
    
    def wrap_rank_entities(query: str) -> str:
        """Rank entities by aggregated metric. Use format: file_id|table_name|key_col|metric_col|agg|n|order|filters_json"""
        try:
            parts = query.split("|")
            file_id_param = parts[0] if len(parts) > 0 else file_id
            table_name = parts[1] if len(parts) > 1 else "Sheet1"
            key_col = parts[2] if len(parts) > 2 else None
            metric_col = parts[3] if len(parts) > 3 else None
            agg = parts[4] if len(parts) > 4 else "sum"
            n = int(parts[5]) if len(parts) > 5 and parts[5] else 5
            order = parts[6] if len(parts) > 6 else "desc"
            filters = json.loads(parts[7]) if len(parts) > 7 and parts[7] else None
            
            if not file_id_param or not key_col or not metric_col:
                return json.dumps({"error": "file_id, key_col, and metric_col required"})
            
            result = rank_entities(user_id, file_id_param, table_name, key_col, metric_col, agg, n, order, filters)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
    
    def wrap_get_date_range(query: str) -> str:
        """Get date range information for a time column. Use format: file_id|table_name|time_col"""
        try:
            parts = query.split("|")
            file_id_param = parts[0] if len(parts) > 0 else file_id
            table_name = parts[1] if len(parts) > 1 else "Sheet1"
            time_col = parts[2] if len(parts) > 2 else None
            
            if not file_id_param or not time_col:
                return json.dumps({"error": "file_id and time_col required"})
            
            from tools.mongodb_tools import get_date_range
            result = get_date_range(user_id, file_id_param, table_name, time_col)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
    
    tools = [
        Tool(
            name="list_user_files",
            func=wrap_list_user_files,
            description="""List all files available for the user.
            Input: (no parameters needed, just call with empty string or "list")
            Returns: List of files with file_id, filename, file_type, table_names, and row_count.
            ALWAYS call this FIRST if you don't know which file_id to use."""
        ),
        Tool(
            name="table_loader",
            func=wrap_table_loader,
            description=f"""Load table sample and schema from MongoDB. 
            Input format: file_id|table_name|filters_json|fields_json|limit
            {"Default file_id: " + file_id if file_id else "file_id is REQUIRED - get it from question context"}
            Returns: schema, sample_rows, row_count. Always call this first to inspect available columns."""
        ),
        Tool(
            name="agg_helper",
            func=wrap_agg_helper,
            description="""Run deterministic aggregations (sum, avg, count, min, max, median).
            Input format: file_id|table_name|filters_json|metrics_json
            metrics_json format: [{"op":"sum","col":"column_name","alias":"result_name"}]
            Returns: aggregated values as Decimal for accuracy.
            USE THIS FOR: Questions asking "What is the mean/average/total/sum/count/min/max/median of X?"
            Examples: "What is the mean of opening stock?", "What is the total revenue?", "What is the average downtime?"
            DO NOT use this for "which entity has highest" questions - use rank_entities instead."""
        ),
        Tool(
            name="timeseries_analyzer",
            func=wrap_timeseries_analyzer,
            description="""Analyze time series data with trend calculation.
            Input format: file_id|table_name|time_col|metric_col|freq|agg|start|end
            freq: day|week|month|year, agg: sum|avg|count|min|max
            Returns: series data and slope/trend. Use for time-based questions."""
        ),
        Tool(
            name="compare_entities",
            func=wrap_compare_entities,
            description="""Compare two entities side-by-side.
            Input format: file_id|table_name|key_col|metric_col|entity_a|entity_b|agg|filters_json
            Returns: values for both entities and percent difference. Use for comparison questions."""
        ),
        Tool(
            name="statistical_summary",
            func=wrap_statistical_summary,
            description="""Get statistical summary (min/max/mean/median/std) for numeric columns.
            Input format: file_id|table_name|columns_json|filters_json
            Returns: statistical measures (min, max, mean, median, std) for each column.
            USE THIS FOR: Questions asking for multiple statistics at once (e.g., "What are the statistics for X?")
            Examples: "Get statistics for downtime", "What are the min/max/mean for opening stock?"
            For single statistics (just mean, just total), use agg_helper instead."""
        ),
        Tool(
            name="calc_eval",
            func=wrap_calc_eval,
            description="""Safe deterministic calculator using Decimal precision.
            Input format: mathematical expression (e.g., "123.45 + 67.89")
            Returns: calculated value. Use for final arithmetic after getting values from agg_helper."""
        ),
        Tool(
            name="rank_entities",
            func=wrap_rank_entities,
            description="""Rank entities by aggregated metric (top N or bottom N).
            Input format: file_id|table_name|key_col|metric_col|agg|n|order|filters_json
            key_col: Entity identifier column (e.g., "Product", "Material_Name", "Supplier", "Operator")
            metric_col: Metric column to aggregate (e.g., "Sales", "Consumption_Kg", "Actual_Quantity")
            agg: Aggregation operation ("sum", "avg", "count", "min", "max")
            n: Number of top/bottom entities (default: 5)
            order: "desc" for top N (highest), "asc" for bottom N (lowest)
            Returns: Ranked list of entities with their aggregated values.
            USE THIS FOR: Questions asking "Which entity has the highest/lowest X?" or "Top N entities by X"
            Examples: "Which supplier provided the most?", "Which operator had the highest total?", "Top 5 products by sales"
            DO NOT use this for simple aggregation questions like "What is the mean of X?" - use agg_helper instead."""
        ),
        Tool(
            name="get_date_range",
            func=wrap_get_date_range,
            description="""Get date range information for a time column (min date, max date, row count, span in days).
            Input format: file_id|table_name|time_col
            Returns: min_date, max_date, row_count, span_days. Use to check if data is too large before analyzing."""
        )
    ]
    
    return tools


def create_agent_prompt() -> PromptTemplate:
    """Create system prompt for agent"""
    
    prompt = """You are an expert data analyst assistant. Your role is to answer questions about data stored in MongoDB using ONLY the provided tools.

CRITICAL RULES:
1. ALWAYS call table_loader FIRST to inspect schema and available columns
2. NEVER compute numbers in your text - ALWAYS use agg_helper, timeseries_analyzer, or calc_eval
3. For time-based questions, use timeseries_analyzer
4. For comparison questions, use compare_entities
5. For final arithmetic, use calc_eval (never do math yourself)
6. If required fields are missing, respond with: insufficient_data: [list_missing_columns]
7. Always include provenance in your final answer

TOOL USAGE EXAMPLES:

Example 1: "What is the total revenue?"
- Step 1: table_loader("file123|Sheet1|||100") to see columns
- Step 2: agg_helper("file123|Sheet1||[{{\"op\":\"sum\",\"col\":\"revenue\",\"alias\":\"total_revenue\"}}]")
- Step 3: Extract total_revenue from result and present answer

Example 2: "Show monthly sales trend"
- Step 1: table_loader to find date and sales columns
- Step 2: timeseries_analyzer("file123|Sheet1|date|sales|month|sum||")
- Step 3: Present series data and trend

Example 3: "Compare Product A vs Product B sales"
- Step 1: table_loader to find product and sales columns
- Step 2: compare_entities("file123|Sheet1|product|sales|Product A|Product B|sum|")
- Step 3: Present comparison with percent difference

Example 4: "What is 15% of total revenue?"
- Step 1: agg_helper to get total_revenue
- Step 2: calc_eval("total_revenue * 0.15")
- Step 3: Present calculated result

RESPONSE FORMAT:
- Provide a clear, concise answer
- Include numeric values with units if applicable
- Mention which tools were used
- Include provenance (mongo_pipeline, matched_row_count) when available

Current question: {{input}}

Available tools: {{tools}}

Tool names: {{tool_names}}

{agent_scratchpad}"""
    
    return PromptTemplate.from_template(prompt)


def create_agent_executor(
    llm: BaseLanguageModel,
    user_id: str,
    file_id: Optional[str] = None,
    max_iterations: int = 15
) -> AgentExecutor:
    """
    Create LangChain agent executor with MongoDB tools.
    
    Args:
        llm: Language model instance
        user_id: User ID for multi-tenant filtering
        file_id: Optional file ID
        max_iterations: Maximum agent iterations
    
    Returns:
        AgentExecutor instance
    """
    tools = create_tool_wrappers(user_id, file_id)
    
    # Create ReAct prompt with required variables
    # Build context about file_id if available
    file_context = ""
    if file_id:
        file_context = f"\n\nIMPORTANT: The file_id to use is: {file_id}\nUse this EXACT file_id in all tool calls. Do NOT use any other file_id."
    else:
        file_context = "\n\nIMPORTANT: No file_id provided. You MUST call list_user_files FIRST to discover available files, then use a real file_id from the results."
    
    react_prompt = PromptTemplate.from_template(f"""Answer the following questions as best you can. You have access to the following tools:

{{tools}}
{file_context}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{{tool_names}}]
Action Input: the input to the action (use EXACT format: file_id|table_name|...)
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

CRITICAL RULES:
1. If you don't know which file_id to use, ALWAYS call list_user_files FIRST to see available files
2. After getting files from list_user_files, pick the most relevant file_id based on the question
3. ALWAYS call table_loader FIRST to inspect schema (after you have the correct file_id)
4. NEVER compute numbers yourself - use agg_helper, timeseries_analyzer, statistical_summary, or calc_eval
5. Include provenance in your answer
6. If file_id is provided above, use that EXACT file_id - do NOT invent or guess file_ids like "12345" or "1"
7. Default table_name is "Sheet1" unless specified otherwise
8. If table_loader returns "no_rows", you're using the wrong file_id - call list_user_files again and try a different file_id
9. NEVER use placeholder file_ids - always use real file_ids from list_user_files results
10. For time series questions requesting charts, ensure the response includes chart_config with chart_type, data, and options

TOOL SELECTION GUIDE - CHOOSE THE RIGHT TOOL BASED ON QUESTION TYPE:

A. For AGGREGATION questions (mean, average, total, sum, count, min, max, median):
   → Use agg_helper
   Examples: "What is the mean of X?", "What is the total Y?", "What is the average Z?"
   Format: file_id|table_name|filters_json|metrics_json
   metrics_json: [{{{{"op":"avg","col":"column_name","alias":"result"}}}}] for mean/average
                 [{{{{"op":"sum","col":"column_name","alias":"result"}}}}] for total/sum
                 [{{{{"op":"count","col":"column_name","alias":"result"}}}}] for count
                 [{{{{"op":"min","col":"column_name","alias":"result"}}}}] for minimum
                 [{{{{"op":"max","col":"column_name","alias":"result"}}}}] for maximum
                 [{{{{"op":"median","col":"column_name","alias":"result"}}}}] for median

B. For STATISTICAL SUMMARY questions (multiple stats at once):
   → Use statistical_summary
   Examples: "What are the statistics for X?", "Get min/max/mean for Y"
   Format: file_id|table_name|columns_json|filters_json

C. For RANKING/TOP N questions (which entity has highest/lowest):
   → Use rank_entities ONLY when question asks "which", "who", "top N", "bottom N"
   Examples: "Which supplier provided the most?", "Top 5 products by sales"
   Format: file_id|table_name|key_col|metric_col|agg|n|order|filters_json
   DO NOT use rank_entities for simple aggregation questions like "What is the mean?"

D. For COMPARISON questions (compare two specific entities):
   → Use compare_entities
   Examples: "Compare Product A vs Product B", "How does X compare to Y?"
   Format: file_id|table_name|key_col|metric_col|entity_a|entity_b|agg|filters_json

E. For TIME SERIES/TREND questions:
   → Use timeseries_analyzer
   Examples: "Show sales over time", "What is the trend of X?"
   Format: file_id|table_name|time_col|metric_col|freq|agg|start|end

F. For ARITHMETIC calculations (after getting values):
   → Use calc_eval
   Examples: "What is 15% of total?", "Calculate X * Y"
   Format: mathematical expression

IMPORTANT: 
- Questions asking "What is the mean/average/total of X?" should use agg_helper, NOT rank_entities
- Questions asking "Which entity has the highest X?" should use rank_entities
- Always read the question carefully and match it to the correct tool category above

Question: {{input}}
Thought: {{agent_scratchpad}}""")
    
    agent = create_react_agent(llm, tools, react_prompt)
    
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=max_iterations,
        handle_parsing_errors="Check your output and make sure it conforms to the format instructions. If you see an error, retry with the correct format.",
        return_intermediate_steps=True,
        max_execution_time=120  # 2 minutes max execution time
    )
    
    return executor


def get_llm_instance(provider: str = "gemini", temperature: float = 0.0):
    """
    Get LLM instance based on provider.
    
    Args:
        provider: "gemini" or "groq"
        temperature: Temperature setting (0.0 for deterministic)
    
    Returns:
        LLM instance
    """
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
        
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature,
            convert_system_message_to_human=True
        )
    
    elif provider == "groq":
        from langchain_groq import ChatGroq
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        
        model_name = os.getenv("AGENT_MODEL_NAME", "llama-4-maverick-17b-128e-instruct")
        
        return ChatGroq(
            model=model_name,
            groq_api_key=api_key,
            temperature=temperature
        )
    
    else:
        raise ValueError(f"Unknown provider: {provider}. Must be 'gemini' or 'groq'")


async def execute_agent_query(
    question: str,
    user_id: str,
    file_id: Optional[str] = None,
    provider: str = "gemini",
    max_iterations: int = 15,
    conversation_id: Optional[str] = None,
    date_range: Optional[Dict[str, Optional[str]]] = None
) -> Dict[str, Any]:
    """
    Execute agent query and return structured response.
    
    Args:
        question: User's question
        user_id: User ID
        file_id: Optional file ID
        provider: LLM provider
        max_iterations: Maximum iterations
    
    Returns:
        Structured response with answer, provenance, and metadata
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Initialize conversation context variables
    requires_date_range = False
    date_range_info = None
    conv_service = None
    
    try:
        # Handle conversation context
        try:
            from services.conversation_service import ConversationService
            conv_service = ConversationService(user_id)
            
            original_question = question
            context_question = question
            
            # If conversation_id exists, get context
            if conversation_id:
                context = await conv_service.get_conversation_context(conversation_id)
                if context:
                    # Always use the CURRENT question, not the original question from context
                    # The original_question from context is just for reference
                    original_question_from_context = context.get("original_question", question)
                    
                    # If this is a date range response, incorporate it into the CURRENT question
                    if date_range and context.get("pending_date_range"):
                        start = date_range.get("start")
                        end = date_range.get("end")
                        context_question = f"""{question}

User has provided date range:
- Start date: {start or 'not specified'}
- End date: {end or 'not specified'}

Please use this date range to filter the data and answer the question."""
                        # Update context
                        await conv_service.set_date_range(conversation_id, start, end)
                        await conv_service.add_message(conversation_id, "user", f"Date range: {start} to {end}")
                    else:
                        # Use the CURRENT question, not the original from context
                        context_question = question
                    
                    # Add current user question to conversation
                    await conv_service.add_message(conversation_id, "user", question)
            else:
                # Create new conversation
                conversation_id = await conv_service.create_conversation(question, file_id)
        except ImportError:
            logger.warning("ConversationService not available - conversation context disabled")
            conv_service = None
            context_question = question
        
        # Get LLM instance
        llm = get_llm_instance(provider, temperature=0.0)
        
        # Enhance question with file_id context if provided
        enhanced_question = context_question
        if file_id:
            enhanced_question = f"""Question: {context_question}

IMPORTANT: Use this EXACT file_id in all tool calls: {file_id}
Do NOT use any other file_id or numbers from the question text.
Default table_name is "Sheet1" unless specified otherwise."""
        else:
            # If no file_id provided, instruct agent to discover files first
            enhanced_question = f"""Question: {context_question}

IMPORTANT: You don't have a specific file_id. You MUST:
1. First call list_user_files to see what files are available
2. Then use the file_id from the list_user_files result
3. Do NOT invent or guess file_ids - always use real file_ids from list_user_files
4. Default table_name is "Sheet1" unless specified otherwise"""
        
        # Create agent executor
        executor = create_agent_executor(llm, user_id, file_id, max_iterations)
        
        # Execute query
        result = executor.invoke({"input": enhanced_question})
        
        # Extract information
        answer = result.get("output", "")
        intermediate_steps = result.get("intermediate_steps", [])
        
        # Extract tools called
        tools_called = []
        tool_outputs = {}
        
        for step in intermediate_steps:
            if len(step) >= 2:
                action = step[0]
                observation = step[1]
                
                tool_name = action.tool if hasattr(action, 'tool') else "unknown"
                tools_called.append(tool_name)
                
                # Parse tool output
                try:
                    if isinstance(observation, str):
                        tool_outputs[tool_name] = json.loads(observation)
                    else:
                        tool_outputs[tool_name] = observation
                except:
                    tool_outputs[tool_name] = str(observation)
        
        # Extract values and provenance from tool outputs
        values = {}
        provenance = {}
        chart_config = None
        
        for tool_name, output in tool_outputs.items():
            if isinstance(output, dict) and output.get("ok"):
                if output.get("result"):
                    if isinstance(output["result"], dict):
                        values.update(output["result"])
                if output.get("provenance"):
                    provenance[tool_name] = output["provenance"]
        
        # Generate chart_config for time series queries
        # Time series queries typically need charts, but check if question explicitly asks for just a number
        if "timeseries_analyzer" in tools_called:
            ts_output = tool_outputs.get("timeseries_analyzer", {})
            if isinstance(ts_output, dict) and ts_output.get("ok"):
                ts_result = ts_output.get("result", {})
                series = ts_result.get("series", [])
                if series:
                    question_lower = question.lower()
                    # Check if question explicitly asks for just a number (not a chart)
                    number_only_keywords = ["what is", "what's", "how much", "total", "sum", "average", "mean", "median"]
                    asks_for_number_only = any(keyword in question_lower for keyword in number_only_keywords) and \
                                         not any(keyword in question_lower for keyword in ["chart", "graph", "plot", "show", "visualize", "display", "trend", "over time"])
                    
                    # Only skip chart if question explicitly asks for just a number AND doesn't mention trends/visualization
                    if not asks_for_number_only:
                        # Determine chart type from question
                        chart_type = "line"
                        if "bar" in question_lower or "column" in question_lower:
                            chart_type = "bar"
                        elif "area" in question_lower:
                            chart_type = "line"  # Area charts can be rendered as filled line
                        
                        # Extract labels and data
                        labels = [s.get("period", "") for s in series]
                        data_values = [float(s.get("value", 0)) if s.get("value") is not None else 0 for s in series]
                        
                        # Determine metric name from question or tool output
                        metric_name = "Value"
                        if "production" in question_lower:
                            metric_name = "Production"
                        elif "sales" in question_lower:
                            metric_name = "Sales"
                        elif "quantity" in question_lower:
                            metric_name = "Quantity"
                        
                        chart_config = {
                            "success": True,
                            "chart_type": chart_type,
                            "title": question if len(question) < 60 else question[:57] + "...",
                            "data": {
                                "labels": labels,
                                "datasets": [{
                                    "label": metric_name,
                                    "data": data_values,
                                    "borderColor": "#3B82F6",
                                    "backgroundColor": "rgba(59, 130, 246, 0.1)" if chart_type == "line" else "#3B82F6",
                                    "borderWidth": 2,
                                    "fill": chart_type == "line",
                                    "tension": 0.4,
                                    "pointRadius": 3,
                                    "pointHoverRadius": 5
                                }]
                            },
                            "options": {
                                "responsive": True,
                                "maintainAspectRatio": False,
                                "plugins": {
                                    "title": {
                                        "display": True,
                                        "text": question if len(question) < 60 else question[:57] + "...",
                                        "font": {"size": 16}
                                    },
                                    "legend": {
                                        "display": True,
                                        "position": "top"
                                    }
                                },
                                "scales": {
                                    "x": {
                                        "title": {
                                            "display": True,
                                            "text": "Time Period"
                                        }
                                    },
                                    "y": {
                                        "beginAtZero": True,
                                        "title": {
                                            "display": True,
                                            "text": metric_name
                                        }
                                    }
                                }
                            }
                        }
        
        # Check if we need to ask for date range
        # Check timeseries_analyzer output for large datasets
        if "timeseries_analyzer" in tools_called:
            ts_output = tool_outputs.get("timeseries_analyzer", {})
            if isinstance(ts_output, dict) and ts_output.get("ok"):
                ts_result = ts_output.get("result", {})
                series = ts_result.get("series", [])
                matched_count = ts_output.get("provenance", {}).get("matched_row_count", 0)
                
                # If series has more than 100 points or matched_count > 1000, ask for date range
                if len(series) > 100 or matched_count > 1000:
                    # Try to get date range info
                    # Extract time_col and file_id from tool calls
                    time_col = None
                    for step in intermediate_steps:
                        if len(step) >= 2:
                            action = step[0]
                            if hasattr(action, 'tool') and action.tool == "timeseries_analyzer":
                                if hasattr(action, 'tool_input'):
                                    parts = action.tool_input.split("|")
                                    if len(parts) > 2:
                                        time_col = parts[2]
                                        break
                    
                    if time_col and file_id and conv_service:
                        # Get date range
                        from tools.mongodb_tools import get_date_range
                        date_range_result = get_date_range(user_id, file_id, "Sheet1", time_col)
                        if date_range_result.get("ok"):
                            date_info = date_range_result.get("result", {})
                            requires_date_range = True
                            date_range_info = {
                                "min_date": date_info.get("min_date"),
                                "max_date": date_info.get("max_date"),
                                "row_count": date_info.get("row_count"),
                                "span_days": date_info.get("span_days"),
                                "time_column": time_col
                            }
                            
                            # Update conversation context
                            await conv_service.mark_date_range_pending(conversation_id, date_range_info)
                            
                            # Modify answer to ask for date range
                            answer = f"""The dataset contains {date_info.get('row_count', 0)} rows spanning from {date_info.get('min_date', 'unknown')} to {date_info.get('max_date', 'unknown')} ({date_info.get('span_days', 0)} days).

To provide an accurate analysis, please specify a date range:
- You can say "last 30 days", "last month", "Q1 2025", or specific dates like "2025-11-01 to 2025-12-31"
- What date range would you like me to analyze?"""
                            
                            # Add assistant message to conversation
                            await conv_service.add_message(
                                conversation_id,
                                "assistant",
                                answer,
                                {"requires_date_range": True, "date_range_info": date_range_info}
                            )
        
        # Generate chart_config for ranking queries (bar chart)
        # Only generate chart if question explicitly asks for visualization
        elif "rank_entities" in tools_called:
            rank_output = tool_outputs.get("rank_entities", {})
            if isinstance(rank_output, dict) and rank_output.get("ok"):
                rank_result = rank_output.get("result", {})
                entities = rank_result.get("entities", [])
                if entities:
                    # Check if question asks for a chart/visualization
                    question_lower = question.lower()
                    chart_keywords = [
                        "chart", "graph", "plot", "visualize", "show", "display",
                        "bar chart", "line chart", "pie chart", "scatter", "visualization",
                        "as a chart", "as a graph", "as a bar", "as a line"
                    ]
                    # Also check for comparative questions that typically need charts
                    comparative_keywords = ["which", "who", "top", "bottom", "compare", "comparison"]
                    has_chart_keyword = any(keyword in question_lower for keyword in chart_keywords)
                    has_comparative_keyword = any(keyword in question_lower for keyword in comparative_keywords)
                    
                    # Only generate chart if:
                    # 1. Question explicitly mentions chart/graph/visualization, OR
                    # 2. Question is comparative (which/who/top/bottom) AND has multiple entities (more than 1)
                    should_generate_chart = has_chart_keyword or (has_comparative_keyword and len(entities) > 1)
                    
                    if should_generate_chart:
                        labels = [e.get("entity", "") for e in entities]
                        data_values = [float(e.get("value", 0)) if e.get("value") is not None else 0 for e in entities]
                        metric_name = rank_result.get("metric", "Value")
                        
                        # Determine chart type from question
                        chart_type = "bar"  # Default to bar chart
                        if "pie" in question_lower or "pie chart" in question_lower:
                            chart_type = "pie"
                        elif "line" in question_lower or "line chart" in question_lower:
                            chart_type = "line"
                        elif "scatter" in question_lower or "scatter chart" in question_lower:
                            chart_type = "scatter"
                        elif "bar" in question_lower or "column" in question_lower or "bar chart" in question_lower:
                            chart_type = "bar"
                        
                        # For pie charts, use different color scheme
                        if chart_type == "pie":
                            # Generate distinct colors for pie chart
                            num_colors = len(data_values)
                            background_colors = []
                            border_colors = []
                            for i in range(num_colors):
                                hue = i / num_colors
                                rgb = colorsys.hsv_to_rgb(hue, 0.7, 0.9)
                                bg_color = f"rgba({int(rgb[0]*255)}, {int(rgb[1]*255)}, {int(rgb[2]*255)}, 0.8)"
                                border_color = f"rgba({int(rgb[0]*255)}, {int(rgb[1]*255)}, {int(rgb[2]*255)}, 1)"
                                background_colors.append(bg_color)
                                border_colors.append(border_color)
                        else:
                            # For bar/line charts, use single color
                            background_colors = "#3B82F6"
                            border_colors = "#2563EB"
                        
                        chart_config = {
                            "success": True,
                            "chart_type": chart_type,
                            "title": question if len(question) < 60 else question[:57] + "...",
                            "data": {
                                "labels": labels,
                                "datasets": [{
                                    "label": metric_name,
                                    "data": data_values,
                                    "backgroundColor": background_colors,
                                    "borderColor": border_colors,
                                    "borderWidth": 1
                                }]
                            },
                            "options": {
                                "responsive": True,
                                "maintainAspectRatio": False,
                                "plugins": {
                                    "title": {
                                        "display": True,
                                        "text": question if len(question) < 60 else question[:57] + "...",
                                        "font": {"size": 16}
                                    },
                                    "legend": {
                                        "display": True,
                                        "position": "top"
                                    }
                                },
                                "scales": {
                                    "x": {
                                        "title": {
                                            "display": True,
                                            "text": "Entity"
                                        }
                                    },
                                    "y": {
                                        "beginAtZero": True,
                                        "title": {
                                            "display": True,
                                            "text": metric_name
                                        }
                                    }
                                }
                            }
                        }
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Add assistant message to conversation if not already added
        if conv_service and not requires_date_range:
            try:
                await conv_service.add_message(
                    conversation_id,
                    "assistant",
                    answer,
                    {"chart_config": chart_config is not None}
                )
            except Exception as e:
                logger.warning(f"Failed to add message to conversation: {str(e)}")
        
        return {
            "request_id": request_id,
            "success": True,
            "answer_short": answer,
            "answer_detailed": answer,
            "values": values if values else None,
            "chart_config": chart_config,
            "provenance": provenance if provenance else None,
            "verification": None,  # Will be populated with verification results
            "confidence": 0.95 if tools_called else 0.5,
            "tools_called": tools_called,
            "tool_outputs": tool_outputs,
            "latency_ms": latency_ms,
            "timestamp": datetime.now(),
            "error": None,
            "requires_date_range": requires_date_range,
            "date_range_info": date_range_info,
            "conversation_id": conversation_id
        }
    
    except Exception as e:
        logger.error(f"Error executing agent query: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return {
            "request_id": request_id,
            "success": False,
            "answer_short": f"Error: {str(e)}",
            "answer_detailed": None,
            "values": None,
            "chart_config": None,
            "provenance": None,
            "verification": None,
            "confidence": 0.0,
            "tools_called": [],
            "tool_outputs": None,
            "latency_ms": latency_ms,
            "timestamp": datetime.now(),
            "error": str(e)
        }

