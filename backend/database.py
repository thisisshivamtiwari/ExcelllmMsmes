"""
MongoDB Database Connection Module
Handles async MongoDB connections using Motor
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global database instance
_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None
_gridfs: Optional[AsyncIOMotorGridFSBucket] = None


def get_mongodb_uri() -> str:
    """Get MongoDB URI from environment variables"""
    # Try MongoDB Atlas connection string first
    uri = os.getenv("MONGODB_URI")
    if uri:
        return uri
    
    # Fallback to local MongoDB
    host = os.getenv("MONGODB_HOST", "localhost")
    port = os.getenv("MONGODB_PORT", "27017")
    db_name = os.getenv("MONGODB_DB_NAME", "excelllm")
    
    return f"mongodb://{host}:{port}/{db_name}"


async def connect_to_mongodb():
    """Connect to MongoDB database"""
    global _client, _database, _gridfs
    
    try:
        uri = get_mongodb_uri()
        db_name = os.getenv("MONGODB_DB_NAME", "excelllm")
        
        # Extract database name from URI if present
        if "mongodb+srv://" in uri or "mongodb://" in uri:
            # If URI contains database name, use it
            if "/" in uri.split("?")[0]:
                db_name_from_uri = uri.split("/")[-1].split("?")[0]
                if db_name_from_uri:
                    db_name = db_name_from_uri
        
        logger.info(f"Connecting to MongoDB: {uri.split('@')[-1] if '@' in uri else uri}")
        
        _client = AsyncIOMotorClient(uri)
        _database = _client[db_name]
        _gridfs = AsyncIOMotorGridFSBucket(_database)
        
        # Test connection
        await _client.admin.command('ping')
        logger.info(f"✅ Successfully connected to MongoDB database: {db_name}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {str(e)}")
        raise


async def close_mongodb_connection():
    """Close MongoDB connection"""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance"""
    if _database is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongodb() first.")
    return _database


def get_gridfs() -> AsyncIOMotorGridFSBucket:
    """Get GridFS bucket instance"""
    if _gridfs is None:
        raise RuntimeError("GridFS not initialized. Call connect_to_mongodb() first.")
    return _gridfs


def get_client() -> AsyncIOMotorClient:
    """Get MongoDB client instance"""
    if _client is None:
        raise RuntimeError("MongoDB client not initialized. Call connect_to_mongodb() first.")
    return _client

