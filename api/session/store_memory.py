"""In-memory session store for single-session chat history.

Replaces DynamoDB store with simple in-memory storage.
History is lost on server restart - by design.
"""

from typing import Any, Dict, List, Optional
from collections import defaultdict
import time


class InMemorySessionStore:
    """Simple in-memory session store for chat history.

    API-compatible with SessionStore (DynamoDB) for drop-in replacement.
    """

    def __init__(self):
        # session_id -> list of turns
        self._turns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # session_id -> summary dict
        self._summaries: Dict[str, Dict[str, Any]] = defaultdict(dict)
        # session_id -> metadata
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def add_turn(
        self,
        session_id: str,
        role: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None,
        patient_id: Optional[str] = None,
    ) -> None:
        """Add a conversation turn."""
        turn = {
            "session_id": session_id,
            "turn_ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "role": role,
            "text": text,
            "meta": meta or {},
            "patient_id": patient_id,
        }
        self._turns[session_id].append(turn)

    # Alias for DynamoDB compatibility
    def append_turn(
        self,
        session_id: str,
        role: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None,
        patient_id: Optional[str] = None,
    ) -> None:
        """Alias for add_turn (DynamoDB API compatibility)."""
        self.add_turn(session_id, role, text, meta, patient_id)

    def get_recent(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent turns for a session (newest first)."""
        turns = self._turns.get(session_id, [])
        # Return newest first, limited
        return list(reversed(turns[-limit:]))

    def get_summary(self, session_id: str) -> Dict[str, Any]:
        """Get session summary."""
        return self._summaries.get(session_id, {})

    def update_summary(
        self,
        session_id: str,
        summary: Dict[str, Any],
        user_id: Optional[str] = None,
        patient_id: Optional[str] = None,
    ) -> None:
        """Update session summary (DynamoDB API compatible)."""
        self._summaries[session_id].update(summary)
        if user_id:
            self._summaries[session_id]["user_id"] = user_id
        if patient_id:
            self._summaries[session_id]["patient_id"] = patient_id
        self._summaries[session_id]["last_activity"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")

    def create_session(
        self,
        session_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new session."""
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        metadata = {
            "session_id": session_id,
            "user_id": user_id,
            "name": name or "",
            "description": description or "",
            "tags": tags or [],
            "created_at": now,
            "last_activity": now,
            "message_count": 0,
        }
        self._metadata[session_id] = metadata
        return metadata

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata."""
        return self._metadata.get(session_id)

    def update_session(
        self,
        session_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update session metadata."""
        if session_id not in self._metadata:
            return None
        if name is not None:
            self._metadata[session_id]["name"] = name
        if description is not None:
            self._metadata[session_id]["description"] = description
        if tags is not None:
            self._metadata[session_id]["tags"] = tags
        self._metadata[session_id]["last_activity"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        return self._metadata[session_id]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its data."""
        deleted = False
        if session_id in self._metadata:
            del self._metadata[session_id]
            deleted = True
        if session_id in self._turns:
            del self._turns[session_id]
            deleted = True
        if session_id in self._summaries:
            del self._summaries[session_id]
            deleted = True
        return deleted

    # Alias for DynamoDB compatibility
    def clear_session(self, session_id: str) -> bool:
        """Alias for delete_session (DynamoDB API compatibility)."""
        return self.delete_session(session_id)

    def list_sessions_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """List sessions for a user (DynamoDB API compatibility)."""
        user_sessions = []
        for session_id, summary in self._summaries.items():
            if summary.get("user_id") == user_id:
                user_sessions.append({
                    "session_id": session_id,
                    "user_id": user_id,
                    **summary,
                })
        # Sort by last_activity descending
        user_sessions.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
        return user_sessions

    def get_first_message_preview(self, session_id: str, max_length: int = 100) -> Optional[str]:
        """Get preview of first message in session (DynamoDB API compatibility)."""
        turns = self._turns.get(session_id, [])
        for turn in turns:
            if turn.get("role") == "user":
                text = turn.get("text", "")
                if len(text) > max_length:
                    return text[:max_length] + "..."
                return text
        return None

    def get_session_count(self, user_id: str) -> int:
        """Count sessions for a user (DynamoDB API compatibility)."""
        return len([
            1 for summary in self._summaries.values()
            if summary.get("user_id") == user_id
        ])

    def list_sessions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List sessions for a user."""
        user_sessions = [
            meta for meta in self._metadata.values()
            if meta.get("user_id") == user_id
        ]
        # Sort by last_activity descending
        user_sessions.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
        return user_sessions[offset:offset + limit]

    def count_sessions(self, user_id: str) -> int:
        """Count sessions for a user."""
        return len([
            1 for meta in self._metadata.values()
            if meta.get("user_id") == user_id
        ])

    def clear_all(self) -> None:
        """Clear all session data (for testing)."""
        self._turns.clear()
        self._summaries.clear()
        self._metadata.clear()


# Type alias for DynamoDB compatibility
SessionStore = InMemorySessionStore


# Singleton instance
_store: Optional[InMemorySessionStore] = None


def get_session_store() -> InMemorySessionStore:
    """Get the singleton session store instance."""
    global _store
    if _store is None:
        _store = InMemorySessionStore()
        print("[SESSION] Using in-memory session store (no persistence)")
    return _store
