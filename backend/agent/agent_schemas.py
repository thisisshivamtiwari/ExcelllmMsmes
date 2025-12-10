"""
Pydantic Schemas for Agent System
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


class ToolEnvelope(BaseModel):
    """Canonical tool response envelope"""
    ok: bool
    tool: str
    result: Optional[Union[Dict, List, float, int, str]] = None
    unit: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AgentQueryRequest(BaseModel):
    """Request model for agent query"""
    question: str = Field(..., description="User's natural language question")
    file_id: Optional[str] = Field(None, description="Specific file ID to query (optional)")
    provider: str = Field("gemini", description="LLM provider: 'gemini' or 'groq'")
    include_provenance: bool = Field(True, description="Include provenance in response")
    max_iterations: int = Field(10, ge=1, le=25, description="Maximum agent iterations")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for multi-turn context")
    date_range: Optional[Dict[str, Optional[str]]] = Field(None, description="Date range filter: {start: 'YYYY-MM-DD', end: 'YYYY-MM-DD'}")


class AgentQueryResponse(BaseModel):
    """Response model for agent query"""
    request_id: str
    success: bool
    answer_short: str
    answer_detailed: Optional[str] = None
    values: Optional[Dict[str, Any]] = None
    chart_config: Optional[Dict[str, Any]] = None
    provenance: Optional[Dict[str, Any]] = None
    verification: Optional[List[Dict[str, Any]]] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    tools_called: List[str] = []
    tool_outputs: Optional[Dict[str, Any]] = None
    latency_ms: int
    timestamp: datetime
    error: Optional[str] = None
    requires_date_range: bool = Field(False, description="Whether agent needs date range from user")
    date_range_info: Optional[Dict[str, Any]] = Field(None, description="Date range information when requires_date_range is True")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for follow-up")


class AgentStatusResponse(BaseModel):
    """Agent status response"""
    status: str
    available: bool
    providers: Dict[str, Dict[str, Any]]
    message: Optional[str] = None

