"""
Rate limiter utility to handle API request throttling and retries.
Prevents hitting Gemini API rate limits during operation.
"""

import time
import logging
from functools import wraps

class RateLimiter:
    """
    Simple rate limiter that enforces delays between API calls.
    """
    
    def __init__(self, requests_per_minute=10):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute  # Seconds between requests
        self.last_request_time = 0
        logging.info(f"[RateLimiter] Initialized: {requests_per_minute} requests/minute "
                    f"(min {self.min_interval:.2f}s between calls)")
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limit"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            logging.info(f"[RateLimiter] Waiting {sleep_time:.2f}s to respect rate limit...")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


def retry_on_rate_limit(max_retries=3, backoff_factor=2):
    """
    Decorator to automatically retry on rate limit errors.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for wait time between retries
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            wait_time = 1  # Start with 1 second
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    error_str = str(e)
                    
                    # Check if it's a rate limit error (429)
                    if '429' in error_str or 'quota exceeded' in error_str.lower():
                        retries += 1
                        
                        if retries >= max_retries:
                            logging.error(f"[RateLimiter] Max retries ({max_retries}) reached")
                            raise
                        
                        # Extract suggested wait time from error message
                        if 'retry in' in error_str.lower():
                            try:
                                # Extract wait time from error message
                                import re
                                match = re.search(r'retry in (\d+\.?\d*)s', error_str.lower())
                                if match:
                                    wait_time = float(match.group(1)) + 1  # Add 1 second buffer
                            except:
                                pass
                        
                        logging.warning(f"[RateLimiter] Rate limit hit. Retry {retries}/{max_retries} "
                                      f"after {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        wait_time *= backoff_factor  # Exponential backoff
                    else:
                        # Not a rate limit error, raise immediately
                        raise
            
            return None
        
        return wrapper
    return decorator


# Global rate limiter instance
_global_rate_limiter = None

def get_rate_limiter(requests_per_minute=10):
    """Get or create global rate limiter instance"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(requests_per_minute)
    return _global_rate_limiter