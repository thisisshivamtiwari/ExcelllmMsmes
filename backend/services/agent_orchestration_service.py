"""
Agent Orchestration Service - DISABLED
Agent and tools directories have been removed - will be rebuilt from scratch
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

from models.user import UserInDB

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """DISABLED - Agent orchestrator removed. Will be rebuilt from scratch."""
    
    def __init__(self, user: UserInDB, provider: str = "gemini"):
        raise NotImplementedError("AgentOrchestrator has been removed - agent and tools directories deleted. Will be rebuilt from scratch.")
    
    def _initialize_agent(self):
        """Initialize the agent with tools"""
        try:
            from agent.agent import ExcelAgent
            from agent.tool_wrapper import (
                create_excel_retriever_tool,
                create_data_calculator_tool,
                create_trend_analyzer_tool,
                create_comparative_analyzer_tool,
                create_kpi_calculator_tool,
                create_graph_generator_tool
            )
            from tools.mongodb_excel_retriever import MongoDBExcelRetriever
            from tools.data_calculator import DataCalculator
            from tools.trend_analyzer import TrendAnalyzer
            from tools.comparative_analyzer import ComparativeAnalyzer
            from tools.kpi_calculator import KPICalculator
            from tools.graph_generator import GraphGenerator
            
            # Import retriever initialization (same as main.py)
            from embeddings.embedder import Embedder
            from embeddings.mongodb_vector_store import MongoDBVectorStore
            
            user_id = str(self.user.id)
            
            # Initialize semantic retriever
            semantic_retriever = None
            try:
                from database import get_database
                embedder = Embedder()
                database = get_database()
                vector_store = MongoDBVectorStore(database=database, collection_name="embeddings")
                from embeddings.retriever import Retriever
                semantic_retriever = Retriever(embedder=embedder, vector_store=vector_store)
                logger.info("✓ Semantic retriever initialized")
            except Exception as e:
                logger.warning(f"Semantic retriever not available: {e}")
                semantic_retriever = None
            
            # Initialize tools
            excel_retriever = MongoDBExcelRetriever(user_id=user_id)
            data_calculator = DataCalculator()
            trend_analyzer = TrendAnalyzer()
            comparative_analyzer = ComparativeAnalyzer()
            kpi_calculator = KPICalculator()
            graph_generator = GraphGenerator()
            
            # Create LangChain tools
            tools = []
            if semantic_retriever:
                tools.append(create_excel_retriever_tool(excel_retriever, semantic_retriever, user_id=user_id))
            tools.append(create_data_calculator_tool(data_calculator))
            tools.append(create_trend_analyzer_tool(trend_analyzer, excel_retriever, semantic_retriever, user_id=user_id))
            tools.append(create_comparative_analyzer_tool(comparative_analyzer, excel_retriever, semantic_retriever, user_id=user_id))
            tools.append(create_kpi_calculator_tool(kpi_calculator, excel_retriever, semantic_retriever, user_id=user_id))
            tools.append(create_graph_generator_tool(graph_generator, excel_retriever, semantic_retriever, user_id=user_id))
            
            self.agent = ExcelAgent(
                tools=tools,
                provider=self.provider,
                model_name="gemini-2.5-flash" if self.provider == "gemini" else None
            )
            logger.info(f"✓ Agent orchestrator initialized for user {self.user.email}")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    async def query_with_validation(
        self,
        question: str,
        max_iterations: int = 3,
        require_verification: bool = True
    ) -> Dict[str, Any]:
        """
        Query agent with validation and iterative refinement.
        
        Args:
            question: User's question
            max_iterations: Maximum refinement iterations
            require_verification: Whether to require verification (default: True)
        
        Returns:
            Dictionary with answer, validation status, and metadata
        """
        if not self.agent:
            return {
                "success": False,
                "error": "Agent not initialized",
                "answer": "Agent system is not available. Please check logs."
            }
        
        best_answer = None
        best_validation = None
        best_score = -1
        
        for iteration in range(max_iterations):
            try:
                logger.info(f"Query iteration {iteration + 1}/{max_iterations}: {question}")
                
                # Query agent
                result = self.agent.query(question, max_retries=2)
                
                if not result.get("success"):
                    if iteration == 0:
                        # Return error on first attempt
                        return result
                    continue
                
                answer = result.get("answer", "")
                chart_config = None
                
                # Extract chart if present
                if isinstance(answer, dict):
                    if (answer.get("chart_type") or answer.get("type")) and answer.get("data"):
                        chart_config = answer
                elif isinstance(answer, str):
                    try:
                        parsed = json.loads(answer)
                        if (parsed.get("chart_type") or parsed.get("type")) and parsed.get("data"):
                            chart_config = parsed
                    except:
                        pass
                
                # Validate answer
                if require_verification:
                    # Determine question type
                    question_lower = question.lower()
                    if any(word in question_lower for word in ["chart", "graph", "plot", "show", "visualize"]):
                        q_type = "chart"
                    elif any(word in question_lower for word in ["which", "who", "best", "worst"]):
                        q_type = "comparative"
                    elif any(word in question_lower for word in ["total", "sum", "average", "count"]):
                        q_type = "calculation"
                    else:
                        q_type = "auto"
                    
                    # Verify answer
                    is_valid, validation_details = await self.validator.verify_answer(
                        question=question,
                        answer=answer,
                        question_type=q_type,
                        chart_config=chart_config
                    )
                    
                    # Score answer (1.0 for valid, 0.5 for invalid but has content, 0.0 for empty)
                    score = 1.0 if is_valid else (0.5 if answer and len(str(answer).strip()) > 0 else 0.0)
                    
                    logger.info(f"Iteration {iteration + 1} validation: valid={is_valid}, score={score}")
                    logger.debug(f"Validation details: {validation_details}")
                    
                    # Keep best answer
                    if score > best_score:
                        best_answer = answer
                        best_validation = validation_details
                        best_score = score
                    
                    # If valid, return immediately
                    if is_valid:
                        return {
                            "success": True,
                            "question": question,
                            "answer": answer,
                            "chart_config": chart_config,
                            "validated": True,
                            "validation_details": validation_details,
                            "intermediate_steps": result.get("intermediate_steps", []),
                            "provider": self.provider,
                            "model_name": self.agent.model_name,
                            "iterations": iteration + 1
                        }
                    
                    # If not valid and not last iteration, refine question
                    if iteration < max_iterations - 1:
                        # Add clarification to question
                        refinement_hint = self._get_refinement_hint(validation_details)
                        if refinement_hint:
                            question = f"{question} {refinement_hint}"
                            logger.info(f"Refining question: {question}")
                else:
                    # No verification required, return immediately
                    return {
                        "success": True,
                        "question": question,
                        "answer": answer,
                        "chart_config": chart_config,
                        "validated": False,
                        "intermediate_steps": result.get("intermediate_steps", []),
                        "provider": self.provider,
                        "model_name": self.agent.model_name,
                        "iterations": iteration + 1
                    }
                
            except Exception as e:
                logger.error(f"Error in iteration {iteration + 1}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                if iteration == 0:
                    return {
                        "success": False,
                        "error": str(e),
                        "answer": f"Error processing query: {str(e)}"
                    }
        
        # Return best answer even if not fully validated
        return {
            "success": True,
            "question": question,
            "answer": best_answer or "Unable to generate a verified answer.",
            "validated": best_score >= 1.0,
            "validation_details": best_validation,
            "validation_score": best_score,
            "provider": self.provider,
            "model_name": self.agent.model_name,
            "iterations": max_iterations,
            "warning": "Answer may not be fully verified" if best_score < 1.0 else None
        }
    
    def _get_refinement_hint(self, validation_details: Dict[str, Any]) -> Optional[str]:
        """Get refinement hint based on validation details"""
        error = validation_details.get("error", "")
        
        if "numeric value" in error.lower():
            return "(provide exact numeric value)"
        elif "chart" in error.lower():
            return "(return chart JSON format)"
        elif "entity" in error.lower() or "comparative" in error.lower():
            return "(specify the exact entity name)"
        elif "difference" in validation_details:
            diff = validation_details.get("difference", 0)
            expected = validation_details.get("expected", 0)
            if expected > 0:
                pct_diff = (diff / expected) * 100
                if pct_diff > 10:
                    return f"(recalculate - current answer differs by {pct_diff:.1f}%)"
        
        return None

