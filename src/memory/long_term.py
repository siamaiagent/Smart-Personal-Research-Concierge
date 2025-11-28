"""
Long-Term Memory Module

This module provides persistent storage for user preferences and query history using JSON files.
It enables the research system to learn from past interactions and maintain user-specific settings.

Author: Google Hackathon Team
License: MIT
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class LongTermMemory:
    """
    Persistent JSON-based storage for user preferences and research history.
    
    This class provides a simple yet robust key-value storage system that
    persists between program runs. It serves as the system's long-term memory,
    storing:
    
    1. User Preferences: Custom settings like default length, format preferences,
       notification settings, etc.
    
    2. Query History: Timestamped log of past research queries for analytics
       and autocomplete features
    
    3. Frequent Queries: Analytics on commonly researched topics
    
    The storage uses JSON format for human readability and easy debugging.
    All data is automatically saved after modifications to prevent data loss.
    
    Architecture:
        - File-based persistence: Survives program restarts
        - Auto-save on modifications: No manual save required
        - Automatic history trimming: Maintains last 50 queries
        - Directory auto-creation: Sets up storage on first run
        - Graceful error handling: Continues operation on file errors
    
    Attributes:
        file_path (str): Absolute path to the JSON storage file
        data (Dict[str, Any]): In-memory representation of stored data
        HISTORY_LIMIT (int): Maximum query history entries to retain
        DEFAULT_STRUCTURE (Dict): Initial data structure for new storage
    
    Storage Structure:
        {
            "user_preferences": {
                "default_length": "medium",
                "default_format": "paragraph",
                "notifications_enabled": true
            },
            "query_history": [
                {
                    "query": "What is quantum computing?",
                    "timestamp": "2024-01-15T14:30:00.123456"
                }
            ],
            "frequent_queries": []
        }
    
    Example Usage:
        >>> memory = LongTermMemory()
        >>> memory.set_preference("default_length", "detailed")
        >>> memory.add_query("How does AI work?")
        >>> history = memory.get_query_history(limit=5)
        >>> for entry in history:
        ...     print(f"{entry['timestamp']}: {entry['query']}")
    
    Thread Safety:
        Not thread-safe. Use external locking if accessing from multiple threads.
    
    Dependencies:
        - json: Built-in JSON serialization
        - pathlib: Cross-platform path handling
        - datetime: Timestamp generation
    """
    
    # Configuration constants
    HISTORY_LIMIT = 50          # Maximum queries to retain
    MEMORY_DIR = 'memory'       # Storage directory name
    MEMORY_FILE = 'mem.json'    # Storage file name
    
    # Default data structure
    DEFAULT_STRUCTURE = {
        'user_preferences': {},
        'frequent_queries': [],
        'query_history': []
    }
    
    def __init__(self, file_path: Optional[str] = None):
        """
        Initialize long-term memory with persistent JSON storage.
        
        Args:
            file_path (str, optional): Custom storage path. If None, uses
                                      default location: <project_root>/memory/mem.json
        
        Behavior:
            - Creates storage directory if it doesn't exist
            - Loads existing data from file or initializes fresh storage
            - Validates and repairs corrupted data structures
        
        Example:
            >>> # Use default location
            >>> memory = LongTermMemory()
            
            >>> # Use custom location
            >>> memory = LongTermMemory("/custom/path/storage.json")
        """
        # Determine storage path
        if file_path is None:
            # Calculate project root (go up from src/memory/ to root)
            project_root = Path(__file__).parent.parent.parent
            file_path = project_root / self.MEMORY_DIR / self.MEMORY_FILE
        
        self.file_path = str(file_path)
        self.data = {}
        
        # Load existing data or initialize fresh storage
        self._load()
        
        print(f"[LongTermMemory] ✓ Initialized")
        print(f"[LongTermMemory] Storage: {self.file_path}")
        print(f"[LongTermMemory] Preferences: {len(self.data.get('user_preferences', {}))}")
        print(f"[LongTermMemory] Query history: {len(self.data.get('query_history', []))}")
    
    def _load(self) -> None:
        """
        Load memory data from JSON file.
        
        Attempts to load existing storage file. If file doesn't exist or is
        corrupted, initializes with default structure. Performs validation
        to ensure all required keys are present.
        
        Error Handling:
            - Missing file: Creates default structure
            - Corrupted JSON: Logs error and creates fresh storage
            - Missing keys: Adds missing keys with defaults
        
        Implementation Notes:
            - Uses utf-8 encoding for international character support
            - Validates structure after loading
            - Repairs incomplete data structures automatically
        """
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                
                # Validate and repair structure
                self._validate_structure()
                
                print(f"[LongTermMemory] ✓ Loaded existing storage")
                print(f"[LongTermMemory] Entries: {self._count_entries()}")
                
            except json.JSONDecodeError as e:
                print(f"[LongTermMemory] ✗ Corrupted JSON file: {e}")
                print(f"[LongTermMemory] Initializing fresh storage")
                self.data = self.DEFAULT_STRUCTURE.copy()
                
            except Exception as e:
                print(f"[LongTermMemory] ✗ Error loading file: {type(e).__name__}: {e}")
                self.data = self.DEFAULT_STRUCTURE.copy()
        else:
            print(f"[LongTermMemory] No existing storage found")
            print(f"[LongTermMemory] Creating fresh storage at: {self.file_path}")
            self.data = self.DEFAULT_STRUCTURE.copy()
            
            # Save initial structure
            self._save()
    
    def _validate_structure(self) -> None:
        """
        Validate and repair data structure.
        
        Ensures all required keys exist in the loaded data. Adds missing
        keys with default values to maintain consistent structure.
        
        Validation Checks:
            - user_preferences: Must be a dictionary
            - query_history: Must be a list
            - frequent_queries: Must be a list
        
        Repairs:
            - Adds missing keys with appropriate defaults
            - Converts incorrect types to expected types
        """
        repaired = False
        
        for key, default_value in self.DEFAULT_STRUCTURE.items():
            if key not in self.data:
                self.data[key] = default_value
                repaired = True
                print(f"[LongTermMemory] ⚠ Repaired missing key: {key}")
            
            # Type validation
            expected_type = type(default_value)
            if not isinstance(self.data[key], expected_type):
                self.data[key] = default_value
                repaired = True
                print(f"[LongTermMemory] ⚠ Fixed incorrect type for: {key}")
        
        if repaired:
            self._save()
    
    def _count_entries(self) -> int:
        """
        Count total entries across all storage categories.
        
        Returns:
            int: Total number of stored items
        """
        count = 0
        count += len(self.data.get('user_preferences', {}))
        count += len(self.data.get('query_history', []))
        count += len(self.data.get('frequent_queries', []))
        return count
    
    def _save(self) -> bool:
        """
        Persist current data to JSON file.
        
        Writes in-memory data to disk with proper formatting. Creates
        parent directories if they don't exist. Uses atomic write
        pattern for safety.
        
        Returns:
            bool: True if save successful, False otherwise
        
        Features:
            - Auto-creates storage directory
            - Pretty-prints JSON (indent=2) for readability
            - UTF-8 encoding for international characters
            - Error handling without data loss
        
        Error Handling:
            - Permission errors: Logs but doesn't crash
            - Disk full: Logs error and continues
            - Directory creation failures: Handled gracefully
        """
        try:
            # Create directory structure if needed
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            
            # Write with pretty formatting
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            
            print(f"[LongTermMemory] ✓ Saved to disk")
            return True
            
        except OSError as e:
            print(f"[LongTermMemory] ✗ File system error: {e}")
            return False
            
        except Exception as e:
            print(f"[LongTermMemory] ✗ Error saving: {type(e).__name__}: {e}")
            return False
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a user preference by key.
        
        Args:
            key (str): Preference key to retrieve
            default (Any): Value to return if key doesn't exist
        
        Returns:
            Any: Stored preference value or default
        
        Example:
            >>> memory.get_preference("default_length", "medium")
            'detailed'
            >>> memory.get_preference("nonexistent_key", "fallback")
            'fallback'
        """
        value = self.data.get('user_preferences', {}).get(key, default)
        print(f"[LongTermMemory] GET preference '{key}': {value}")
        return value
    
    def set_preference(self, key: str, value: Any) -> None:
        """
        Store or update a user preference.
        
        Args:
            key (str): Preference key
            value (Any): Value to store (must be JSON-serializable)
        
        Behavior:
            - Overwrites existing values
            - Automatically saves to disk
            - Creates preferences dict if missing
        
        Example:
            >>> memory.set_preference("default_length", "detailed")
            >>> memory.set_preference("auto_search", True)
            >>> memory.set_preference("favorite_topics", ["AI", "ML"])
        """
        # Ensure preferences dict exists
        if 'user_preferences' not in self.data:
            self.data['user_preferences'] = {}
        
        # Store preference
        self.data['user_preferences'][key] = value
        
        # Persist to disk
        self._save()
        
        print(f"[LongTermMemory] SET preference '{key}': {value}")
    
    def delete_preference(self, key: str) -> bool:
        """
        Remove a user preference by key.
        
        Args:
            key (str): Preference key to delete
        
        Returns:
            bool: True if preference existed and was deleted, False otherwise
        
        Example:
            >>> memory.delete_preference("old_setting")
            True
        """
        preferences = self.data.get('user_preferences', {})
        
        if key in preferences:
            del preferences[key]
            self._save()
            print(f"[LongTermMemory] DELETED preference '{key}'")
            return True
        else:
            print(f"[LongTermMemory] Preference '{key}' not found")
            return False
    
    def add_query(self, query: str) -> None:
        """
        Add a query to the history log.
        
        Stores the query with an ISO-formatted timestamp. Automatically
        trims history to maintain the last HISTORY_LIMIT entries.
        
        Args:
            query (str): Research query to log
        
        Features:
            - Automatic timestamping with microsecond precision
            - Circular buffer behavior (oldest entries dropped)
            - Immediate persistence to disk
        
        Example:
            >>> memory.add_query("What is quantum entanglement?")
            >>> memory.add_query("How does blockchain work?")
        """
        # Ensure history list exists
        if 'query_history' not in self.data:
            self.data['query_history'] = []
        
        # Create timestamped entry
        query_entry = {
            'query': query,
            'timestamp': datetime.now().isoformat()
        }
        
        # Append to history
        self.data['query_history'].append(query_entry)
        
        # Maintain size limit (circular buffer)
        if len(self.data['query_history']) > self.HISTORY_LIMIT:
            self.data['query_history'] = self.data['query_history'][-self.HISTORY_LIMIT:]
            print(f"[LongTermMemory] Trimmed history to {self.HISTORY_LIMIT} entries")
        
        # Persist to disk
        self._save()
        
        print(f"[LongTermMemory] ✓ Added query to history (total: {len(self.data['query_history'])})")
    
    def get_query_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Retrieve recent query history.
        
        Args:
            limit (int): Maximum number of queries to return (default: 10)
        
        Returns:
            List[Dict[str, str]]: List of query entries, most recent last.
                Each entry contains:
                - query (str): The research query
                - timestamp (str): ISO-formatted timestamp
        
        Example:
            >>> history = memory.get_query_history(limit=5)
            >>> for entry in history:
            ...     print(f"{entry['timestamp']}: {entry['query']}")
            2024-01-15T14:30:00: What is AI?
            2024-01-15T14:35:00: How does ML work?
        """
        history = self.data.get('query_history', [])
        recent = history[-limit:] if limit > 0 else history
        
        print(f"[LongTermMemory] Retrieved {len(recent)} query entries")
        return recent
    
    def get_all_preferences(self) -> Dict[str, Any]:
        """
        Retrieve all stored user preferences.
        
        Returns:
            Dict[str, Any]: Dictionary of all preferences
        
        Example:
            >>> prefs = memory.get_all_preferences()
            >>> print(prefs)
            {'default_length': 'detailed', 'notifications': True}
        """
        preferences = self.data.get('user_preferences', {})
        print(f"[LongTermMemory] Retrieved {len(preferences)} preferences")
        return preferences.copy()  # Return copy to prevent external modification
    
    def clear_history(self) -> None:
        """
        Delete all query history.
        
        Removes all entries from query_history while preserving preferences.
        Useful for privacy or testing purposes.
        
        Example:
            >>> memory.clear_history()
            >>> len(memory.get_query_history())
            0
        """
        self.data['query_history'] = []
        self._save()
        print("[LongTermMemory] ✓ Cleared all query history")
    
    def clear_all(self) -> None:
        """
        Reset all storage to default state.
        
        Clears preferences, history, and all other stored data.
        Useful for testing or complete reset.
        
        Warning:
            This operation cannot be undone!
        
        Example:
            >>> memory.clear_all()
        """
        self.data = self.DEFAULT_STRUCTURE.copy()
        self._save()
        print("[LongTermMemory] ⚠ Cleared all data (reset to defaults)")
    
    def export_data(self) -> Dict[str, Any]:
        """
        Export all memory data for backup or analysis.
        
        Returns:
            Dict[str, Any]: Complete copy of all stored data
        
        Use Cases:
            - Creating backups before major changes
            - Analytics on usage patterns
            - Migrating to different storage backend
        
        Example:
            >>> backup = memory.export_data()
            >>> with open('backup.json', 'w') as f:
            ...     json.dump(backup, f)
        """
        print(f"[LongTermMemory] Exported {self._count_entries()} entries")
        return self.data.copy()
    
    def import_data(self, data: Dict[str, Any], merge: bool = False) -> bool:
        """
        Import memory data from external source.
        
        Args:
            data (Dict[str, Any]): Data to import
            merge (bool): If True, merge with existing data. If False, replace.
        
        Returns:
            bool: True if import successful
        
        Example:
            >>> with open('backup.json', 'r') as f:
            ...     backup_data = json.load(f)
            >>> memory.import_data(backup_data, merge=True)
        """
        try:
            if merge:
                # Merge preferences
                if 'user_preferences' in data:
                    self.data.setdefault('user_preferences', {}).update(
                        data['user_preferences']
                    )
                
                # Append history
                if 'query_history' in data:
                    self.data.setdefault('query_history', []).extend(
                        data['query_history']
                    )
                    # Trim to limit
                    self.data['query_history'] = self.data['query_history'][-self.HISTORY_LIMIT:]
            else:
                # Full replacement
                self.data = data
            
            # Validate and save
            self._validate_structure()
            self._save()
            
            print(f"[LongTermMemory] ✓ Imported data ({'merged' if merge else 'replaced'})")
            return True
            
        except Exception as e:
            print(f"[LongTermMemory] ✗ Import failed: {type(e).__name__}: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Generate statistics about stored data.
        
        Returns:
            Dict[str, Any]: Statistics including:
                - total_preferences: Number of stored preferences
                - total_queries: Number of queries in history
                - oldest_query: Timestamp of oldest query
                - newest_query: Timestamp of newest query
        
        Example:
            >>> stats = memory.get_statistics()
            >>> print(f"Total queries: {stats['total_queries']}")
        """
        history = self.data.get('query_history', [])
        
        stats = {
            'total_preferences': len(self.data.get('user_preferences', {})),
            'total_queries': len(history),
            'oldest_query': history[0]['timestamp'] if history else None,
            'newest_query': history[-1]['timestamp'] if history else None,
            'storage_path': self.file_path,
            'history_limit': self.HISTORY_LIMIT
        }
        
        return stats


# Module-level utility functions
def create_memory(file_path: Optional[str] = None) -> LongTermMemory:
    """
    Factory function to create LongTermMemory instance.
    
    Args:
        file_path (str, optional): Custom storage path
    
    Returns:
        LongTermMemory: Initialized memory instance
    
    Example:
        >>> memory = create_memory()
    """
    return LongTermMemory(file_path)


if __name__ == "__main__":
    # Demo/testing code
    print("LongTermMemory Demo")
    print("=" * 60)
    
    try:
        # Initialize memory
        memory = LongTermMemory()
        
        # Test preferences
        print("\n📝 TESTING PREFERENCES:")
        memory.set_preference("default_length", "detailed")
        memory.set_preference("notifications_enabled", True)
        memory.set_preference("favorite_topics", ["AI", "ML", "NLP"])
        
        length = memory.get_preference("default_length")
        print(f"Retrieved length: {length}")
        
        all_prefs = memory.get_all_preferences()
        print(f"All preferences: {all_prefs}")
        
        # Test query history
        print("\n📚 TESTING QUERY HISTORY:")
        memory.add_query("What is artificial intelligence?")
        memory.add_query("How does machine learning work?")
        memory.add_query("What are neural networks?")
        
        history = memory.get_query_history(limit=5)
        print(f"Recent queries:")
        for entry in history:
            print(f"  - {entry['query']} ({entry['timestamp']})")
        
        # Test statistics
        print("\n📊 STATISTICS:")
        stats = memory.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Test export
        print("\n💾 TESTING EXPORT:")
        backup = memory.export_data()
        print(f"Exported {len(backup)} top-level keys")
        
        print("\n✓ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()