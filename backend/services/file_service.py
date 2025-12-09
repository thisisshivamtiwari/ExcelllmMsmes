"""
File Service
Handles file storage in MongoDB GridFS with user context
"""

import os
import math
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import uuid
import logging
from bson import ObjectId

from database import get_database, get_gridfs
from models.user import UserInDB

logger = logging.getLogger(__name__)


def sanitize_for_json(value: Any) -> Any:
    """
    Sanitize values for JSON serialization.
    Converts inf, -inf, and nan to None or 0.
    """
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
    elif isinstance(value, dict):
        return {k: sanitize_for_json(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_for_json(item) for item in value]
    return value


async def upload_file_to_gridfs(
    user: UserInDB,
    file_content: bytes,
    original_filename: str,
    file_metadata: Dict[str, Any],
    industry: str
) -> Dict[str, Any]:
    """
    Upload file to MongoDB GridFS with user context
    
    Args:
        user: Current authenticated user
        file_content: File content as bytes
        original_filename: Original filename
        file_metadata: File metadata (columns, row_count, etc.)
        industry: User's industry
        
    Returns:
        File document with file_id and metadata
    """
    db = get_database()
    gridfs = get_gridfs()
    files_collection = db["files"]
    
    # Generate unique file ID
    file_id = str(uuid.uuid4())
    
    # Upload file to GridFS
    gridfs_file_id = await gridfs.upload_from_stream(
        filename=original_filename,
        source=file_content,
        metadata={
            "user_id": str(user.id),
            "file_id": file_id,
            "industry": industry,
            "uploaded_at": datetime.utcnow().isoformat()
        }
    )
    
    # Create file document in files collection
    file_doc = {
        "user_id": user.id,
        "file_id": file_id,
        "original_filename": original_filename,
        "industry": industry,
        "file_type": Path(original_filename).suffix.lower().replace('.', ''),
        "file_size_bytes": len(file_content),
        "uploaded_at": datetime.utcnow(),
        "metadata": file_metadata,
        "storage": {
            "type": "gridfs",
            "gridfs_id": gridfs_file_id
        },
        "is_indexed": False,
        "indexed_at": None
    }
    
    # Insert file document
    result = await files_collection.insert_one(file_doc)
    file_doc["_id"] = result.inserted_id
    
    logger.info(f"File uploaded to GridFS: {file_id} for user {user.id}")
    
    return {
        "file_id": file_id,
        "gridfs_id": str(gridfs_file_id),
        "original_filename": original_filename,
        "uploaded_at": file_doc["uploaded_at"].isoformat(),
        "file_size_bytes": len(file_content)
    }


async def get_file_from_gridfs(file_id: str, user: UserInDB) -> Optional[bytes]:
    """
    Retrieve file from GridFS (user-specific)
    
    Args:
        file_id: File ID
        user: Current authenticated user
        
    Returns:
        File content as bytes, or None if not found
    """
    db = get_database()
    gridfs = get_gridfs()
    files_collection = db["files"]
    
    # Find file document (must belong to user)
    file_doc = await files_collection.find_one({
        "file_id": file_id,
        "user_id": user.id
    })
    
    if not file_doc:
        return None
    
    # Get GridFS ID
    gridfs_id = file_doc["storage"]["gridfs_id"]
    
    # Download file from GridFS
    grid_out = await gridfs.open_download_stream(gridfs_id)
    file_content = await grid_out.read()
    
    return file_content


async def get_user_files(user: UserInDB, deduplicate: bool = False) -> List[Dict[str, Any]]:
    """
    Get all files for a user
    
    Args:
        user: Current authenticated user
        deduplicate: If True, return only the most recent file for each filename (default: False)
        
    Returns:
        List of file documents
    """
    db = get_database()
    files_collection = db["files"]
    
    # user.id is an ObjectId from UserInDB model
    # MongoDB stores user_id as ObjectId, so we can query directly
    try:
        logger.info(f"Querying files for user_id: {user.id} (type: {type(user.id)})")
        cursor = files_collection.find({"user_id": user.id}).sort("uploaded_at", -1)
        files = []
        seen_filenames = set()  # Track filenames for deduplication
        
        async for doc in cursor:
            metadata = doc.get("metadata", {})
            # Sanitize metadata to remove any invalid float values
            sanitized_metadata = sanitize_for_json(metadata)
            
            original_filename = doc["original_filename"]
            
            # If deduplicating, skip files with names we've already seen
            if deduplicate:
                if original_filename in seen_filenames:
                    logger.info(f"Skipping duplicate file: {original_filename} (file_id: {doc['file_id']})")
                    continue
                seen_filenames.add(original_filename)
            
            file_data = {
                "file_id": doc["file_id"],
                "filename": original_filename,  # Frontend expects 'filename'
                "original_filename": original_filename,
                "industry": doc.get("industry", ""),
                "file_type": doc.get("file_type", ""),
                "file_size_bytes": doc.get("file_size_bytes", 0),
                "uploaded_at": doc["uploaded_at"].isoformat() if doc.get("uploaded_at") else None,
                "sheet_names": sanitized_metadata.get("sheet_names", []) if isinstance(sanitized_metadata, dict) else [],
                "metadata": sanitized_metadata,
                "is_indexed": doc.get("is_indexed", False)
            }
            
            # Sanitize the entire file_data object
            files.append(sanitize_for_json(file_data))
        
        logger.info(f"Found {len(files)} files for user {user.id} (deduplicated: {deduplicate})")
        return files
    except Exception as e:
        logger.error(f"Error querying files for user {user.id}: {str(e)}")
        logger.error(f"User ID type: {type(user.id)}, value: {user.id}")
        raise


async def get_file_metadata(file_id: str, user: UserInDB) -> Optional[Dict[str, Any]]:
    """
    Get file metadata (user-specific)
    
    Args:
        file_id: File ID
        user: Current authenticated user
        
    Returns:
        File metadata or None if not found
    """
    db = get_database()
    files_collection = db["files"]
    
    file_doc = await files_collection.find_one({
        "file_id": file_id,
        "user_id": user.id
    })
    
    if not file_doc:
        return None
    
    return {
        "file_id": file_doc["file_id"],
        "original_filename": file_doc["original_filename"],
        "industry": file_doc["industry"],
        "file_type": file_doc["file_type"],
        "file_size_bytes": file_doc["file_size_bytes"],
        "uploaded_at": file_doc["uploaded_at"].isoformat(),
        "metadata": file_doc.get("metadata", {}),
        "is_indexed": file_doc.get("is_indexed", False)
    }


async def delete_file(file_id: str, user: UserInDB) -> bool:
    """
    Delete file from GridFS and database (user-specific)
    
    Args:
        file_id: File ID
        user: Current authenticated user
        
    Returns:
        True if deleted, False if not found
    """
    db = get_database()
    gridfs = get_gridfs()
    files_collection = db["files"]
    
    # Find file document (must belong to user)
    file_doc = await files_collection.find_one({
        "file_id": file_id,
        "user_id": user.id
    })
    
    if not file_doc:
        return False
    
    # Delete from GridFS
    try:
        gridfs_id = file_doc["storage"]["gridfs_id"]
        await gridfs.delete(gridfs_id)
    except Exception as e:
        logger.error(f"Error deleting file from GridFS: {e}")
    
    # Delete file document
    await files_collection.delete_one({"_id": file_doc["_id"]})
    
    logger.info(f"File deleted: {file_id} for user {user.id}")
    return True

