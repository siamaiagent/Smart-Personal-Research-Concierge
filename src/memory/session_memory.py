"""
Session Memory Module

This module provides in-memory session storage for temporary conversation data.
Sessions are ephemeral and exist only during program runtime, ideal for conversation context.

Author: Google Hackathon Team
License: MIT
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set


class SessionMemory:
    """
    High-performance in-memory session storage with automatic cleanup and analytics.
    
    This class provides ephemeral key-value storage for session-specific data that
    doesn't need to persist between program runs. It's ideal for:
    
    1. Conversation Context: Storing temporary chat history and state
    2. User Interactions: Tracking current research progress and preferences
    3. Temporary Cache: Holding intermediate results during processing
    4. Session Analytics: Monitoring active sessions and usage patterns
    
    Unlike LongTermMemory, SessionMemory:
    - Stores data in RAM (faster access)
    - Data is lost on program restart (ephemeral)
    - No disk I/O overhead
    - Ideal for short-lived, high-frequency data
    
    Architecture:
        - UUID-based session identification
        - Automatic timestamp tracking (created_at, last_updated)
        - Session cleanup utilities for memory management
        - Thread-safe single-instance operations
    
    Attributes:
        store (Dict[str, Dict[str, Any]]): In-memory session data
        SESSION_ID_LENGTH (int): Character length for session IDs
        DEFAULT_TTL_HOURS (int): Default time-to-live for sessions
    
    Storage Structure:
        {
            "abc123de": {
                "created_at": "2024-01-15T14:30:00.123456",
                "last_updated": "2024-01-15T14:35:00.123456",
                "user_query": "What is AI?",
                "research_results": {...},
                "conversation_history": [...]
            }
        }
    
    Example Usage:
        >>> memory = SessionMemory()
        >>> sid = memory.new_session()
        >>> memory.set(sid, "user_name", "Alice")
        >>> memory.set(sid, "query", "What is quantum computing?")
        >>> name = memory.get(sid, "user_name")
        >>> print(f"User: {name}")
        User: Alice
        
        >>> # Get all session data
        >>> session_data = memory.get_all(sid)
        >>> print(session_data)
    
    Performance:
        - O(1) average case for get/set operations
        - O(n) for cleanup operations (n = number of sessions)
        - No disk I/O latency
        - Memory footprint depends on stored data volume
    
    Thread Safety:
        Not thread-safe. Use external locking for concurrent access.
    
    Dependencies:
        - uuid: Session ID generation
        - datetime: Timestamp tracking and TTL calculations
    """
    
    # Configuration constants
    SESSION_ID_LENGTH = 8       # Short UUID length for readability
    DEFAULT_TTL_HOURS = 24      # Default session lifetime in hours
    
    # Reserved keys (automatically managed)
    RESERVED_KEYS = {'created_at', 'last_updated', 'access_count'}
    
    def __init__(self):
        """
        Initialize session memory with empty storage.
        
        Creates an empty in-memory store ready to hold session data.
        All data exists only in RAM and is lost on program termination.
        
        Example:
            >>> memory = SessionMemory()
            >>> print(f"Active sessions: {len(memory.list_sessions())}")
            Active sessions: 0
        """
        self.store: Dict[str, Dict[str, Any]] = {}
        
        print("[SessionMemory] ✓ Initialized")
        print(f"[SessionMemory] Session ID length: {self.SESSION_ID_LENGTH} chars")
        print(f"[SessionMemory] Default TTL: {self.DEFAULT_TTL_HOURS} hours")
    
    def new_session(self) -> str:
        """
        Create a new session with unique identifier.
        
        Generates a unique session ID and initializes the session with
        metadata timestamps. The session is immediately ready for use.
        
        Returns:
            str: Unique session identifier (8-character UUID)
        
        Session Initialization:
            - created_at: ISO timestamp of session creation
            - last_updated: ISO timestamp (initially same as created_at)
            - access_count: Number of get/set operations (starts at 0)
        
        Example:
            >>> memory = SessionMemory()
            >>> sid1 = memory.new_session()
            >>> sid2 = memory.new_session()
            >>> print(sid1 == sid2)
            False  # Each session has unique ID
        """
        # Generate short UUID for readability
        sid = str(uuid.uuid4())[:self.SESSION_ID_LENGTH]
        
        # Initialize session with metadata
        now = datetime.now().isoformat()
        self.store[sid] = {
            'created_at': now,
            'last_updated': now,
            'access_count': 0
        }
        
        print(f"[SessionMemory] ✓ NEW session created: {sid}")
        return sid
    
    def get(self, sid: str, key: str, default: Any = None) -> Any:
        """
        Retrieve a value from session storage.
        
        Args:
            sid (str): Session identifier
            key (str): Key to retrieve
            default (Any): Value to return if key doesn't exist
        
        Returns:
            Any: Stored value or default if not found
        
        Behavior:
            - Returns default if session doesn't exist
            - Returns default if key doesn't exist in session
            - Increments access counter
            - Does NOT update last_updated timestamp (read operation)
        
        Example:
            >>> sid = memory.new_session()
            >>> memory.set(sid, "name", "Alice")
            >>> name = memory.get(sid, "name")
            >>> print(name)
            Alice
            >>> unknown = memory.get(sid, "age", 25)
            >>> print(unknown)
            25
        """
        # Check if session exists
        if sid not in self.store:
            print(f"[SessionMemory] ⚠ GET session={sid}, key={key}: Session not found, returning default")
            return default
        
        # Increment access counter
        self.store[sid]['access_count'] = self.store[sid].get('access_count', 0) + 1
        
        # Retrieve value
        value = self.store[sid].get(key, default)
        
        # Log with truncated value for readability
        value_str = str(value)[:50]
        if len(str(value)) > 50:
            value_str += "..."
        
        print(f"[SessionMemory] GET session={sid}, key={key}: {value_str}")
        return value
    
    def set(self, sid: str, key: str, value: Any) -> None:
        """
        Store a value in session storage.
        
        Args:
            sid (str): Session identifier
            key (str): Key to store under
            value (Any): Value to store
        
        Behavior:
            - Creates session if it doesn't exist
            - Overwrites existing values
            - Updates last_updated timestamp
            - Increments access counter
        
        Restrictions:
            - Cannot override reserved keys (created_at, last_updated, access_count)
            - Use provided methods to access metadata
        
        Example:
            >>> sid = memory.new_session()
            >>> memory.set(sid, "query", "What is AI?")
            >>> memory.set(sid, "results", {"data": [1, 2, 3]})
            >>> memory.set(sid, "step", 1)
        """
        # Prevent overriding reserved keys
        if key in self.RESERVED_KEYS:
            print(f"[SessionMemory] ⚠ Cannot override reserved key: {key}")
            return
        
        # Create session if it doesn't exist
        if sid not in self.store:
            now = datetime.now().isoformat()
            self.store[sid] = {
                'created_at': now,
                'last_updated': now,
                'access_count': 0
            }
            print(f"[SessionMemory] Auto-created session: {sid}")
        
        # Store value
        self.store[sid][key] = value
        
        # Update metadata
        self.store[sid]['last_updated'] = datetime.now().isoformat()
        self.store[sid]['access_count'] = self.store[sid].get('access_count', 0) + 1
        
        # Log with truncated value
        value_str = str(value)[:50]
        if len(str(value)) > 50:
            value_str += "..."
        
        print(f"[SessionMemory] SET session={sid}, key={key}: {value_str}")
    
    def get_all(self, sid: str) -> Dict[str, Any]:
        """
        Retrieve all data for a session.
        
        Args:
            sid (str): Session identifier
        
        Returns:
            Dict[str, Any]: Complete session data including metadata.
                           Empty dict if session doesn't exist.
        
        Includes:
            - All user-stored key-value pairs
            - created_at: Session creation timestamp
            - last_updated: Last modification timestamp
            - access_count: Number of operations
        
        Example:
            >>> sid = memory.new_session()
            >>> memory.set(sid, "name", "Alice")
            >>> memory.set(sid, "age", 30)
            >>> data = memory.get_all(sid)
            >>> print(data.keys())
            dict_keys(['created_at', 'last_updated', 'access_count', 'name', 'age'])
        """
        session_data = self.store.get(sid, {})
        
        if session_data:
            print(f"[SessionMemory] GET_ALL session={sid}: {len(session_data)} keys")
        else:
            print(f"[SessionMemory] ⚠ GET_ALL session={sid}: Session not found")
        
        # Return copy to prevent external modification
        return session_data.copy()
    
    def delete(self, sid: str) -> bool:
        """
        Delete an entire session and all its data.
        
        Args:
            sid (str): Session identifier to delete
        
        Returns:
            bool: True if session existed and was deleted, False otherwise
        
        Use Cases:
            - User explicitly ends conversation
            - Cleanup after processing complete
            - Memory management for long-running processes
        
        Example:
            >>> sid = memory.new_session()
            >>> memory.set(sid, "data", "value")
            >>> memory.delete(sid)
            True
            >>> memory.get(sid, "data")
            None  # Session no longer exists
        """
        if sid in self.store:
            # Get session info before deletion
            key_count = len(self.store[sid])
            
            # Delete session
            del self.store[sid]
            
            print(f"[SessionMemory] ✓ DELETED session={sid} ({key_count} keys)")
            return True
        else:
            print(f"[SessionMemory] ⚠ DELETE session={sid}: Session not found")
            return False
    
    def delete_key(self, sid: str, key: str) -> bool:
        """
        Delete a specific key from a session.
        
        Args:
            sid (str): Session identifier
            key (str): Key to delete
        
        Returns:
            bool: True if key existed and was deleted, False otherwise
        
        Restrictions:
            - Cannot delete reserved keys (metadata)
        
        Example:
            >>> sid = memory.new_session()
            >>> memory.set(sid, "temp_data", "value")
            >>> memory.delete_key(sid, "temp_data")
            True
        """
        if key in self.RESERVED_KEYS:
            print(f"[SessionMemory] ⚠ Cannot delete reserved key: {key}")
            return False
        
        if sid in self.store and key in self.store[sid]:
            del self.store[sid][key]
            self.store[sid]['last_updated'] = datetime.now().isoformat()
            print(f"[SessionMemory] ✓ DELETED key={key} from session={sid}")
            return True
        else:
            print(f"[SessionMemory] ⚠ Key={key} not found in session={sid}")
            return False
    
    def list_sessions(self) -> List[str]:
        """
        List all active session identifiers.
        
        Returns:
            List[str]: List of active session IDs
        
        Example:
            >>> memory = SessionMemory()
            >>> sid1 = memory.new_session()
            >>> sid2 = memory.new_session()
            >>> sessions = memory.list_sessions()
            >>> print(len(sessions))
            2
        """
        sessions = list(self.store.keys())
        print(f"[SessionMemory] LIST: {len(sessions)} active session(s)")
        return sessions
    
    def exists(self, sid: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            sid (str): Session identifier to check
        
        Returns:
            bool: True if session exists, False otherwise
        
        Example:
            >>> sid = memory.new_session()
            >>> memory.exists(sid)
            True
            >>> memory.exists("invalid_id")
            False
        """
        exists = sid in self.store
        print(f"[SessionMemory] EXISTS session={sid}: {exists}")
        return exists
    
    def get_session_age(self, sid: str) -> Optional[timedelta]:
        """
        Calculate how long a session has existed.
        
        Args:
            sid (str): Session identifier
        
        Returns:
            timedelta: Age of session, or None if session doesn't exist
        
        Example:
            >>> sid = memory.new_session()
            >>> import time
            >>> time.sleep(2)
            >>> age = memory.get_session_age(sid)
            >>> print(f"Age: {age.total_seconds():.1f}s")
            Age: 2.0s
        """
        if sid not in self.store:
            return None
        
        created_str = self.store[sid].get('created_at')
        if not created_str:
            return None
        
        created_at = datetime.fromisoformat(created_str)
        age = datetime.now() - created_at
        
        print(f"[SessionMemory] Session {sid} age: {age}")
        return age
    
    def cleanup_old_sessions(self, max_age_hours: int = DEFAULT_TTL_HOURS) -> int:
        """
        Remove sessions older than specified age.
        
        Args:
            max_age_hours (int): Maximum session age in hours (default: 24)
        
        Returns:
            int: Number of sessions deleted
        
        Use Cases:
            - Periodic cleanup in long-running services
            - Memory management
            - Remove abandoned sessions
        
        Example:
            >>> # Cleanup sessions older than 1 hour
            >>> deleted = memory.cleanup_old_sessions(max_age_hours=1)
            >>> print(f"Cleaned up {deleted} old sessions")
        """
        max_age = timedelta(hours=max_age_hours)
        now = datetime.now()
        to_delete = []
        
        # Find old sessions
        for sid, data in self.store.items():
            created_str = data.get('created_at')
            if created_str:
                created_at = datetime.fromisoformat(created_str)
                age = now - created_at
                
                if age > max_age:
                    to_delete.append(sid)
        
        # Delete old sessions
        for sid in to_delete:
            del self.store[sid]
        
        if to_delete:
            print(f"[SessionMemory] ✓ CLEANUP: Deleted {len(to_delete)} session(s) older than {max_age_hours}h")
        else:
            print(f"[SessionMemory] CLEANUP: No sessions older than {max_age_hours}h")
        
        return len(to_delete)
    
    def cleanup_inactive_sessions(self, inactive_hours: int = 2) -> int:
        """
        Remove sessions with no recent activity.
        
        Args:
            inactive_hours (int): Hours of inactivity before cleanup (default: 2)
        
        Returns:
            int: Number of sessions deleted
        
        Example:
            >>> deleted = memory.cleanup_inactive_sessions(inactive_hours=1)
        """
        max_inactive = timedelta(hours=inactive_hours)
        now = datetime.now()
        to_delete = []
        
        # Find inactive sessions
        for sid, data in self.store.items():
            updated_str = data.get('last_updated')
            if updated_str:
                last_updated = datetime.fromisoformat(updated_str)
                inactive_time = now - last_updated
                
                if inactive_time > max_inactive:
                    to_delete.append(sid)
        
        # Delete inactive sessions
        for sid in to_delete:
            del self.store[sid]
        
        if to_delete:
            print(f"[SessionMemory] ✓ CLEANUP: Deleted {len(to_delete)} inactive session(s) (>{inactive_hours}h)")
        else:
            print(f"[SessionMemory] CLEANUP: No inactive sessions (>{inactive_hours}h)")
        
        return len(to_delete)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Generate statistics about active sessions.
        
        Returns:
            Dict[str, Any]: Statistics including:
                - total_sessions: Number of active sessions
                - total_keys: Total keys across all sessions
                - avg_keys_per_session: Average keys per session
                - oldest_session: ID of oldest session
                - newest_session: ID of newest session
                - total_accesses: Sum of all access counts
        
        Example:
            >>> stats = memory.get_statistics()
            >>> print(f"Active sessions: {stats['total_sessions']}")
            >>> print(f"Avg keys per session: {stats['avg_keys_per_session']:.1f}")
        """
        if not self.store:
            return {
                'total_sessions': 0,
                'total_keys': 0,
                'avg_keys_per_session': 0,
                'oldest_session': None,
                'newest_session': None,
                'total_accesses': 0
            }
        
        total_keys = sum(len(data) - 3 for data in self.store.values())  # Exclude metadata
        total_accesses = sum(data.get('access_count', 0) for data in self.store.values())
        
        # Find oldest and newest
        sessions_by_age = sorted(
            self.store.items(),
            key=lambda x: x[1].get('created_at', '')
        )
        
        oldest_sid = sessions_by_age[0][0] if sessions_by_age else None
        newest_sid = sessions_by_age[-1][0] if sessions_by_age else None
        
        stats = {
            'total_sessions': len(self.store),
            'total_keys': total_keys,
            'avg_keys_per_session': total_keys / len(self.store) if self.store else 0,
            'oldest_session': oldest_sid,
            'newest_session': newest_sid,
            'total_accesses': total_accesses
        }
        
        return stats
    
    def clear_all(self) -> int:
        """
        Delete all sessions and data.
        
        Returns:
            int: Number of sessions deleted
        
        Warning:
            This operation cannot be undone!
        
        Example:
            >>> count = memory.clear_all()
            >>> print(f"Deleted {count} sessions")
        """
        count = len(self.store)
        self.store.clear()
        print(f"[SessionMemory] ⚠ CLEARED all data ({count} sessions)")
        return count


# Module-level utility functions
def create_session_memory() -> SessionMemory:
    """
    Factory function to create SessionMemory instance.
    
    Returns:
        SessionMemory: Initialized session memory
    
    Example:
        >>> memory = create_session_memory()
    """
    return SessionMemory()


if __name__ == "__main__":
    # Demo/testing code
    print("SessionMemory Demo")
    print("=" * 60)
    
    try:
        # Initialize memory
        memory = SessionMemory()
        
        # Test session creation
        print("\n📝 TESTING SESSION CREATION:")
        sid1 = memory.new_session()
        sid2 = memory.new_session()
        print(f"Created sessions: {sid1}, {sid2}")
        
        # Test data storage
        print("\n💾 TESTING DATA STORAGE:")
        memory.set(sid1, "user_name", "Alice")
        memory.set(sid1, "query", "What is AI?")
        memory.set(sid1, "results", {"count": 5, "data": [1, 2, 3, 4, 5]})
        
        memory.set(sid2, "user_name", "Bob")
        memory.set(sid2, "query", "How does ML work?")
        
        # Test retrieval
        print("\n📖 TESTING DATA RETRIEVAL:")
        name1 = memory.get(sid1, "user_name")
        query1 = memory.get(sid1, "query")
        print(f"Session 1 - User: {name1}, Query: {query1}")
        
        # Test get_all
        print("\n📚 TESTING GET_ALL:")
        data1 = memory.get_all(sid1)
        print(f"Session 1 keys: {list(data1.keys())}")
        
        # Test session listing
        print("\n📋 TESTING SESSION LISTING:")
        sessions = memory.list_sessions()
        print(f"Active sessions: {sessions}")
        
        # Test statistics
        print("\n📊 STATISTICS:")
        stats = memory.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Test session age
        print("\n⏰ TESTING SESSION AGE:")
        import time
        time.sleep(1)
        age = memory.get_session_age(sid1)
        print(f"Session {sid1} age: {age.total_seconds():.1f}s")
        
        # Test deletion
        print("\n🗑️ TESTING DELETION:")
        memory.delete_key(sid1, "results")
        memory.delete(sid2)
        print(f"Remaining sessions: {memory.list_sessions()}")
        
        print("\n✓ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()