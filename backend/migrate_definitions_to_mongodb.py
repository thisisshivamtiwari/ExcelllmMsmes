"""
Migration script to copy user_definitions from local JSON files to MongoDB
Run this once to migrate existing definitions to MongoDB
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Add backend directory to path
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Load environment variables - try backend folder first, then project root
env_loaded = False

# Try backend folder first (where user says .env is located)
backend_env = BACKEND_DIR / ".env"
if backend_env.exists():
    load_dotenv(backend_env)
    print(f"✅ Loaded .env from: {backend_env}")
    env_loaded = True

# Also try project root (in case it's there too)
project_env = PROJECT_ROOT / ".env"
if project_env.exists() and not env_loaded:
    load_dotenv(project_env)
    print(f"✅ Loaded .env from: {project_env}")
    env_loaded = True

# Fallback to current directory
if not env_loaded:
    load_dotenv()
    print(f"⚠️  Using default .env loading (current directory)")

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import get_database, connect_to_mongodb, close_mongodb_connection
from models.user import UserInDB

# Metadata directory (where old JSON files are stored)
METADATA_DIR = BACKEND_DIR.parent / "uploaded_files" / "metadata"


def load_file_metadata(file_id: str) -> Optional[Dict[str, Any]]:
    """Load file metadata from JSON file."""
    metadata_file = METADATA_DIR / f"{file_id}.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {file_id}: {e}")
            return None
    return None


async def migrate_definitions():
    """Migrate user_definitions from local JSON files to MongoDB"""
    # Check if MongoDB URI is set
    mongodb_uri = os.getenv("MONGODB_URI")
    
    # Debug: Show all MongoDB-related env vars
    print(f"\n🔍 Environment variables check:")
    print(f"   MONGODB_URI: {'✅ Found' if mongodb_uri else '❌ Not found'}")
    if mongodb_uri:
        # Show first 50 chars for security
        print(f"   Value: {mongodb_uri[:50]}...")
    else:
        # Check for alternative variable names
        alt_vars = ["MONGO_URI", "DATABASE_URL", "MONGODB_CONNECTION_STRING"]
        for var in alt_vars:
            val = os.getenv(var)
            if val:
                print(f"   Found {var} instead, using it...")
                mongodb_uri = val
                break
    
    if not mongodb_uri:
        print("\n❌ MONGODB_URI not found in environment variables!")
        print(f"   Checked .env files in:")
        print(f"   - {BACKEND_DIR / '.env'}")
        print(f"   - {PROJECT_ROOT / '.env'}")
        print(f"   Current working directory: {os.getcwd()}")
        print(f"\n   Please ensure MONGODB_URI is set in your .env file")
        return
    
    print(f"🔗 Connecting to MongoDB...")
    print(f"   URI: {mongodb_uri[:50]}..." if len(mongodb_uri) > 50 else f"   URI: {mongodb_uri}")
    
    try:
        await connect_to_mongodb()
        print("✅ Connected to MongoDB successfully")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return
    
    db = get_database()
    files_collection = db["files"]
    
    print("🔍 Scanning for local JSON metadata files...")
    
    if not METADATA_DIR.exists():
        print(f"❌ Metadata directory not found: {METADATA_DIR}")
        return
    
    json_files = list(METADATA_DIR.glob("*.json"))
    print(f"📁 Found {len(json_files)} JSON files")
    
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    for json_file in json_files:
        file_id = json_file.stem  # filename without .json extension
        
        # Skip relationship cache file
        if json_file.name == "relationship_cache.json":
            continue
        
        try:
            # Load old metadata from JSON
            old_metadata = load_file_metadata(file_id)
            if not old_metadata:
                skipped_count += 1
                continue
            
            # Get user_definitions from old metadata
            old_user_defs = old_metadata.get("user_definitions", {})
            if not old_user_defs:
                print(f"\n📄 Skipping {file_id}: No user_definitions found in local file")
                skipped_count += 1
                continue
            
            print(f"\n📄 Processing file: {file_id}")
            print(f"   Found {len(old_user_defs)} definitions in local file")
            
            # Find file in MongoDB
            file_doc = await files_collection.find_one({"file_id": file_id})
            
            if not file_doc:
                print(f"   ⚠️  File not found in MongoDB (file_id: {file_id}), skipping...")
                print(f"   💡 This file may have been uploaded before MongoDB migration")
                skipped_count += 1
                continue
            
            # Check if MongoDB already has definitions
            mongo_metadata = file_doc.get("metadata", {})
            mongo_user_defs = mongo_metadata.get("user_definitions", {})
            
            if mongo_user_defs:
                print(f"   ℹ️  MongoDB already has {len(mongo_user_defs)} definitions")
                # Merge: MongoDB takes precedence, but add any missing from local
                merged_defs = {**old_user_defs, **mongo_user_defs}
                if merged_defs != mongo_user_defs:
                    print(f"   🔄 Merging: {len(merged_defs)} total definitions")
                    await files_collection.update_one(
                        {"_id": file_doc["_id"]},
                        {"$set": {"metadata.user_definitions": merged_defs}}
                    )
                    migrated_count += 1
                else:
                    print(f"   ✅ Already up to date")
                    skipped_count += 1
            else:
                # No definitions in MongoDB, copy from local
                print(f"   📤 Copying {len(old_user_defs)} definitions to MongoDB...")
                await files_collection.update_one(
                    {"_id": file_doc["_id"]},
                    {"$set": {"metadata.user_definitions": old_user_defs}}
                )
                migrated_count += 1
                print(f"   ✅ Migrated successfully")
        
        except Exception as e:
            print(f"   ❌ Error migrating {file_id}: {e}")
            error_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Migration complete!")
    print(f"   Migrated: {migrated_count} files")
    print(f"   Skipped: {skipped_count} files")
    print(f"   Errors: {error_count} files")
    print(f"{'='*60}")
    
    await close_mongodb_connection()


if __name__ == "__main__":
    print("🚀 Starting migration of user_definitions to MongoDB...")
    asyncio.run(migrate_definitions())

