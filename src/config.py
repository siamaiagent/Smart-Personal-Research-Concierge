"""
Configuration settings for the Smart Personal Research Concierge.
"""

# Rate Limiting Configuration
RATE_LIMIT_REQUESTS_PER_MINUTE = 10  # Free tier: 10-15 safe
RATE_LIMIT_MAX_RETRIES = 3
RATE_LIMIT_BACKOFF_FACTOR = 2

# Model Configuration
GEMINI_MODEL = "gemini-2.0-flash"  # Can be changed based on availability

# Memory Configuration
MEMORY_FILE = "memory/mem.json"
JOBS_FILE = "jobs.json"

# Observability Configuration
LOG_FILE = "logs/agent.log"
METRICS_FILE = "logs/metrics.json"
