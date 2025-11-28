"""
Configuration Settings Module

This module centralizes all configuration settings for the Smart Personal Research Concierge.
It provides type-safe, well-documented configuration with validation and environment support.

Author: Google Hackathon Team
License: MIT
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


# =============================================================================
# PROJECT PATHS
# =============================================================================

# Project root directory (parent of config.py)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Data directories
MEMORY_DIR = PROJECT_ROOT / "memory"
LOGS_DIR = PROJECT_ROOT / "logs"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# Ensure directories exist
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# RATE LIMITING CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class RateLimitConfig:
    """
    Rate limiting configuration for API requests.
    
    These settings control how aggressively the system makes API calls
    to prevent hitting quota limits and ensure stable operation.
    
    Attributes:
        requests_per_minute (int): Maximum API requests per minute
        max_retries (int): Retry attempts on rate limit errors
        backoff_factor (float): Exponential backoff multiplier
        initial_wait (float): Initial retry wait time in seconds
    
    Tier Recommendations:
        Free Tier:
            - requests_per_minute: 10-15 (conservative)
            - Prevents quota exhaustion
            - Safe for extended operation
        
        Paid Tier:
            - requests_per_minute: 30-60
            - Faster research completion
            - Higher throughput
    
    Performance Impact:
        10 req/min:  ~6s per API call (very safe)
        15 req/min:  ~4s per API call (safe)
        30 req/min:  ~2s per API call (moderate)
        60 req/min:  ~1s per API call (aggressive)
    """
    requests_per_minute: int = 10
    max_retries: int = 3
    backoff_factor: float = 2.0
    initial_wait: float = 1.0
    
    def validate(self) -> None:
        """Validate configuration values."""
        if not 1 <= self.requests_per_minute <= 60:
            raise ValueError(f"requests_per_minute must be 1-60, got {self.requests_per_minute}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be non-negative, got {self.max_retries}")
        if self.backoff_factor < 1.0:
            raise ValueError(f"backoff_factor must be >= 1.0, got {self.backoff_factor}")


# Default rate limiting configuration
RATE_LIMIT = RateLimitConfig()


# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class ModelConfig:
    """
    AI model configuration settings.
    
    Attributes:
        name (str): Gemini model identifier
        temperature (float): Sampling temperature (0.0-1.0)
        top_p (float): Nucleus sampling parameter
        top_k (int): Top-k sampling parameter
        max_output_tokens (int): Maximum tokens in response
    
    Available Models:
        - gemini-2.0-flash: Fast, efficient (recommended)
        - gemini-pro: High quality, slower
        - gemini-pro-vision: Multimodal support
    
    Temperature Guide:
        0.0-0.3:  Deterministic, focused (fact-checking)
        0.4-0.7:  Balanced creativity (research synthesis)
        0.8-1.0:  Creative, diverse (brainstorming)
    """
    name: str = "gemini-2.0-flash"
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 40
    max_output_tokens: int = 2048
    
    def validate(self) -> None:
        """Validate configuration values."""
        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError(f"temperature must be 0.0-1.0, got {self.temperature}")
        if not 0.0 <= self.top_p <= 1.0:
            raise ValueError(f"top_p must be 0.0-1.0, got {self.top_p}")
        if self.top_k < 1:
            raise ValueError(f"top_k must be positive, got {self.top_k}")
        if self.max_output_tokens < 1:
            raise ValueError(f"max_output_tokens must be positive, got {self.max_output_tokens}")


# Default model configuration
MODEL = ModelConfig()


# =============================================================================
# MEMORY CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class MemoryConfig:
    """
    Memory storage configuration.
    
    Attributes:
        long_term_file (Path): Persistent JSON storage path
        jobs_file (Path): Research jobs tracking file
        query_history_limit (int): Max queries to retain
        auto_cleanup_enabled (bool): Enable periodic cleanup
        cleanup_days (int): Days before cleaning old data
    
    Storage Structure:
        memory/
            mem.json           - User preferences & history
            jobs.json          - Background job tracking
    """
    long_term_file: Path = MEMORY_DIR / "mem.json"
    jobs_file: Path = MEMORY_DIR / "jobs.json"
    query_history_limit: int = 50
    auto_cleanup_enabled: bool = True
    cleanup_days: int = 30
    
    def validate(self) -> None:
        """Validate configuration values."""
        if self.query_history_limit < 1:
            raise ValueError(f"query_history_limit must be positive, got {self.query_history_limit}")
        if self.cleanup_days < 1:
            raise ValueError(f"cleanup_days must be positive, got {self.cleanup_days}")


# Default memory configuration
MEMORY = MemoryConfig()


# =============================================================================
# RESEARCH PIPELINE CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class ResearchConfig:
    """
    Research pipeline configuration.
    
    Attributes:
        min_subtopics (int): Minimum research subtopics
        max_subtopics (int): Maximum research subtopics
        results_per_subtopic (int): Search results per subtopic
        enable_scraping (bool): Enable web scraping
        enable_fact_checking (bool): Enable fact verification
        parallel_research (bool): Enable parallel subtopic research
        confidence_threshold (float): Minimum fact-check confidence
    
    Pipeline Modes:
        Fast Mode:
            - parallel_research: True
            - enable_scraping: False
            - enable_fact_checking: False
            - Duration: ~10-20 seconds
        
        Quality Mode:
            - parallel_research: False
            - enable_scraping: True
            - enable_fact_checking: True
            - Duration: ~30-60 seconds
        
        Balanced Mode (Default):
            - parallel_research: True
            - enable_scraping: False
            - enable_fact_checking: True
            - Duration: ~15-30 seconds
    """
    min_subtopics: int = 3
    max_subtopics: int = 5
    results_per_subtopic: int = 3
    enable_scraping: bool = False
    enable_fact_checking: bool = True
    parallel_research: bool = True
    confidence_threshold: float = 0.6
    
    def validate(self) -> None:
        """Validate configuration values."""
        if not 1 <= self.min_subtopics <= self.max_subtopics:
            raise ValueError(f"Invalid subtopic range: {self.min_subtopics}-{self.max_subtopics}")
        if self.results_per_subtopic < 1:
            raise ValueError(f"results_per_subtopic must be positive, got {self.results_per_subtopic}")
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(f"confidence_threshold must be 0.0-1.0, got {self.confidence_threshold}")


# Default research configuration
RESEARCH = ResearchConfig()


# =============================================================================
# SCRAPING CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class ScrapingConfig:
    """
    Web scraping configuration.
    
    Attributes:
        timeout (int): Request timeout in seconds
        rate_limit_delay (float): Delay between scrape requests
        min_paragraph_length (int): Minimum paragraph character count
        max_paragraphs (int): Maximum paragraphs to extract
        user_agent (str): HTTP User-Agent header
        respect_robots_txt (bool): Check robots.txt (TODO)
    
    Ethical Guidelines:
        - Always respect robots.txt
        - Use reasonable rate limiting
        - Identify bot with User-Agent
        - Only scrape public content
    """
    timeout: int = 6
    rate_limit_delay: float = 1.0
    min_paragraph_length: int = 50
    max_paragraphs: int = 10
    user_agent: str = "Mozilla/5.0 (compatible; ResearchBot/1.0; +https://github.com/yourproject)"
    respect_robots_txt: bool = False  # TODO: Implement
    
    def validate(self) -> None:
        """Validate configuration values."""
        if self.timeout < 1:
            raise ValueError(f"timeout must be positive, got {self.timeout}")
        if self.rate_limit_delay < 0:
            raise ValueError(f"rate_limit_delay must be non-negative, got {self.rate_limit_delay}")


# Default scraping configuration
SCRAPING = ScrapingConfig()


# =============================================================================
# OBSERVABILITY CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class ObservabilityConfig:
    """
    Logging and metrics configuration.
    
    Attributes:
        log_file (Path): Application log file path
        metrics_file (Path): Performance metrics JSON file
        log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_metrics (bool): Track performance metrics
        enable_console_output (bool): Print to console
        log_format (str): Log message format
    
    Log Levels:
        DEBUG:   Detailed debugging information
        INFO:    General informational messages
        WARNING: Warning messages (non-critical)
        ERROR:   Error messages (critical issues)
    """
    log_file: Path = LOGS_DIR / "agent.log"
    metrics_file: Path = LOGS_DIR / "metrics.json"
    log_level: str = "INFO"
    enable_metrics: bool = True
    enable_console_output: bool = True
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def validate(self) -> None:
        """Validate configuration values."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}, got {self.log_level}")


# Default observability configuration
OBSERVABILITY = ObservabilityConfig()


# =============================================================================
# ENVIRONMENT VARIABLE OVERRIDES
# =============================================================================

def load_env_overrides() -> None:
    """
    Load configuration overrides from environment variables.
    
    Supported Environment Variables:
        GEMINI_MODEL: Override model name
        RATE_LIMIT_RPM: Override requests per minute
        LOG_LEVEL: Override logging level
        ENABLE_SCRAPING: Enable/disable scraping ("true"/"false")
        ENABLE_FACT_CHECKING: Enable/disable fact checking
        PARALLEL_RESEARCH: Enable/disable parallel research
    
    Example:
        export GEMINI_MODEL="gemini-pro"
        export RATE_LIMIT_RPM="20"
        export LOG_LEVEL="DEBUG"
        export ENABLE_SCRAPING="true"
    """
    global MODEL, RATE_LIMIT, RESEARCH, OBSERVABILITY
    
    # Model overrides
    if model_name := os.getenv("GEMINI_MODEL"):
        MODEL = ModelConfig(name=model_name)
    
    # Rate limit overrides
    if rpm := os.getenv("RATE_LIMIT_RPM"):
        try:
            RATE_LIMIT = RateLimitConfig(requests_per_minute=int(rpm))
        except ValueError as e:
            print(f"Warning: Invalid RATE_LIMIT_RPM: {e}")
    
    # Research overrides
    scraping = os.getenv("ENABLE_SCRAPING", "").lower() == "true"
    fact_checking = os.getenv("ENABLE_FACT_CHECKING", "").lower() == "true"
    parallel = os.getenv("PARALLEL_RESEARCH", "").lower() == "true"
    
    if any([os.getenv("ENABLE_SCRAPING"), 
            os.getenv("ENABLE_FACT_CHECKING"), 
            os.getenv("PARALLEL_RESEARCH")]):
        RESEARCH = ResearchConfig(
            enable_scraping=scraping or RESEARCH.enable_scraping,
            enable_fact_checking=fact_checking or RESEARCH.enable_fact_checking,
            parallel_research=parallel or RESEARCH.parallel_research
        )
    
    # Observability overrides
    if log_level := os.getenv("LOG_LEVEL"):
        try:
            OBSERVABILITY = ObservabilityConfig(log_level=log_level.upper())
        except ValueError as e:
            print(f"Warning: Invalid LOG_LEVEL: {e}")


# Load environment overrides on import
load_env_overrides()


# =============================================================================
# VALIDATION
# =============================================================================

def validate_all_configs() -> None:
    """
    Validate all configuration settings.
    
    Raises:
        ValueError: If any configuration is invalid
    
    Example:
        >>> try:
        ...     validate_all_configs()
        ...     print("✓ Configuration valid")
        ... except ValueError as e:
        ...     print(f"✗ Configuration error: {e}")
    """
    configs = [
        ("RateLimitConfig", RATE_LIMIT),
        ("ModelConfig", MODEL),
        ("MemoryConfig", MEMORY),
        ("ResearchConfig", RESEARCH),
        ("ScrapingConfig", SCRAPING),
        ("ObservabilityConfig", OBSERVABILITY)
    ]
    
    for name, config in configs:
        try:
            config.validate()
        except ValueError as e:
            raise ValueError(f"{name} validation failed: {e}")


# Validate on import
try:
    validate_all_configs()
except ValueError as e:
    print(f"⚠️  Configuration Warning: {e}")


# =============================================================================
# CONFIGURATION SUMMARY
# =============================================================================

def print_config_summary() -> None:
    """
    Print a human-readable configuration summary.
    
    Useful for debugging and understanding current settings.
    
    Example:
        >>> print_config_summary()
        
        ╔══════════════════════════════════════════════╗
        ║   Smart Personal Research Concierge Config   ║
        ╚══════════════════════════════════════════════╝
        
        📊 Rate Limiting:
          • Requests/min: 10
          • Max retries: 3
        ...
    """
    print("\n" + "="*60)
    print("SMART PERSONAL RESEARCH CONCIERGE - CONFIGURATION")
    print("="*60)
    
    print("\n📊 RATE LIMITING:")
    print(f"  • Requests/min: {RATE_LIMIT.requests_per_minute}")
    print(f"  • Max retries: {RATE_LIMIT.max_retries}")
    print(f"  • Backoff factor: {RATE_LIMIT.backoff_factor}x")
    
    print("\n🤖 MODEL:")
    print(f"  • Name: {MODEL.name}")
    print(f"  • Temperature: {MODEL.temperature}")
    print(f"  • Max tokens: {MODEL.max_output_tokens}")
    
    print("\n💾 MEMORY:")
    print(f"  • Long-term file: {MEMORY.long_term_file.name}")
    print(f"  • Query limit: {MEMORY.query_history_limit}")
    print(f"  • Auto-cleanup: {MEMORY.auto_cleanup_enabled}")
    
    print("\n🔍 RESEARCH:")
    print(f"  • Subtopics: {RESEARCH.min_subtopics}-{RESEARCH.max_subtopics}")
    print(f"  • Results/subtopic: {RESEARCH.results_per_subtopic}")
    print(f"  • Parallel: {RESEARCH.parallel_research}")
    print(f"  • Scraping: {RESEARCH.enable_scraping}")
    print(f"  • Fact-checking: {RESEARCH.enable_fact_checking}")
    
    print("\n🌐 SCRAPING:")
    print(f"  • Timeout: {SCRAPING.timeout}s")
    print(f"  • Rate limit delay: {SCRAPING.rate_limit_delay}s")
    print(f"  • Max paragraphs: {SCRAPING.max_paragraphs}")
    
    print("\n📝 OBSERVABILITY:")
    print(f"  • Log level: {OBSERVABILITY.log_level}")
    print(f"  • Metrics enabled: {OBSERVABILITY.enable_metrics}")
    print(f"  • Console output: {OBSERVABILITY.enable_console_output}")
    
    print("\n" + "="*60 + "\n")


# =============================================================================
# PRESET CONFIGURATIONS
# =============================================================================

def get_fast_mode_config() -> dict:
    """Get configuration for fast research mode."""
    return {
        'research': ResearchConfig(
            parallel_research=True,
            enable_scraping=False,
            enable_fact_checking=False
        ),
        'rate_limit': RateLimitConfig(requests_per_minute=15)
    }


def get_quality_mode_config() -> dict:
    """Get configuration for quality research mode."""
    return {
        'research': ResearchConfig(
            parallel_research=False,
            enable_scraping=True,
            enable_fact_checking=True
        ),
        'rate_limit': RateLimitConfig(requests_per_minute=10)
    }


def get_balanced_mode_config() -> dict:
    """Get configuration for balanced research mode (default)."""
    return {
        'research': RESEARCH,
        'rate_limit': RATE_LIMIT
    }


if __name__ == "__main__":
    # Demo/testing code
    print("Configuration Module Demo")
    print_config_summary()
    
    # Test validation
    print("\n🧪 TESTING VALIDATION:")
    try:
        validate_all_configs()
        print("  ✓ All configurations valid")
    except ValueError as e:
        print(f"  ✗ Validation error: {e}")
    
    # Show preset configs
    print("\n⚙️  PRESET CONFIGURATIONS:")
    print("\n  Fast Mode:")
    fast = get_fast_mode_config()
    print(f"    - Parallel: {fast['research'].parallel_research}")
    print(f"    - Scraping: {fast['research'].enable_scraping}")
    print(f"    - Fact-checking: {fast['research'].enable_fact_checking}")
    
    print("\n  Quality Mode:")
    quality = get_quality_mode_config()
    print(f"    - Parallel: {quality['research'].parallel_research}")
    print(f"    - Scraping: {quality['research'].enable_scraping}")
    print(f"    - Fact-checking: {quality['research'].enable_fact_checking}")
    
    print("\n✓ Demo complete!")