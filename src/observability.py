"""
Observability Module

This module provides comprehensive observability for the research pipeline, including
logging, metrics collection, performance tracking, and analytics.

Author: Google Hackathon Team
License: MIT
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from threading import Lock


class ObservabilityLogger:
    """
    Enterprise-grade observability system for research pipeline monitoring.
    
    This class provides centralized logging, metrics collection, and performance
    tracking for all agents in the research pipeline. It enables:
    
    1. Performance Monitoring:
       - Timing of agent operations
       - Success/failure tracking
       - Average, min, max timings
       - Throughput metrics
    
    2. Error Tracking:
       - Detailed error logging
       - Error categorization
       - Historical error analysis
       - Root cause identification
    
    3. Usage Analytics:
       - Agent call frequency
       - Success rates
       - Popular queries (via integration)
       - System health metrics
    
    4. Persistence:
       - JSON-based metrics storage
       - Historical session tracking
       - Metrics retention (last 50 sessions)
       - Log file rotation
    
    Architecture:
        - Thread-safe operations via Lock
        - Dual logging (file + console)
        - Structured metrics format
        - Automatic directory creation
    
    Attributes:
        metrics (Dict): In-memory metrics storage
        metrics_file (Path): Path to metrics JSON file
        log_file (Path): Path to log file
        _lock (Lock): Thread synchronization
    
    Metrics Structure:
        {
            "session_start": "2024-01-15T14:30:00",
            "session_end": "2024-01-15T14:35:00",
            "agent_calls": {
                "QueryUnderstandingAgent": {"success": 5, "failure": 0}
            },
            "agent_timings_avg": {
                "ResearchAgent": {"avg": 3.2, "min": 2.1, "max": 5.0, "count": 5}
            },
            "total_errors": 2,
            "errors": [...]
        }
    
    Example Usage:
        >>> logger = get_logger()
        >>> 
        >>> # Time an operation
        >>> start = logger.start_timer("MyAgent")
        >>> # ... do work ...
        >>> logger.end_timer("MyAgent", start, success=True)
        >>> 
        >>> # Log custom event
        >>> logger.log_event("RESEARCH", "Started research", {"query": "..."})
        >>> 
        >>> # Save and display metrics
        >>> logger.save_metrics()
        >>> logger.print_summary()
    
    Integration:
        Works seamlessly with all agents via timing decorators
        and explicit logging calls. No agent code changes needed.
    
    Thread Safety:
        All public methods are thread-safe. Multiple threads can
        safely log events and record metrics simultaneously.
    """
    
    # Configuration constants
    METRICS_RETENTION = 50      # Number of sessions to retain
    MAX_ERRORS_DISPLAYED = 10   # Errors shown in summary
    RECENT_ERRORS_SAVED = 10    # Recent errors saved to file
    
    def __init__(
        self,
        log_file: Optional[Path] = None,
        metrics_file: Optional[Path] = None,
        log_level: str = "INFO"
    ):
        """
        Initialize observability logger with configuration.
        
        Args:
            log_file (Path, optional): Custom log file path
            metrics_file (Path, optional): Custom metrics file path
            log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        # Get project root
        project_root = Path(__file__).parent.parent
        
        # Set file paths
        self.log_file = log_file or (project_root / 'logs' / 'agent.log')
        self.metrics_file = metrics_file or (project_root / 'logs' / 'metrics.json')
        
        # Setup logging
        self._setup_logging(log_level)
        
        # Initialize metrics storage
        self.metrics = {
            'agent_calls': {},
            'agent_timings': {},
            'errors': [],
            'events': [],
            'session_start': datetime.now().isoformat(),
            'session_id': self._generate_session_id()
        }
        
        # Thread safety
        self._lock = Lock()
        
        logging.info("="*80)
        logging.info("ObservabilityLogger initialized")
        logging.info(f"Session ID: {self.metrics['session_id']}")
        logging.info(f"Log file: {self.log_file}")
        logging.info(f"Metrics file: {self.metrics_file}")
        logging.info("="*80)
    
    def _generate_session_id(self) -> str:
        """
        Generate unique session identifier.
        
        Returns:
            str: Session ID (timestamp-based)
        """
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _setup_logging(self, log_level: str) -> None:
        """
        Setup dual logging (file + console) with proper formatting.
        
        Args:
            log_level (str): Logging level
        
        Configuration:
            - File logging: Detailed with timestamps
            - Console logging: Simplified format
            - Auto-creates log directory
            - Append mode for files
        """
        # Ensure logs directory exists
        os.makedirs(self.log_file.parent, exist_ok=True)
        
        # Convert log level string to logging constant
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Clear existing handlers to avoid duplicates
        logging.getLogger('').handlers.clear()
        
        # Configure root logger
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler with detailed format
        file_handler = logging.FileHandler(str(self.log_file), mode='a', encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler with simplified format
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        
        # Add handlers to root logger
        root_logger = logging.getLogger('')
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    def start_timer(self, agent_name: str) -> float:
        """
        Start timing an agent operation.
        
        Args:
            agent_name (str): Name of agent being timed
        
        Returns:
            float: Start timestamp for use with end_timer()
        
        Example:
            >>> start = logger.start_timer("ResearchAgent")
            >>> # ... do research ...
            >>> logger.end_timer("ResearchAgent", start)
        """
        logging.info(f"▶️  Starting {agent_name}")
        return time.time()
    
    def end_timer(
        self,
        agent_name: str,
        start_time: float,
        success: bool = True,
        error: Optional[Exception] = None
    ) -> float:
        """
        End timing and record metrics for an agent operation.
        
        Args:
            agent_name (str): Name of agent being timed
            start_time (float): Start timestamp from start_timer()
            success (bool): Whether operation succeeded
            error (Exception, optional): Error if operation failed
        
        Returns:
            float: Elapsed time in seconds
        
        Metrics Recorded:
            - Success/failure count
            - Timing data (for averages)
            - Error details if failed
        
        Example:
            >>> start = logger.start_timer("FactCheckerAgent")
            >>> try:
            ...     # ... fact checking ...
            ...     logger.end_timer("FactCheckerAgent", start, success=True)
            ... except Exception as e:
            ...     logger.end_timer("FactCheckerAgent", start, success=False, error=e)
        """
        elapsed = time.time() - start_time
        
        with self._lock:
            # Log completion
            if success:
                logging.info(f"✅ {agent_name} completed in {elapsed:.2f}s")
            else:
                logging.error(f"❌ {agent_name} failed in {elapsed:.2f}s: {error}")
            
            # Initialize metrics for agent if needed
            if agent_name not in self.metrics['agent_calls']:
                self.metrics['agent_calls'][agent_name] = {'success': 0, 'failure': 0}
                self.metrics['agent_timings'][agent_name] = []
            
            # Update call counts
            if success:
                self.metrics['agent_calls'][agent_name]['success'] += 1
            else:
                self.metrics['agent_calls'][agent_name]['failure'] += 1
                
                # Record error
                self.metrics['errors'].append({
                    'agent': agent_name,
                    'error': str(error),
                    'error_type': type(error).__name__ if error else 'Unknown',
                    'timestamp': datetime.now().isoformat(),
                    'elapsed': elapsed
                })
            
            # Record timing
            self.metrics['agent_timings'][agent_name].append(elapsed)
        
        return elapsed
    
    def log_event(
        self,
        event_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a custom event with optional structured data.
        
        Args:
            event_type (str): Event category (e.g., "SESSION", "RESEARCH", "ERROR")
            message (str): Event description
            data (Dict, optional): Additional structured data
        
        Example:
            >>> logger.log_event("RESEARCH", "Started research on AI", 
            ...                  {"subtopics": 5, "parallel": True})
            >>> logger.log_event("SESSION", "User preferences updated",
            ...                  {"length": "detailed", "format": "paragraph"})
        """
        with self._lock:
            # Create log message
            log_msg = f"[{event_type}] {message}"
            if data:
                log_msg += f" | {json.dumps(data)}"
            
            logging.info(log_msg)
            
            # Store event in metrics
            self.metrics['events'].append({
                'type': event_type,
                'message': message,
                'data': data,
                'timestamp': datetime.now().isoformat()
            })
    
    def save_metrics(self) -> bool:
        """
        Save metrics to JSON file with historical tracking.
        
        Returns:
            bool: True if save successful, False otherwise
        
        Features:
            - Calculates summary statistics
            - Appends to historical data
            - Maintains retention limit
            - Pretty-prints JSON
        
        File Structure:
            List of session metrics, each with:
            - Session start/end times
            - Agent call counts
            - Timing statistics
            - Error summaries
        
        Example:
            >>> logger.save_metrics()
            True
        """
        with self._lock:
            try:
                # Calculate session summary
                metrics_summary = self._calculate_summary()
                
                # Load existing metrics history
                metrics_history = self._load_metrics_history()
                
                # Append current session
                metrics_history.append(metrics_summary)
                
                # Maintain retention limit
                metrics_history = metrics_history[-self.METRICS_RETENTION:]
                
                # Save to file
                with open(self.metrics_file, 'w', encoding='utf-8') as f:
                    json.dump(metrics_history, f, indent=2, ensure_ascii=False)
                
                logging.info(f"✅ Metrics saved to {self.metrics_file}")
                return True
                
            except OSError as e:
                logging.error(f"❌ Failed to save metrics (file system): {e}")
                return False
                
            except Exception as e:
                logging.error(f"❌ Failed to save metrics: {type(e).__name__}: {e}")
                return False
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """
        Calculate metrics summary for current session.
        
        Returns:
            Dict[str, Any]: Summary statistics
        """
        summary = {
            'session_id': self.metrics['session_id'],
            'session_start': self.metrics['session_start'],
            'session_end': datetime.now().isoformat(),
            'agent_calls': self.metrics['agent_calls'].copy(),
            'agent_timings_avg': {},
            'total_errors': len(self.metrics['errors']),
            'errors': self.metrics['errors'][-self.RECENT_ERRORS_SAVED:],
            'total_events': len(self.metrics['events']),
            'event_types': self._count_event_types()
        }
        
        # Calculate timing statistics
        for agent, timings in self.metrics['agent_timings'].items():
            if timings:
                summary['agent_timings_avg'][agent] = {
                    'avg': sum(timings) / len(timings),
                    'min': min(timings),
                    'max': max(timings),
                    'total': sum(timings),
                    'count': len(timings)
                }
        
        # Calculate session duration
        start = datetime.fromisoformat(self.metrics['session_start'])
        end = datetime.now()
        duration = (end - start).total_seconds()
        summary['session_duration_seconds'] = duration
        
        return summary
    
    def _count_event_types(self) -> Dict[str, int]:
        """
        Count events by type.
        
        Returns:
            Dict[str, int]: Event type counts
        """
        counts = {}
        for event in self.metrics['events']:
            event_type = event['type']
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts
    
    def _load_metrics_history(self) -> List[Dict[str, Any]]:
        """
        Load existing metrics history from file.
        
        Returns:
            List[Dict[str, Any]]: Historical metrics or empty list
        """
        if not self.metrics_file.exists():
            return []
        
        try:
            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                
                # Ensure list format
                if not isinstance(history, list):
                    history = [history]
                
                return history
                
        except json.JSONDecodeError:
            logging.warning("⚠️  Corrupted metrics file, starting fresh")
            return []
            
        except Exception as e:
            logging.error(f"⚠️  Error loading metrics history: {e}")
            return []
    
    def print_summary(self) -> None:
        """
        Print comprehensive metrics summary to console.
        
        Displays:
            - Agent call statistics
            - Timing analysis
            - Error summary
            - Event counts
            - Session duration
        
        Format:
            Beautiful formatted output with emojis and box-drawing
            for easy reading and analysis.
        """
        with self._lock:
            print("\n" + "="*80)
            print("📊 OBSERVABILITY METRICS SUMMARY")
            print("="*80)
            
            # Session info
            print(f"\n🔍 Session: {self.metrics['session_id']}")
            start = datetime.fromisoformat(self.metrics['session_start'])
            duration = (datetime.now() - start).total_seconds()
            print(f"⏱️  Duration: {duration:.1f}s ({duration/60:.1f}m)")
            
            # Agent calls
            if self.metrics['agent_calls']:
                print("\n🔧 Agent Calls:")
                for agent, counts in sorted(self.metrics['agent_calls'].items()):
                    total = counts['success'] + counts['failure']
                    success_rate = (counts['success'] / total * 100) if total > 0 else 0
                    status_icon = "✅" if success_rate == 100 else "⚠️" if success_rate >= 50 else "❌"
                    print(f"  {status_icon} {agent}:")
                    print(f"     Calls: {total} ({counts['success']} ✓, {counts['failure']} ✗)")
                    print(f"     Success rate: {success_rate:.1f}%")
            
            # Agent timings
            if self.metrics['agent_timings']:
                print("\n⏱️  Agent Performance:")
                for agent, timings in sorted(self.metrics['agent_timings'].items()):
                    if timings:
                        avg = sum(timings) / len(timings)
                        min_time = min(timings)
                        max_time = max(timings)
                        print(f"  • {agent}:")
                        print(f"     Avg: {avg:.2f}s | Min: {min_time:.2f}s | Max: {max_time:.2f}s")
            
            # Errors
            if self.metrics['errors']:
                print(f"\n❌ Errors: {len(self.metrics['errors'])} total")
                recent_errors = self.metrics['errors'][-3:]  # Last 3
                for i, error in enumerate(recent_errors, 1):
                    print(f"  {i}. [{error['error_type']}] {error['agent']}")
                    print(f"     {error['error'][:70]}...")
                    print(f"     Time: {error['timestamp']}")
            else:
                print("\n✅ No errors recorded")
            
            # Events
            if self.metrics['events']:
                event_counts = self._count_event_types()
                print(f"\n📝 Events: {len(self.metrics['events'])} total")
                for event_type, count in sorted(event_counts.items()):
                    print(f"  • {event_type}: {count}")
            
            print("\n" + "="*80)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for programmatic access.
        
        Returns:
            Dict[str, Any]: Complete statistics including:
                - Session info
                - Agent metrics
                - Error counts
                - Event counts
        
        Example:
            >>> stats = logger.get_statistics()
            >>> print(f"Total errors: {stats['total_errors']}")
            >>> print(f"Success rate: {stats['overall_success_rate']:.1f}%")
        """
        with self._lock:
            # Calculate overall success rate
            total_success = sum(c['success'] for c in self.metrics['agent_calls'].values())
            total_failure = sum(c['failure'] for c in self.metrics['agent_calls'].values())
            total_calls = total_success + total_failure
            success_rate = (total_success / total_calls * 100) if total_calls > 0 else 0
            
            return {
                'session_id': self.metrics['session_id'],
                'session_start': self.metrics['session_start'],
                'total_agent_calls': total_calls,
                'successful_calls': total_success,
                'failed_calls': total_failure,
                'overall_success_rate': success_rate,
                'total_errors': len(self.metrics['errors']),
                'total_events': len(self.metrics['events']),
                'agents_used': list(self.metrics['agent_calls'].keys())
            }
    
    def reset(self) -> None:
        """
        Reset metrics for new session.
        
        Useful for testing or starting fresh tracking.
        Previous metrics should be saved before resetting.
        """
        with self._lock:
            self.metrics = {
                'agent_calls': {},
                'agent_timings': {},
                'errors': [],
                'events': [],
                'session_start': datetime.now().isoformat(),
                'session_id': self._generate_session_id()
            }
            logging.info(f"✅ Metrics reset for new session: {self.metrics['session_id']}")


# Global logger singleton
_global_logger: Optional[ObservabilityLogger] = None
_global_lock = Lock()


def get_logger() -> ObservabilityLogger:
    """
    Get or create global observability logger singleton.
    
    Returns:
        ObservabilityLogger: Global logger instance
    
    Thread Safety:
        Thread-safe initialization using Lock. Multiple threads
        calling this simultaneously will safely get the same instance.
    
    Example:
        >>> logger = get_logger()
        >>> start = logger.start_timer("MyAgent")
        >>> # ... work ...
        >>> logger.end_timer("MyAgent", start)
    """
    global _global_logger
    
    with _global_lock:
        if _global_logger is None:
            _global_logger = ObservabilityLogger()
            logging.info("✅ Global observability logger created")
        
        return _global_logger


def reset_global_logger() -> None:
    """
    Reset global logger singleton.
    
    Creates a new logger instance, useful for testing or
    starting fresh tracking with different configuration.
    
    Example:
        >>> logger1 = get_logger()
        >>> reset_global_logger()
        >>> logger2 = get_logger()
        >>> assert logger1 is not logger2
    """
    global _global_logger
    
    with _global_lock:
        _global_logger = None
        logging.info("✅ Global observability logger reset")


if __name__ == "__main__":
    # Demo/testing code
    print("ObservabilityLogger Demo")
    print("=" * 80)
    
    try:
        # Initialize logger
        logger = ObservabilityLogger()
        
        # Simulate agent operations
        print("\n🧪 SIMULATING AGENT OPERATIONS:")
        
        # Successful operation
        start = logger.start_timer("TestAgent1")
        time.sleep(0.5)
        logger.end_timer("TestAgent1", start, success=True)
        
        # Another successful operation
        start = logger.start_timer("TestAgent2")
        time.sleep(0.3)
        logger.end_timer("TestAgent2", start, success=True)
        
        # Failed operation
        start = logger.start_timer("TestAgent3")
        time.sleep(0.2)
        error = Exception("Simulated error")
        logger.end_timer("TestAgent3", start, success=False, error=error)
        
        # Log custom events
        logger.log_event("TEST", "Demo event 1", {"data": "value"})
        logger.log_event("SESSION", "Demo event 2")
        
        # Print summary
        logger.print_summary()
        
        # Get statistics
        print("\n📈 STATISTICS:")
        stats = logger.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Save metrics
        print("\n💾 SAVING METRICS:")
        if logger.save_metrics():
            print("  ✅ Metrics saved successfully")
        
        print("\n✅ Demo complete!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()