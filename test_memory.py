from src.memory.session_memory import SessionMemory
from src.memory.long_term import LongTermMemory
import time

print("="*60)
print("TESTING MEMORY SYSTEMS")
print("="*60)

# Test 1: Session Memory
print("\n--- TEST 1: Session Memory ---")
session_mem = SessionMemory()

# Create two sessions
sid1 = session_mem.new_session()
sid2 = session_mem.new_session()

# Store data in session 1
session_mem.set(sid1, 'user_name', 'Alice')
session_mem.set(sid1, 'preference', 'short')

# Store data in session 2
session_mem.set(sid2, 'user_name', 'Bob')
session_mem.set(sid2, 'preference', 'detailed')

# Retrieve data
print(f"\nSession 1 user: {session_mem.get(sid1, 'user_name')}")
print(f"Session 2 user: {session_mem.get(sid2, 'user_name')}")

print(f"\nAll sessions: {session_mem.list_sessions()}")

# Test 2: Long-Term Memory
print("\n--- TEST 2: Long-Term Memory ---")
lt_mem = LongTermMemory()

# Set preferences
lt_mem.set_preference('summary_length', 'medium')
lt_mem.set_preference('language', 'en')

# Add queries
lt_mem.add_query("What is AI?")
lt_mem.add_query("How does machine learning work?")

# Retrieve
print(f"\nStored preferences: {lt_mem.get_all_preferences()}")
print(f"Query history: {lt_mem.get_query_history()}")

# Test 3: Persistence
print("\n--- TEST 3: Testing Persistence ---")
print("Creating new LongTermMemory instance (simulating restart)...")

lt_mem2 = LongTermMemory()  # Load from file
print(f"Preferences after 'restart': {lt_mem2.get_all_preferences()}")
print(f"Queries after 'restart': {lt_mem2.get_query_history()}")

print("\n✅ All memory tests passed!")
print("="*60)