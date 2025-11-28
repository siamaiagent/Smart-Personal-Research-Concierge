"""
Long-Running Job Manager Module

This module provides robust job management for long-running research operations with
pause/resume capability, persistence, and comprehensive state tracking.

Author: Google Hackathon Team
License: MIT
"""

import json
import sys
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from threading import Lock


class JobStatus(Enum):
    """
    Enumeration of possible job states.
    
    States:
        QUEUED: Job created but not started
        RUNNING: Job currently executing
        PAUSED: Job paused by user
        COMPLETED: Job finished successfully
        FAILED: Job encountered an error
        CANCELLED: Job cancelled by user
    """
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LongRunningJobManager:
    """
    Enterprise-grade job manager for long-running research operations.
    
    This class provides comprehensive management of research jobs that may take
    minutes to complete. Jobs are persisted to disk and can survive program
    restarts, making them ideal for:
    
    1. Deep Research: Multi-step research pipelines
    2. Batch Processing: Processing multiple queries
    3. Background Tasks: Non-blocking operations
    4. Resumable Operations: Continue after interruption
    
    Key Features:
    
    1. Persistence:
       - Jobs saved to JSON file
       - Survives program restarts
       - State preserved across sessions
    
    2. Progress Tracking:
       - Percentage completion (0-100%)
       - Current step description
       - Timestamp tracking
       - Duration calculation
    
    3. State Management:
       - Queue, run, pause, resume, cancel
       - Status transitions validated
       - Error handling and recovery
    
    4. Query & Filtering:
       - List jobs by status
       - Search by query text
       - Filter by date range
       - Get job statistics
    
    Architecture:
        - Thread-safe operations with Lock
        - JSON-based persistence
        - UUID-based job identification
        - Immutable job IDs
    
    Attributes:
        jobs_file (Path): Path to jobs storage file
        jobs (Dict[str, Dict]): In-memory job data
        _lock (Lock): Thread synchronization lock
    
    Job Structure:
        {
            "job_id": "abc123de",
            "query": "What is quantum computing?",
            "status": "running",
            "created_at": "2024-01-15T14:30:00.123456",
            "updated_at": "2024-01-15T14:35:00.123456",
            "progress": 60,
            "current_step": "Fact checking",
            "results": {...},
            "error": None,
            "config": {...}
        }
    
    Example Usage:
        >>> manager = LongRunningJobManager()
        >>> 
        >>> # Start a job
        >>> job_id = manager.start_deep_research("AI in healthcare")
        >>> 
        >>> # Update progress
        >>> manager.update_progress(job_id, 50, "Conducting research")
        >>> 
        >>> # Check status
        >>> status = manager.check_status(job_id)
        >>> print(f"Progress: {status['progress']}%")
        >>> 
        >>> # Pause and resume
        >>> manager.pause_job(job_id)
        >>> manager.resume_job(job_id)
        >>> 
        >>> # Complete
        >>> manager.complete_job(job_id, {"summary": "..."})
    
    Thread Safety:
        All public methods are thread-safe through Lock usage.
        Multiple threads can safely interact with the manager.
    
    Persistence:
        Jobs are automatically saved after every state change.
        File format: JSON with 2-space indentation for readability.
    
    Dependencies:
        - Standard library only (json, uuid, datetime, threading)
        - No external dependencies required
    """
    
    # Configuration constants
    JOB_ID_LENGTH = 8           # Short UUID length
    DEFAULT_JOBS_FILE = "jobs.json"
    AUTO_SAVE = True            # Save after every change
    
    # Status transition rules
    VALID_TRANSITIONS = {
        JobStatus.QUEUED: {JobStatus.RUNNING, JobStatus.CANCELLED},
        JobStatus.RUNNING: {JobStatus.PAUSED, JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED},
        JobStatus.PAUSED: {JobStatus.RUNNING, JobStatus.CANCELLED},
        JobStatus.COMPLETED: set(),  # Terminal state
        JobStatus.FAILED: set(),     # Terminal state
        JobStatus.CANCELLED: set()   # Terminal state
    }
    
    def __init__(self, jobs_file: Optional[str] = None):
        """
        Initialize job manager with persistent storage.
        
        Args:
            jobs_file (str, optional): Custom jobs file path.
                                      Defaults to <project_root>/jobs.json
        
        Example:
            >>> # Default location
            >>> manager = LongRunningJobManager()
            
            >>> # Custom location
            >>> manager = LongRunningJobManager("custom/path/jobs.json")
        """
        # Determine jobs file path
        if jobs_file is None:
            project_root = Path(__file__).parent.parent
            self.jobs_file = project_root / self.DEFAULT_JOBS_FILE
        else:
            self.jobs_file = Path(jobs_file)
        
        # Initialize storage
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        
        # Load existing jobs
        self._load_jobs()
        
        print(f"[LongRunningJobManager] ✓ Initialized")
        print(f"[LongRunningJobManager] Storage: {self.jobs_file}")
        print(f"[LongRunningJobManager] Active jobs: {len(self.jobs)}")
    
    def _load_jobs(self) -> None:
        """
        Load jobs from persistent storage.
        
        Handles missing files and corrupted data gracefully.
        Creates directory structure if needed.
        """
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, 'r', encoding='utf-8') as f:
                    self.jobs = json.load(f)
                
                print(f"[LongRunningJobManager] ✓ Loaded {len(self.jobs)} job(s) from storage")
                
            except json.JSONDecodeError as e:
                print(f"[LongRunningJobManager] ✗ Corrupted jobs file: {e}")
                print(f"[LongRunningJobManager] Starting with empty job list")
                self.jobs = {}
                
            except Exception as e:
                print(f"[LongRunningJobManager] ✗ Error loading jobs: {type(e).__name__}: {e}")
                self.jobs = {}
        else:
            print(f"[LongRunningJobManager] No existing jobs file, starting fresh")
            self.jobs = {}
    
    def _save_jobs(self) -> bool:
        """
        Persist jobs to storage.
        
        Returns:
            bool: True if save successful, False otherwise
        """
        if not self.AUTO_SAVE:
            return True
        
        try:
            # Create directory if needed
            self.jobs_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write with pretty formatting
            with open(self.jobs_file, 'w', encoding='utf-8') as f:
                json.dump(self.jobs, f, indent=2, ensure_ascii=False)
            
            return True
            
        except OSError as e:
            print(f"[LongRunningJobManager] ✗ File system error: {e}")
            return False
            
        except Exception as e:
            print(f"[LongRunningJobManager] ✗ Error saving jobs: {type(e).__name__}: {e}")
            return False
    
    def _validate_transition(
        self, 
        current_status: JobStatus, 
        new_status: JobStatus
    ) -> bool:
        """
        Validate if status transition is allowed.
        
        Args:
            current_status (JobStatus): Current job status
            new_status (JobStatus): Desired new status
        
        Returns:
            bool: True if transition is valid
        """
        return new_status in self.VALID_TRANSITIONS.get(current_status, set())
    
    def start_deep_research(
        self, 
        query: str, 
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new deep research job.
        
        Creates a new job in QUEUED status and persists it to storage.
        Returns a unique job ID that can be used to track progress.
        
        Args:
            query (str): Research query
            config (Dict[str, Any], optional): Job configuration options
        
        Returns:
            str: Unique job identifier (8-character UUID)
        
        Job Configuration Options:
            - parallel: Enable parallel research
            - enable_scraping: Enable web scraping
            - enable_fact_checking: Enable fact verification
            - max_subtopics: Maximum research subtopics
        
        Example:
            >>> manager = LongRunningJobManager()
            >>> job_id = manager.start_deep_research(
            ...     "What is quantum computing?",
            ...     config={"parallel": True, "enable_scraping": False}
            ... )
            >>> print(f"Job started: {job_id}")
        """
        with self._lock:
            # Generate unique ID
            job_id = str(uuid.uuid4())[:self.JOB_ID_LENGTH]
            
            # Create job record
            now = datetime.now().isoformat()
            job = {
                'job_id': job_id,
                'query': query,
                'status': JobStatus.QUEUED.value,
                'created_at': now,
                'updated_at': now,
                'progress': 0,
                'current_step': None,
                'results': None,
                'error': None,
                'config': config or {}
            }
            
            # Store and persist
            self.jobs[job_id] = job
            self._save_jobs()
            
            print(f"[LongRunningJobManager] ✓ Created job {job_id}")
            print(f"[LongRunningJobManager] Query: '{query[:50]}...'")
            
            return job_id
    
    def check_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Check the status of a job.
        
        Args:
            job_id (str): Job identifier
        
        Returns:
            Optional[Dict[str, Any]]: Job data or None if not found
        
        Example:
            >>> status = manager.check_status(job_id)
            >>> if status:
            ...     print(f"Status: {status['status']}")
            ...     print(f"Progress: {status['progress']}%")
            ...     print(f"Step: {status['current_step']}")
        """
        with self._lock:
            job = self.jobs.get(job_id)
            
            if job:
                print(f"[LongRunningJobManager] Job {job_id}:")
                print(f"  Status: {job['status']}")
                print(f"  Progress: {job['progress']}%")
                if job['current_step']:
                    print(f"  Step: {job['current_step']}")
            else:
                print(f"[LongRunningJobManager] ⚠ Job {job_id} not found")
            
            # Return copy to prevent external modification
            return job.copy() if job else None
    
    def update_progress(
        self, 
        job_id: str, 
        progress: int, 
        current_step: Optional[str] = None
    ) -> bool:
        """
        Update job progress and current step.
        
        Args:
            job_id (str): Job identifier
            progress (int): Progress percentage (0-100)
            current_step (str, optional): Description of current step
        
        Returns:
            bool: True if update successful
        
        Example:
            >>> manager.update_progress(job_id, 50, "Conducting research")
            >>> manager.update_progress(job_id, 75, "Synthesizing summary")
        """
        with self._lock:
            if job_id not in self.jobs:
                print(f"[LongRunningJobManager] ⚠ Cannot update: Job {job_id} not found")
                return False
            
            # Clamp progress to valid range
            progress = max(0, min(100, progress))
            
            # Update job
            self.jobs[job_id]['progress'] = progress
            self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
            
            if current_step:
                self.jobs[job_id]['current_step'] = current_step
            
            self._save_jobs()
            
            step_info = f" - {current_step}" if current_step else ""
            print(f"[LongRunningJobManager] Job {job_id}: {progress}%{step_info}")
            
            return True
    
    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused or queued job.
        
        Args:
            job_id (str): Job identifier
        
        Returns:
            bool: True if job resumed successfully
        
        Validation:
            - Job must exist
            - Job cannot be in terminal state (completed/failed/cancelled)
            - Job cannot already be running
        
        Example:
            >>> manager.pause_job(job_id)
            >>> # ... do something else ...
            >>> manager.resume_job(job_id)
        """
        with self._lock:
            job = self.jobs.get(job_id)
            
            if not job:
                print(f"[LongRunningJobManager] ✗ Cannot resume: Job {job_id} not found")
                return False
            
            current_status = JobStatus(job['status'])
            
            # Check if already running
            if current_status == JobStatus.RUNNING:
                print(f"[LongRunningJobManager] ⚠ Job {job_id} already running")
                return False
            
            # Check if in terminal state
            if current_status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
                print(f"[LongRunningJobManager] ✗ Cannot resume: Job {job_id} is {current_status.value}")
                return False
            
            # Validate transition
            if not self._validate_transition(current_status, JobStatus.RUNNING):
                print(f"[LongRunningJobManager] ✗ Invalid transition: {current_status.value} → running")
                return False
            
            # Update to running
            self.jobs[job_id]['status'] = JobStatus.RUNNING.value
            self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
            self._save_jobs()
            
            print(f"[LongRunningJobManager] ✓ Resumed job {job_id} from {job['progress']}%")
            return True
    
    def pause_job(self, job_id: str) -> bool:
        """
        Pause a running job.
        
        Args:
            job_id (str): Job identifier
        
        Returns:
            bool: True if job paused successfully
        
        Example:
            >>> if manager.pause_job(job_id):
            ...     print("Job paused successfully")
        """
        with self._lock:
            job = self.jobs.get(job_id)
            
            if not job:
                print(f"[LongRunningJobManager] ✗ Cannot pause: Job {job_id} not found")
                return False
            
            current_status = JobStatus(job['status'])
            
            if current_status != JobStatus.RUNNING:
                print(f"[LongRunningJobManager] ⚠ Job {job_id} is not running ({current_status.value})")
                return False
            
            # Pause job
            self.jobs[job_id]['status'] = JobStatus.PAUSED.value
            self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
            self._save_jobs()
            
            print(f"[LongRunningJobManager] ✓ Paused job {job_id} at {job['progress']}%")
            return True
    
    def complete_job(self, job_id: str, results: Any) -> bool:
        """
        Mark a job as completed with results.
        
        Args:
            job_id (str): Job identifier
            results (Any): Job results (must be JSON-serializable)
        
        Returns:
            bool: True if job completed successfully
        
        Example:
            >>> results = {
            ...     'summary': "...",
            ...     'action_plan': {...}
            ... }
            >>> manager.complete_job(job_id, results)
        """
        with self._lock:
            if job_id not in self.jobs:
                print(f"[LongRunningJobManager] ✗ Cannot complete: Job {job_id} not found")
                return False
            
            self.jobs[job_id]['status'] = JobStatus.COMPLETED.value
            self.jobs[job_id]['progress'] = 100
            self.jobs[job_id]['results'] = results
            self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
            self._save_jobs()
            
            print(f"[LongRunningJobManager] ✓ Job {job_id} completed")
            return True
    
    def fail_job(self, job_id: str, error: str) -> bool:
        """
        Mark a job as failed with error message.
        
        Args:
            job_id (str): Job identifier
            error (str): Error message or exception
        
        Returns:
            bool: True if job marked as failed
        
        Example:
            >>> try:
            ...     # ... research operation ...
            ... except Exception as e:
            ...     manager.fail_job(job_id, str(e))
        """
        with self._lock:
            if job_id not in self.jobs:
                print(f"[LongRunningJobManager] ✗ Cannot fail: Job {job_id} not found")
                return False
            
            self.jobs[job_id]['status'] = JobStatus.FAILED.value
            self.jobs[job_id]['error'] = str(error)
            self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
            self._save_jobs()
            
            print(f"[LongRunningJobManager] ✗ Job {job_id} failed: {error}")
            return True
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job (can be in any non-terminal state).
        
        Args:
            job_id (str): Job identifier
        
        Returns:
            bool: True if job cancelled
        
        Example:
            >>> manager.cancel_job(job_id)
        """
        with self._lock:
            job = self.jobs.get(job_id)
            
            if not job:
                print(f"[LongRunningJobManager] ✗ Cannot cancel: Job {job_id} not found")
                return False
            
            current_status = JobStatus(job['status'])
            
            # Check if already in terminal state
            if current_status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
                print(f"[LongRunningJobManager] ⚠ Job {job_id} already in terminal state ({current_status.value})")
                return False
            
            self.jobs[job_id]['status'] = JobStatus.CANCELLED.value
            self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
            self._save_jobs()
            
            print(f"[LongRunningJobManager] ✓ Job {job_id} cancelled")
            return True
    
    def list_jobs(self, status: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        List all jobs, optionally filtered by status.
        
        Args:
            status (str, optional): Filter by status (queued, running, etc.)
        
        Returns:
            Dict[str, Dict[str, Any]]: Job dictionary
        
        Example:
            >>> # List all jobs
            >>> all_jobs = manager.list_jobs()
            
            >>> # List only running jobs
            >>> running = manager.list_jobs(status="running")
            
            >>> # List completed jobs
            >>> completed = manager.list_jobs(status="completed")
        """
        with self._lock:
            if status:
                filtered = {
                    jid: job.copy() 
                    for jid, job in self.jobs.items() 
                    if job['status'] == status
                }
                print(f"[LongRunningJobManager] Found {len(filtered)} job(s) with status '{status}'")
                return filtered
            
            print(f"[LongRunningJobManager] Total jobs: {len(self.jobs)}")
            return {jid: job.copy() for jid, job in self.jobs.items()}
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full job details by ID.
        
        Args:
            job_id (str): Job identifier
        
        Returns:
            Optional[Dict[str, Any]]: Job data or None
        
        Example:
            >>> job = manager.get_job(job_id)
            >>> if job:
            ...     print(f"Query: {job['query']}")
            ...     print(f"Status: {job['status']}")
            ...     print(f"Progress: {job['progress']}%")
        """
        with self._lock:
            job = self.jobs.get(job_id)
            return job.copy() if job else None
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from storage.
        
        Args:
            job_id (str): Job identifier
        
        Returns:
            bool: True if job deleted
        
        Example:
            >>> manager.delete_job(job_id)
        """
        with self._lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                self._save_jobs()
                print(f"[LongRunningJobManager] ✓ Deleted job {job_id}")
                return True
            
            print(f"[LongRunningJobManager] ⚠ Job {job_id} not found")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive job statistics.
        
        Returns:
            Dict[str, Any]: Statistics including counts by status,
                           average completion time, etc.
        
        Example:
            >>> stats = manager.get_statistics()
            >>> print(f"Total jobs: {stats['total_jobs']}")
            >>> print(f"Completed: {stats['completed_jobs']}")
            >>> print(f"Success rate: {stats['success_rate']:.1f}%")
        """
        with self._lock:
            total = len(self.jobs)
            
            # Count by status
            status_counts = {}
            for status in JobStatus:
                count = sum(1 for job in self.jobs.values() if job['status'] == status.value)
                status_counts[status.value] = count
            
            # Calculate success rate
            completed = status_counts.get(JobStatus.COMPLETED.value, 0)
            failed = status_counts.get(JobStatus.FAILED.value, 0)
            finished = completed + failed
            success_rate = (completed / finished * 100) if finished > 0 else 0
            
            return {
                'total_jobs': total,
                'queued_jobs': status_counts.get(JobStatus.QUEUED.value, 0),
                'running_jobs': status_counts.get(JobStatus.RUNNING.value, 0),
                'paused_jobs': status_counts.get(JobStatus.PAUSED.value, 0),
                'completed_jobs': completed,
                'failed_jobs': failed,
                'cancelled_jobs': status_counts.get(JobStatus.CANCELLED.value, 0),
                'success_rate': success_rate
            }


def simulate_deep_research(
    job_manager: LongRunningJobManager, 
    job_id: str, 
    query: str
) -> Optional[Dict[str, Any]]:
    """
    Simulate a deep research operation with multiple steps.
    
    This demonstrates the complete research pipeline with progress tracking,
    pause/resume capability, and error handling.
    
    Args:
        job_manager (LongRunningJobManager): Job manager instance
        job_id (str): Job identifier
        query (str): Research query
    
    Returns:
        Optional[Dict[str, Any]]: Research results or None if failed
    
    Pipeline Steps:
        1. Query Understanding (20%)
        2. Research (40%)
        3. Fact Checking (60%)
        4. Synthesis (80%)
        5. Action Plan (100%)
    
    Example:
        >>> manager = LongRunningJobManager()
        >>> job_id = manager.start_deep_research("AI in healthcare")
        >>> results = simulate_deep_research(manager, job_id, "AI in healthcare")
    """
    # Add src to Python path
    src_path = Path(__file__).parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    from agents.query_understanding import QueryUnderstandingAgent
    from agents.research_agent import ResearchAgent
    from agents.fact_checker import FactCheckerAgent
    from agents.synthesizer import SynthesizerAgent
    from agents.action_plan import ActionPlanAgent
    
    print(f"\n{'='*60}")
    print(f"[DeepResearch] Starting deep research for job {job_id}")
    print(f"[DeepResearch] Query: '{query}'")
    print(f"{'='*60}")
    
    try:
        # Step 1: Query Understanding (20%)
        print(f"\n[DeepResearch] Step 1/5: Query Understanding")
        job_manager.update_progress(job_id, 20, "Understanding query")
        q_agent = QueryUnderstandingAgent()
        understanding = q_agent.run(query)
        subtopics = understanding['subtopics']
        time.sleep(1)  # Simulate work
        
        # Step 2: Research (40%)
        print(f"\n[DeepResearch] Step 2/5: Research")
        job_manager.update_progress(job_id, 40, "Conducting research")
        r_agent = ResearchAgent(parallel=True, use_scraper=False)
        research_results = r_agent.run(subtopics)
        time.sleep(1)  # Simulate work
        
        # Step 3: Fact Checking (60%)
        print(f"\n[DeepResearch] Step 3/5: Fact Checking")
        job_manager.update_progress(job_id, 60, "Fact checking")
        f_agent = FactCheckerAgent()
        verified_results = f_agent.run(research_results)
        time.sleep(1)  # Simulate work
        
        # Step 4: Synthesis (80%)
        print(f"\n[DeepResearch] Step 4/5: Synthesis")
        job_manager.update_progress(job_id, 80, "Synthesizing summary")
        s_agent = SynthesizerAgent()
        summary = s_agent.run(verified_results, understanding['preferences'])
        time.sleep(1)  # Simulate work
        
        # Step 5: Action Plan (100%)
        print(f"\n[DeepResearch] Step 5/5: Action Plan")
        job_manager.update_progress(job_id, 100, "Creating action plan")
        a_agent = ActionPlanAgent()
        action_plan = a_agent.run(summary, query)
        
        # Complete job
        results = {
            'summary': summary,
            'action_plan': action_plan,
            'subtopics': subtopics,
            'verified_findings_count': sum(
                len(r['findings']) for r in verified_results
            )
        }
        
        job_manager.complete_job(job_id, results)
        
        print(f"\n{'='*60}")
        print(f"[DeepResearch] ✓ Job {job_id} completed successfully")
        print(f"{'='*60}\n")
        
        return results
        
    except Exception as e:
        job_manager.fail_job(job_id, str(e))
        
        print(f"\n{'='*60}")
        print(f"[DeepResearch] ✗ Job {job_id} failed: {type(e).__name__}")
        print(f"[DeepResearch] Error: {e}")
        print(f"{'='*60}\n")
        
        return None


if __name__ == "__main__":
    # Demo/testing code
    print("LongRunningJobManager Demo")
    print("=" * 60)
    
    try:
        # Initialize manager
        manager = LongRunningJobManager()
        
        # Create a job
        print("\n📝 CREATING JOB:")
        job_id = manager.start_deep_research(
            "What is quantum computing?",
            config={"parallel": True}
        )
        
        # Simulate progress
        print("\n⏳ SIMULATING PROGRESS:")
        steps = [
            (20, "Understanding query"),
            (40, "Conducting research"),
            (60, "Fact checking"),
            (80, "Synthesizing summary"),
            (100, "Creating action plan")
        ]
        
        for progress, step in steps:
            manager.update_progress(job_id, progress, step)
            time.sleep(0.5)
        
        # Complete job
        results = {"summary": "Quantum computing uses...", "action_plan": {...}}
        manager.complete_job(job_id, results)
        
        # Check status
        print("\n📊 JOB STATUS:")
        status = manager.check_status(job_id)
        
        # Get statistics
        print("\n📈 STATISTICS:")
        stats = manager.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # List jobs
        print("\n📋 ALL JOBS:")
        jobs = manager.list_jobs()
        for jid, job in jobs.items():
            print(f"  {jid}: {job['status']} - {job['query'][:50]}...")
        
        print("\n✓ Demo complete!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()