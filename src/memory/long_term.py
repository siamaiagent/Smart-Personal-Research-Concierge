"""
Persistent long-term memory using JSON file storage.

Stores user preferences, query history, and other data that persists
between program runs. Data is saved to memory/mem.json.
"""

import json
import os
from datetime import datetime

class LongTermMemory:
    """
    Persistent storage using JSON file.
    Data survives between program runs.
    Stores user preferences and frequent queries.
    """
    
    def __init__(self, file_path=None):
        # Always save to project root /memory folder
        if file_path is None:
            # Get project root directory
            import sys
            from pathlib import Path
        
        # Go up from src/memory/ to project root
        project_root = Path(__file__).parent.parent.parent
        file_path = project_root / 'memory' / 'mem.json'
    
        self.file_path = str(file_path)
        self.data = {}
        self._load()
        print(f"[LongTermMemory] Initialized with file: {self.file_path}")
    
    def _load(self):
        """Load memory from JSON file"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    self.data = json.load(f)
                print(f"[LongTermMemory] Loaded {len(self.data)} entries from file")
            except Exception as e:
                print(f"[LongTermMemory] Error loading file: {e}")
                self.data = {}
        else:
            print(f"[LongTermMemory] No existing memory file found, starting fresh")
            self.data = {
                'user_preferences': {},
                'frequent_queries': [],
                'query_history': []
            }
    
    def _save(self):
        """Save memory to JSON file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            
            with open(self.file_path, 'w') as f:
                json.dump(self.data, f, indent=2)
            print(f"[LongTermMemory] Saved to file")
        except Exception as e:
            print(f"[LongTermMemory] Error saving file: {e}")
    
    def get_preference(self, key, default=None):
        """Get a user preference"""
        value = self.data.get('user_preferences', {}).get(key, default)
        print(f"[LongTermMemory] GET preference: {key} = {value}")
        return value
    
    def set_preference(self, key, value):
        """Set a user preference"""
        if 'user_preferences' not in self.data:
            self.data['user_preferences'] = {}
        
        self.data['user_preferences'][key] = value
        self._save()
        print(f"[LongTermMemory] SET preference: {key} = {value}")
    
    def add_query(self, query):
        """Add a query to history"""
        if 'query_history' not in self.data:
            self.data['query_history'] = []
        
        query_entry = {
            'query': query,
            'timestamp': datetime.now().isoformat()
        }
        
        self.data['query_history'].append(query_entry)
        
        # Keep only last 50 queries
        self.data['query_history'] = self.data['query_history'][-50:]
        
        self._save()
        print(f"[LongTermMemory] Added query to history")
    
    def get_query_history(self, limit=10):
        """Get recent query history"""
        history = self.data.get('query_history', [])
        return history[-limit:]
    
    def get_all_preferences(self):
        """Get all user preferences"""
        return self.data.get('user_preferences', {})
    
    def clear_history(self):
        """Clear query history"""
        self.data['query_history'] = []
        self._save()
        print("[LongTermMemory] Cleared query history")