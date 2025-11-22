"""
In-memory session storage for temporary conversation data.

Stores session-specific data that is lost when program exits.
Each session has a unique ID and can store key-value pairs.
"""

import uuid
from datetime import datetime

class SessionMemory:
    """
    In-memory storage for session-specific data.
    Each session is identified by a unique session_id.
    Memory is lost when program stops.
    """
    
    def __init__(self):
        self.store = {}
        print("[SessionMemory] Initialized")
    
    def get(self, sid, key, default=None):
        """
        Get a value from session storage.
        
        Args:
            sid: Session ID
            key: Key to retrieve
            default: Default value if not found
            
        Returns:
            Stored value or default
        """
        value = self.store.get(sid, {}).get(key, default)
        print(f"[SessionMemory] GET session={sid}, key={key}, value={value}")
        return value
    
    def set(self, sid, key, value):
        """
        Store a value in session storage.
        
        Args:
            sid: Session ID
            key: Key to store
            value: Value to store
        """
        if sid not in self.store:
            self.store[sid] = {
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
        
        self.store[sid][key] = value
        self.store[sid]['last_updated'] = datetime.now().isoformat()
        
        print(f"[SessionMemory] SET session={sid}, key={key}, value={value}")
    
    def get_all(self, sid):
        """Get all data for a session"""
        return self.store.get(sid, {})
    
    def delete(self, sid):
        """Delete an entire session"""
        if sid in self.store:
            del self.store[sid]
            print(f"[SessionMemory] DELETED session={sid}")
    
    def new_session(self):
        """Create a new session ID"""
        sid = str(uuid.uuid4())[:8]  # Short UUID
        print(f"[SessionMemory] NEW session created: {sid}")
        return sid
    
    def list_sessions(self):
        """List all active session IDs"""
        return list(self.store.keys())