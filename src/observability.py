"""
Observability module for tracking agent performance and behavior.

Provides centralized logging, metrics collection, and timing tracking
for all agents in the research pipeline. Saves metrics to JSON for
analysis and debugging.
"""

import logging
import json
import time
import os
from datetime import datetime
from pathlib import Path

class ObservabilityLogger:
    """
    Centralized logging and metrics collection for all agents.
    Tracks timing, success/failure, and collects metrics.
    """
    
    def __init__(self):
        # Setup file logging
        self._setup_logging()
        
        # Metrics storage
        self.metrics = {
            'agent_calls': {},
            'agent_timings': {},
            'errors': [],
            'session_start': datetime.now().isoformat()
        }
        
        # Get project root for metrics file
        project_root = Path(__file__).parent.parent
        self.metrics_file = project_root / 'logs' / 'metrics.json'
        
        # Ensure logs directory exists
        os.makedirs(self.metrics_file.parent, exist_ok=True)
        
        logging.info("ObservabilityLogger initialized")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        # Get project root
        project_root = Path(__file__).parent.parent
        log_file = project_root / 'logs' / 'agent.log'
        
        # Ensure logs directory exists
        os.makedirs(log_file.parent, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            filename=str(log_file),
            filemode='a',
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Also log to console
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
    
    def start_timer(self, agent_name):
        """Start timing an agent operation"""
        logging.info(f"Starting {agent_name}")
        return time.time()
    
    def end_timer(self, agent_name, start_time, success=True, error=None):
        """End timing and record metrics"""
        elapsed = time.time() - start_time
        
        # Log completion
        if success:
            logging.info(f"{agent_name} completed in {elapsed:.2f}s")
        else:
            logging.error(f"{agent_name} failed in {elapsed:.2f}s: {error}")
        
        # Update metrics
        if agent_name not in self.metrics['agent_calls']:
            self.metrics['agent_calls'][agent_name] = {'success': 0, 'failure': 0}
            self.metrics['agent_timings'][agent_name] = []
        
        if success:
            self.metrics['agent_calls'][agent_name]['success'] += 1
        else:
            self.metrics['agent_calls'][agent_name]['failure'] += 1
            self.metrics['errors'].append({
                'agent': agent_name,
                'error': str(error),
                'timestamp': datetime.now().isoformat()
            })
        
        self.metrics['agent_timings'][agent_name].append(elapsed)
    
    def log_event(self, event_type, message, data=None):
        """Log a custom event"""
        log_msg = f"[{event_type}] {message}"
        if data:
            log_msg += f" | Data: {data}"
        logging.info(log_msg)
    
    def save_metrics(self):
        """Save metrics to JSON file"""
        try:
            # Calculate averages
            metrics_summary = {
                'session_start': self.metrics['session_start'],
                'session_end': datetime.now().isoformat(),
                'agent_calls': self.metrics['agent_calls'],
                'agent_timings_avg': {},
                'total_errors': len(self.metrics['errors']),
                'errors': self.metrics['errors'][-10:]  # Last 10 errors
            }
            
            # Calculate average timings
            for agent, timings in self.metrics['agent_timings'].items():
                if timings:
                    metrics_summary['agent_timings_avg'][agent] = {
                        'avg': sum(timings) / len(timings),
                        'min': min(timings),
                        'max': max(timings),
                        'count': len(timings)
                    }
            
            # Append to metrics file
            metrics_history = []
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    try:
                        metrics_history = json.load(f)
                        if not isinstance(metrics_history, list):
                            metrics_history = [metrics_history]
                    except:
                        metrics_history = []
            
            metrics_history.append(metrics_summary)
            
            # Keep only last 50 sessions
            metrics_history = metrics_history[-50:]
            
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics_history, f, indent=2)
            
            logging.info(f"Metrics saved to {self.metrics_file}")
            
        except Exception as e:
            logging.error(f"Failed to save metrics: {e}")
    
    def print_summary(self):
        """Print a summary of metrics"""
        print("\n" + "="*80)
        print("📊 OBSERVABILITY METRICS SUMMARY")
        print("="*80)
        
        print("\n🔧 Agent Calls:")
        for agent, counts in self.metrics['agent_calls'].items():
            total = counts['success'] + counts['failure']
            success_rate = (counts['success'] / total * 100) if total > 0 else 0
            print(f"  • {agent}: {total} calls ({success_rate:.1f}% success)")
        
        print("\n⏱️  Agent Timings (avg):")
        for agent, timings in self.metrics['agent_timings'].items():
            if timings:
                avg = sum(timings) / len(timings)
                print(f"  • {agent}: {avg:.2f}s")
        
        if self.metrics['errors']:
            print(f"\n❌ Errors: {len(self.metrics['errors'])} total")
            for error in self.metrics['errors'][-3:]:  # Last 3 errors
                print(f"  • {error['agent']}: {error['error'][:50]}...")
        else:
            print("\n✅ No errors recorded")
        
        print("\n" + "="*80)


# Global logger instance
_global_logger = None

def get_logger():
    """Get or create global logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = ObservabilityLogger()
    return _global_logger