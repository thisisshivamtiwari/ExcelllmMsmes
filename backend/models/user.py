"""
User Model and Schema
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId


class UserProfile(BaseModel):
    """User profile information"""
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(BaseModel):
    """User creation schema"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    industry: str = Field(..., description="Selected industry")
    name: Optional[str] = None
    company: Optional[str] = None


class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response schema (without password)"""
    id: str
    email: str
    industry: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    last_login: Optional[datetime] = None
    profile: Optional[UserProfile] = None

    class Config:
        from_attributes = True


class UserInDB(BaseModel):
    """User document in database"""
    id: ObjectId = Field(alias="_id")
    email: str
    password_hash: str
    industry: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    last_login: Optional[datetime] = None
    profile: Optional[UserProfile] = None

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True  # Allow both id and _id

