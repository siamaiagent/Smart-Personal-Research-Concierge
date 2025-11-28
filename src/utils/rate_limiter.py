"""
Rate Limiter Utility Module

This module provides robust API rate limiting and retry logic with exponential backoff.
Prevents API quota exhaustion and handles transient failures gracefully.

Author: Google Hackathon Team
License: MIT
"""

import logging
import re
import time
from functools import wraps
from typing import Optional, Callable, Any
from threading import Lock


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class RateLimiter:
    """
    Thread-safe rate limiter for API request throttling with intelligent wait management.
    
    This class implements a simple but effective rate limiting strategy using
    time-based throttling. It ensures API calls don't exceed specified quotas
    by enforcing minimum intervals between consecutive requests.
    
    Key Features:
    
    1. Automatic Throttling:
       - Calculates minimum interval between requests
       - Automatically sleeps if requests are too frequent
       - Thread-safe for concurrent usage
    
    2. Flexible Configuration:
       - Configurable requests per minute
       - Adjustable at initialization
       - Global singleton pattern available
    
    3. Transparent Operation:
       - Detailed logging of wait times
       - No impact on application logic
       - Works with any API or function
    
    Architecture:
        - Uses timestamp tracking for request timing
        - Thread lock prevents race conditions
        - Calculates sleep time dynamically
        - Logs all throttling actions
    
    Attributes:
        requests_per_minute (int): Maximum allowed requests per minute
        min_interval (float): Minimum seconds between requests
        last_request_time (float): Timestamp of last request
        _lock (Lock): Thread synchronization lock
        _request_count (int): Total requests processed
    
    Mathematical Model:
        min_interval = 60 / requests_per_minute
        
        Examples:
        - 10 req/min → 6.0s interval
        - 20 req/min → 3.0s interval
        - 60 req/min → 1.0s interval
    
    Example Usage:
        >>> limiter = RateLimiter(requests_per_minute=10)
        >>> for i in range(20):
        ...     limiter.wait_if_needed()
        ...     make_api_call()  # Guaranteed to respect rate limit
        
        >>> # With custom rate
        >>> fast_limiter = RateLimiter(requests_per_minute=30)
        >>> slow_limiter = RateLimiter(requests_per_minute=5)
    
    Thread Safety:
        Thread-safe through Lock usage. Multiple threads can safely
        share a single RateLimiter instance.
    
    Performance:
        - O(1) time complexity for wait calculation
        - Minimal memory footprint (~100 bytes)
        - No external dependencies beyond stdlib
    """
    
    # Default configuration
    DEFAULT_REQUESTS_PER_MINUTE = 10
    MIN_REQUESTS_PER_MINUTE = 1
    MAX_REQUESTS_PER_MINUTE = 60
    
    def __init__(self, requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE):
        """
        Initialize rate limiter with specified request quota.
        
        Args:
            requests_per_minute (int): Maximum requests per minute (1-60).
                                      Default: 10 requests/minute (6s interval)
        
        Raises:
            ValueError: If requests_per_minute is out of valid range
        
        Example:
            >>> # Conservative rate limiting
            >>> limiter = RateLimiter(requests_per_minute=5)
            
            >>> # Moderate rate limiting (default)
            >>> limiter = RateLimiter()
            
            >>> # Aggressive rate limiting (use carefully!)
            >>> limiter = RateLimiter(requests_per_minute=30)
        """
        # Validate input
        if not self.MIN_REQUESTS_PER_MINUTE <= requests_per_minute <= self.MAX_REQUESTS_PER_MINUTE:
            raise ValueError(
                f"requests_per_minute must be between {self.MIN_REQUESTS_PER_MINUTE} "
                f"and {self.MAX_REQUESTS_PER_MINUTE}, got {requests_per_minute}"
            )
        
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self.last_request_time = 0.0
        self._lock = Lock()
        self._request_count = 0
        
        logging.info(
            f"[RateLimiter] ✓ Initialized: {requests_per_minute} req/min "
            f"(min interval: {self.min_interval:.2f}s)"
        )
    
    def wait_if_needed(self) -> float:
        """
        Wait if necessary to respect rate limit.
        
        This method checks if enough time has passed since the last request.
        If not, it sleeps for the remaining time to maintain the rate limit.
        
        Returns:
            float: Actual time waited in seconds (0 if no wait needed)
        
        Thread Safety:
            Uses lock to ensure thread-safe operation. Multiple threads
            will queue and each will respect the rate limit.
        
        Example:
            >>> limiter = RateLimiter(requests_per_minute=10)
            >>> 
            >>> # Before API call
            >>> wait_time = limiter.wait_if_needed()
            >>> print(f"Waited {wait_time:.2f}s")
            >>> 
            >>> # Make API call
            >>> response = api_call()
        """
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            # Calculate required wait time
            wait_needed = self.min_interval - time_since_last
            
            if wait_needed > 0:
                logging.info(
                    f"[RateLimiter] ⏳ Throttling: waiting {wait_needed:.2f}s "
                    f"(request #{self._request_count + 1})"
                )
                time.sleep(wait_needed)
                actual_wait = wait_needed
            else:
                actual_wait = 0.0
            
            # Update timestamp and counter
            self.last_request_time = time.time()
            self._request_count += 1
            
            return actual_wait
    
    def get_statistics(self) -> dict:
        """
        Get rate limiter statistics and configuration.
        
        Returns:
            dict: Statistics including:
                - requests_per_minute: Configured rate limit
                - min_interval: Minimum seconds between requests
                - total_requests: Total requests processed
                - last_request_time: Timestamp of last request
                - time_since_last: Seconds since last request
        
        Example:
            >>> limiter = RateLimiter()
            >>> limiter.wait_if_needed()
            >>> stats = limiter.get_statistics()
            >>> print(f"Processed {stats['total_requests']} requests")
        """
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time if self.last_request_time > 0 else 0
            
            return {
                'requests_per_minute': self.requests_per_minute,
                'min_interval': self.min_interval,
                'total_requests': self._request_count,
                'last_request_time': self.last_request_time,
                'time_since_last': time_since_last
            }
    
    def reset(self) -> None:
        """
        Reset rate limiter state.
        
        Clears request history and counters. Useful for testing
        or starting fresh after a long idle period.
        
        Example:
            >>> limiter = RateLimiter()
            >>> # ... make some requests ...
            >>> limiter.reset()
            >>> # Fresh start with no wait required
        """
        with self._lock:
            self.last_request_time = 0.0
            self._request_count = 0
            logging.info("[RateLimiter] ✓ Reset complete")


def retry_on_rate_limit(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_wait: float = 1.0
) -> Callable:
    """
    Decorator for automatic retry with exponential backoff on rate limit errors.
    
    This decorator wraps functions to automatically retry when rate limit
    errors occur. It implements intelligent exponential backoff and can
    extract suggested wait times from error messages.
    
    Key Features:
    
    1. Automatic Retry:
       - Detects rate limit errors (429 status, quota messages)
       - Retries up to max_retries times
       - Raises original error after max attempts
    
    2. Exponential Backoff:
       - Wait time increases exponentially: 1s, 2s, 4s, 8s...
       - Prevents thundering herd problem
       - Configurable backoff factor
    
    3. Smart Wait Extraction:
       - Parses "Retry after X seconds" from errors
       - Adds buffer to suggested wait times
       - Falls back to exponential backoff if not found
    
    Args:
        max_retries (int): Maximum retry attempts (default: 3)
        backoff_factor (float): Exponential multiplier (default: 2.0)
        initial_wait (float): First retry wait time in seconds (default: 1.0)
    
    Returns:
        Callable: Decorated function with retry logic
    
    Error Detection:
        Catches rate limit errors by checking for:
        - "429" (HTTP Too Many Requests)
        - "quota exceeded" (case-insensitive)
        - "rate limit" (case-insensitive)
    
    Wait Time Calculation:
        1. Check error message for "retry in Xs" or "retry after Xs"
        2. If found: use that time + 1 second buffer
        3. If not found: use exponential backoff
        
        Backoff formula: wait_time = initial_wait * (backoff_factor ^ retry_count)
    
    Example Usage:
        >>> @retry_on_rate_limit(max_retries=3, backoff_factor=2)
        ... def call_api():
        ...     return gemini.generate_content(prompt)
        
        >>> # Custom configuration
        >>> @retry_on_rate_limit(max_retries=5, backoff_factor=1.5, initial_wait=2.0)
        ... def critical_api_call():
        ...     return important_operation()
        
        >>> # Usage
        >>> try:
        ...     result = call_api()
        ... except Exception as e:
        ...     print(f"Failed after retries: {e}")
    
    Logging:
        - Logs each retry attempt with wait time
        - Logs max retry exhaustion
        - Logs successful retry recovery
    
    Thread Safety:
        Decorator itself is thread-safe. However, if the wrapped function
        modifies shared state, external synchronization is required.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retries = 0
            wait_time = initial_wait
            
            while retries <= max_retries:
                try:
                    # Attempt function call
                    result = func(*args, **kwargs)
                    
                    # Log successful retry if this isn't first attempt
                    if retries > 0:
                        logging.info(
                            f"[RateLimiter] ✓ Success after {retries} retry(ies) "
                            f"for {func.__name__}"
                        )
                    
                    return result
                
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # Check if it's a rate limit error
                    is_rate_limit_error = any([
                        '429' in str(e),
                        'quota exceeded' in error_str,
                        'rate limit' in error_str,
                        'too many requests' in error_str
                    ])
                    
                    if not is_rate_limit_error:
                        # Not a rate limit error - raise immediately
                        raise
                    
                    # Rate limit error detected
                    retries += 1
                    
                    if retries > max_retries:
                        logging.error(
                            f"[RateLimiter] ✗ Max retries ({max_retries}) exhausted "
                            f"for {func.__name__}"
                        )
                        raise
                    
                    # Try to extract suggested wait time from error
                    suggested_wait = _extract_wait_time(str(e))
                    if suggested_wait:
                        wait_time = suggested_wait + 1.0  # Add 1s buffer
                        logging.info(
                            f"[RateLimiter] ⚠ Using suggested wait time: {wait_time:.1f}s"
                        )
                    
                    # Log retry attempt
                    logging.warning(
                        f"[RateLimiter] ⚠ Rate limit hit for {func.__name__}. "
                        f"Retry {retries}/{max_retries} after {wait_time:.1f}s..."
                    )
                    
                    # Wait before retry
                    time.sleep(wait_time)
                    
                    # Exponential backoff for next attempt
                    wait_time *= backoff_factor
            
            # Should never reach here, but just in case
            return None
        
        return wrapper
    return decorator


def _extract_wait_time(error_message: str) -> Optional[float]:
    """
    Extract suggested wait time from error message.
    
    Args:
        error_message (str): Error message to parse
    
    Returns:
        Optional[float]: Extracted wait time in seconds, or None
    
    Patterns Matched:
        - "retry in 5s"
        - "retry after 5 seconds"
        - "wait 5.5s"
        - "retry in 5.0 seconds"
    
    Example:
        >>> _extract_wait_time("Rate limit exceeded. Retry in 5s")
        5.0
        >>> _extract_wait_time("Quota exceeded. Retry after 10.5 seconds")
        10.5
        >>> _extract_wait_time("Unknown error")
        None
    """
    patterns = [
        r'retry in (\d+\.?\d*)\s*s',
        r'retry after (\d+\.?\d*)\s*s',
        r'wait (\d+\.?\d*)\s*s',
        r'retry in (\d+\.?\d*)\s*seconds?',
        r'retry after (\d+\.?\d*)\s*seconds?'
    ]
    
    error_lower = error_message.lower()
    
    for pattern in patterns:
        match = re.search(pattern, error_lower)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                continue
    
    return None


# Global rate limiter singleton
_global_rate_limiter: Optional[RateLimiter] = None
_global_lock = Lock()


def get_rate_limiter(requests_per_minute: int = 10) -> RateLimiter:
    """
    Get or create global rate limiter singleton instance.
    
    This function provides a convenient way to access a shared rate limiter
    across the entire application. The singleton pattern ensures all API
    calls share the same rate limiting state.
    
    Args:
        requests_per_minute (int): Rate limit (only used on first call)
    
    Returns:
        RateLimiter: Global rate limiter instance
    
    Thread Safety:
        Thread-safe initialization using Lock. Multiple threads calling
        this function simultaneously will safely get the same instance.
    
    Note:
        The requests_per_minute parameter only takes effect on the first
        call. Subsequent calls return the existing instance with its
        original configuration.
    
    Example:
        >>> # First call creates instance
        >>> limiter1 = get_rate_limiter(requests_per_minute=10)
        
        >>> # Subsequent calls return same instance
        >>> limiter2 = get_rate_limiter()
        >>> assert limiter1 is limiter2  # Same object
        
        >>> # Use in different modules
        >>> # module1.py
        >>> limiter = get_rate_limiter()
        >>> limiter.wait_if_needed()
        
        >>> # module2.py
        >>> limiter = get_rate_limiter()  # Same instance!
        >>> limiter.wait_if_needed()
    """
    global _global_rate_limiter
    
    with _global_lock:
        if _global_rate_limiter is None:
            _global_rate_limiter = RateLimiter(requests_per_minute)
            logging.info("[RateLimiter] ✓ Global instance created")
        
        return _global_rate_limiter


def reset_global_rate_limiter() -> None:
    """
    Reset global rate limiter singleton.
    
    Clears the global instance, allowing creation of a new one with
    different configuration. Useful for testing or reconfiguration.
    
    Example:
        >>> limiter1 = get_rate_limiter(requests_per_minute=10)
        >>> reset_global_rate_limiter()
        >>> limiter2 = get_rate_limiter(requests_per_minute=20)
        >>> assert limiter1 is not limiter2  # Different objects
    """
    global _global_rate_limiter
    
    with _global_lock:
        _global_rate_limiter = None
        logging.info("[RateLimiter] ✓ Global instance reset")


if __name__ == "__main__":
    # Demo/testing code
    print("RateLimiter Demo")
    print("=" * 60)
    
    # Test 1: Basic rate limiting
    print("\n🔄 TEST 1: Basic Rate Limiting (10 req/min)")
    limiter = RateLimiter(requests_per_minute=10)
    
    for i in range(3):
        print(f"\nRequest {i+1}:")
        wait_time = limiter.wait_if_needed()
        print(f"  Waited: {wait_time:.2f}s")
        print(f"  Making API call...")
    
    # Test 2: Statistics
    print("\n\n📊 TEST 2: Statistics")
    stats = limiter.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test 3: Retry decorator
    print("\n\n🔁 TEST 3: Retry Decorator")
    
    attempt_count = 0
    
    @retry_on_rate_limit(max_retries=3, backoff_factor=1.5)
    def simulated_api_call():
        global attempt_count
        attempt_count += 1
        print(f"  Attempt {attempt_count}")
        
        if attempt_count < 2:
            raise Exception("429: Rate limit exceeded. Retry in 2s")
        
        return "Success!"
    
    try:
        result = simulated_api_call()
        print(f"  Result: {result}")
    except Exception as e:
        print(f"  Failed: {e}")
    
    # Test 4: Wait time extraction
    print("\n\n🔍 TEST 4: Wait Time Extraction")
    test_messages = [
        "Rate limit exceeded. Retry in 5s",
        "Quota exceeded. Retry after 10.5 seconds",
        "No wait time in this message"
    ]
    
    for msg in test_messages:
        wait = _extract_wait_time(msg)
        print(f"  '{msg[:40]}...' → {wait}s")
    
    # Test 5: Global singleton
    print("\n\n🌍 TEST 5: Global Singleton")
    limiter1 = get_rate_limiter(requests_per_minute=15)
    limiter2 = get_rate_limiter()
    print(f"  Same instance: {limiter1 is limiter2}")
    print(f"  Request rate: {limiter1.requests_per_minute} req/min")
    
    print("\n✓ All tests complete!")