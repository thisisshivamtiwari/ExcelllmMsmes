"""
Conversation Context Service
Manages multi-turn conversations with context preservation
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from bson import ObjectId
from database import get_database

logger = logging.getLogger(__name__)


class ConversationService:
    """Manage conversation context for multi-turn agent queries"""
    
    def __init__(self, user_id: str):
        self.user_id = ObjectId(user_id) if isinstance(user_id, str) and len(user_id) == 24 else user_id
        self.db = get_database()
        self.conversations_collection = self.db["agent_conversations"]
    
    async def create_conversation(
        self,
        initial_question: str,
        file_id: Optional[str] = None
    ) -> str:
        """Create a new conversation thread"""
        conversation = {
            "user_id": self.user_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "messages": [
                {
                    "role": "user",
                    "content": initial_question,
                    "timestamp": datetime.now()
                }
            ],
            "context": {
                "original_question": initial_question,
                "file_id": file_id,
                "pending_date_range": False,
                "date_range_info": None
            },
            "status": "active"
        }
        
        result = await self.conversations_collection.insert_one(conversation)
        return str(result.inserted_id)
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a message to the conversation"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }
        
        await self.conversations_collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$push": {"messages": message},
                "$set": {"updated_at": datetime.now()}
            }
        )
    
    async def update_context(
        self,
        conversation_id: str,
        context_updates: Dict[str, Any]
    ):
        """Update conversation context"""
        await self.conversations_collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$set": {
                    "context": context_updates,
                    "updated_at": datetime.now()
                }
            }
        )
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID"""
        conv = await self.conversations_collection.find_one({
            "_id": ObjectId(conversation_id),
            "user_id": self.user_id
        })
        
        if conv:
            conv["_id"] = str(conv["_id"])
            conv["user_id"] = str(conv["user_id"])
        
        return conv
    
    async def get_conversation_context(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation context for agent"""
        conv = await self.get_conversation(conversation_id)
        if conv:
            return conv.get("context", {})
        return None
    
    async def mark_date_range_pending(
        self,
        conversation_id: str,
        date_range_info: Dict[str, Any]
    ):
        """Mark that we're waiting for date range from user"""
        await self.update_context(
            conversation_id,
            {
                "pending_date_range": True,
                "date_range_info": date_range_info
            }
        )
    
    async def set_date_range(
        self,
        conversation_id: str,
        start_date: Optional[str],
        end_date: Optional[str]
    ):
        """Set date range from user response"""
        context = await self.get_conversation_context(conversation_id)
        if context:
            context["pending_date_range"] = False
            context["date_range"] = {
                "start": start_date,
                "end": end_date
            }
            await self.update_context(conversation_id, context)


