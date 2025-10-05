# backend/app/services/history.py
"""
Conversation history management service.
Stores and retrieves chat conversation history.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from ..core.config import settings
from ..models import ConversationHistory, ConversationTurn, ChatResponse

# History storage directory
HISTORY_DIR = Path(settings.UPLOAD_DIR) / "history"
HISTORY_DIR.mkdir(exist_ok=True)

class ConversationHistoryManager:
    """Manages conversation history storage and retrieval"""
    
    def __init__(self):
        self.history_dir = HISTORY_DIR
    
    def create_conversation(self) -> str:
        """Create a new conversation and return its ID"""
        conversation_id = str(uuid.uuid4())
        conversation = ConversationHistory(
            conversation_id=conversation_id,
            turns=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self._save_conversation(conversation)
        return conversation_id
    
    def add_turn(self, conversation_id: str, query: str, response: ChatResponse) -> None:
        """Add a new turn to an existing conversation"""
        conversation = self.get_conversation(conversation_id)
        
        if not conversation:
            # Create new conversation if it doesn't exist
            conversation = ConversationHistory(
                conversation_id=conversation_id,
                turns=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        
        turn = ConversationTurn(
            query=query,
            response=response,
            timestamp=datetime.now()
        )
        
        conversation.turns.append(turn)
        conversation.updated_at = datetime.now()
        
        self._save_conversation(conversation)
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationHistory]:
        """Retrieve a conversation by ID"""
        file_path = self.history_dir / f"{conversation_id}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return ConversationHistory(**data)
        except Exception:
            return None
    
    def list_conversations(self, limit: int = 50) -> List[Dict]:
        """List recent conversations with basic info"""
        conversations = []
        
        for file_path in self.history_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    conversations.append({
                        "conversation_id": data["conversation_id"],
                        "created_at": data["created_at"],
                        "updated_at": data["updated_at"],
                        "turn_count": len(data.get("turns", [])),
                        "last_query": data["turns"][-1]["query"] if data.get("turns") else ""
                    })
            except Exception:
                continue
        
        # Sort by updated_at descending
        conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        return conversations[:limit]
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        file_path = self.history_dir / f"{conversation_id}.json"
        
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except Exception:
                return False
        return False
    
    def _save_conversation(self, conversation: ConversationHistory) -> None:
        """Save conversation to disk"""
        file_path = self.history_dir / f"{conversation.conversation_id}.json"
        
        # Convert to dict for JSON serialization
        data = conversation.model_dump()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

# Global instance
history_manager = ConversationHistoryManager()