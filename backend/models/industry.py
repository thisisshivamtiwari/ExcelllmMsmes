"""
Industry Model and Schema
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from bson import ObjectId


class SchemaTemplate(BaseModel):
    """Schema template for an industry"""
    name: str
    columns: List[str]
    description: str


class IndustryCreate(BaseModel):
    """Industry creation schema"""
    name: str
    display_name: str
    description: str
    icon: Optional[str] = None
    schema_templates: Optional[List[SchemaTemplate]] = None


class IndustryResponse(BaseModel):
    """Industry response schema"""
    id: str
    name: str
    display_name: str
    description: str
    icon: Optional[str] = None
    schema_templates: Optional[List[SchemaTemplate]] = None
    created_at: datetime

    class Config:
        from_attributes = True

