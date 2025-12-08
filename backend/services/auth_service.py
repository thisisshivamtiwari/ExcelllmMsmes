"""
Authentication Service
Handles user authentication, password hashing, and JWT tokens
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import HTTPException, status
from bson import ObjectId
import logging

from database import get_database
from models.user import UserCreate, UserInDB, UserResponse

logger = logging.getLogger(__name__)

# JWT settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production-min-32-chars")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        # Bcrypt has a 72-byte limit, truncate if necessary
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        # Ensure hashed_password is bytes
        if isinstance(hashed_password, str):
            hashed_bytes = hashed_password.encode('utf-8')
        else:
            hashed_bytes = hashed_password
        
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


async def create_user(user_data: UserCreate) -> UserResponse:
    """Create a new user"""
    db = get_database()
    users_collection = db["users"]
    
    # Check if user already exists
    existing_user = await users_collection.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    password_hash = get_password_hash(user_data.password)
    
    # Create user document
    now = datetime.utcnow()
    user_doc = {
        "email": user_data.email,
        "password_hash": password_hash,
        "industry": user_data.industry,
        "created_at": now,
        "updated_at": now,
        "is_active": True,
        "last_login": None,
        "profile": {
            "name": user_data.name,
            "company": user_data.company
        } if user_data.name or user_data.company else None
    }
    
    # Insert user
    result = await users_collection.insert_one(user_doc)
    
    # Return user response
    user_doc["_id"] = result.inserted_id
    return UserResponse(
        id=str(result.inserted_id),
        email=user_doc["email"],
        industry=user_doc["industry"],
        created_at=user_doc["created_at"],
        updated_at=user_doc["updated_at"],
        is_active=user_doc["is_active"],
        last_login=user_doc["last_login"],
        profile=user_doc["profile"]
    )


async def authenticate_user(email: str, password: str) -> Optional[UserInDB]:
    """Authenticate a user by email and password"""
    db = get_database()
    users_collection = db["users"]
    
    # Find user by email
    user_doc = await users_collection.find_one({"email": email})
    if not user_doc:
        return None
    
    # Verify password
    if not verify_password(password, user_doc["password_hash"]):
        return None
    
    # Check if user is active
    if not user_doc.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Update last login
    await users_collection.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Convert to UserInDB - ensure _id is properly set
    # MongoDB returns _id as ObjectId, Pydantic needs it as-is
    user_data = dict(user_doc)
    if "_id" not in user_data or user_data["_id"] is None:
        raise ValueError("User document missing _id field")
    
    return UserInDB(**user_data)


async def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    """Get user by ID"""
    db = get_database()
    users_collection = db["users"]
    
    try:
        user_doc = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            return None
        return UserInDB(**user_doc)
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        return None


async def get_user_by_email(email: str) -> Optional[UserInDB]:
    """Get user by email"""
    db = get_database()
    users_collection = db["users"]
    
    user_doc = await users_collection.find_one({"email": email})
    if not user_doc:
        return None
    
    # Ensure _id is properly set
    user_data = dict(user_doc)
    if "_id" not in user_data:
        return None
    
    return UserInDB(**user_data)

