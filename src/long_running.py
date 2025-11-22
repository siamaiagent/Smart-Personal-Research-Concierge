"""
Long-running operations manager with pause/resume capability.

Manages research jobs that may take minutes to complete. Jobs are
persisted to disk (jobs.json) and can be paused and resumed across
program restarts.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
import time

class LongRunningJobManager:
    """
    Manages long-running research jobs with pause/resume capability.
    Jobs are stored in jobs.json and can be resumed after interruption.
    """
    
    def __init__(self, jobs_file='jobs.json'):
        # Get project root
        project_root = Path(__file__).parent.parent
        self.jobs_file = project_root / jobs_file
        self.jobs = {}
        self._load_jobs()
        print(f"[LongRunningJobManager] Initialized with file: {self.jobs_file}")
    
    def _load_jobs(self):
        """Load jobs from file"""
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, 'r') as f:
                    self.jobs = json.load(f)
                print(f"[LongRunningJobManager] Loaded {len(self.jobs)} jobs from file")
            except Exception as e:
                print(f"[LongRunningJobManager] Error loading jobs: {e}")
                self.jobs = {}
        else:
            print("[LongRunningJobManager] No existing jobs file, starting fresh")
            self.jobs = {}
    
    def _save_jobs(self):
        """Save jobs to file"""
        try:
            with open(self.jobs_file, 'w') as f:
                json.dump(self.jobs, f, indent=2)
            print(f"[LongRunningJobManager] Saved {len(self.jobs)} jobs to file")
        except Exception as e:
            print(f"[LongRunningJobManager] Error saving jobs: {e}")
    
    def start_deep_research(self, query, config=None):
        """
        Start a new deep research job.
        
        Args:
            query: Research query
            config: Optional configuration dict
            
        Returns:
            job_id: Unique identifier for this job
        """
        job_id = str(uuid.uuid4())[:8]  # Short UUID
        
        job = {
            'job_id': job_id,
            'query': query,
            'status': 'queued',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'progress': 0,
            'current_step': None,
            'results': None,
            'error': None,
            'config': config or {}
        }
        
        self.jobs[job_id] = job
        self._save_jobs()
        
        print(f"[LongRunningJobManager] Created job {job_id} for query: {query}")
        return job_id
    
    def check_status(self, job_id):
        """
        Check the status of a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job dict or None if not found
        """
        job = self.jobs.get(job_id)
        if job:
            print(f"[LongRunningJobManager] Job {job_id} status: {job['status']} ({job['progress']}% complete)")
        else:
            print(f"[LongRunningJobManager] Job {job_id} not found")
        return job
    
    def update_progress(self, job_id, progress, current_step=None):
        """Update job progress"""
        if job_id in self.jobs:
            self.jobs[job_id]['progress'] = progress
            self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
            if current_step:
                self.jobs[job_id]['current_step'] = current_step
            self._save_jobs()
            print(f"[LongRunningJobManager] Job {job_id} progress: {progress}% - {current_step}")
    
    def resume_job(self, job_id):
        """
        Resume a paused or queued job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if job can be resumed, False otherwise
        """
        job = self.jobs.get(job_id)
        
        if not job:
            print(f"[LongRunningJobManager] Cannot resume: Job {job_id} not found")
            return False
        
        if job['status'] == 'completed':
            print(f"[LongRunningJobManager] Job {job_id} already completed")
            return False
        
        if job['status'] == 'running':
            print(f"[LongRunningJobManager] Job {job_id} already running")
            return False
        
        # Mark as running
        self.jobs[job_id]['status'] = 'running'
        self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
        self._save_jobs()
        
        print(f"[LongRunningJobManager] Resumed job {job_id} from {job['progress']}%")
        return True
    
    def complete_job(self, job_id, results):
        """Mark a job as completed"""
        if job_id in self.jobs:
            self.jobs[job_id]['status'] = 'completed'
            self.jobs[job_id]['progress'] = 100
            self.jobs[job_id]['results'] = results
            self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
            self._save_jobs()
            print(f"[LongRunningJobManager] Job {job_id} completed")
    
    def fail_job(self, job_id, error):
        """Mark a job as failed"""
        if job_id in self.jobs:
            self.jobs[job_id]['status'] = 'failed'
            self.jobs[job_id]['error'] = str(error)
            self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
            self._save_jobs()
            print(f"[LongRunningJobManager] Job {job_id} failed: {error}")
    
    def pause_job(self, job_id):
        """Pause a running job"""
        if job_id in self.jobs and self.jobs[job_id]['status'] == 'running':
            self.jobs[job_id]['status'] = 'paused'
            self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
            self._save_jobs()
            print(f"[LongRunningJobManager] Job {job_id} paused at {self.jobs[job_id]['progress']}%")
            return True
        return False
    
    def list_jobs(self, status=None):
        """List all jobs, optionally filtered by status"""
        if status:
            filtered = {jid: job for jid, job in self.jobs.items() if job['status'] == status}
            return filtered
        return self.jobs
    
    def get_job(self, job_id):
        """Get full job details"""
        return self.jobs.get(job_id)


def simulate_deep_research(job_manager, job_id, query):
    """
    Simulate a deep research operation with multiple steps.
    This demonstrates pause/resume capability.
    """
    # Add sys path manipulation
    import sys
    from pathlib import Path
    
    # Add src to Python path if not already there
    src_path = Path(__file__).parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    from agents.query_understanding import QueryUnderstandingAgent
    from agents.research_agent import ResearchAgent
    from agents.fact_checker import FactCheckerAgent
    from agents.synthesizer import SynthesizerAgent
    from agents.action_plan import ActionPlanAgent
    
    print(f"\n[DeepResearch] Starting deep research for job {job_id}")
    
    # ... rest of the function stays the same
    
    try:
        # Step 1: Query Understanding (20%)
        job_manager.update_progress(job_id, 20, "Understanding query")
        q_agent = QueryUnderstandingAgent()
        understanding = q_agent.run(query)
        subtopics = understanding['subtopics']
        time.sleep(1)  # Simulate work
        
        # Step 2: Research (40%)
        job_manager.update_progress(job_id, 40, "Conducting research")
        r_agent = ResearchAgent(parallel=True, use_scraper=False)
        research_results = r_agent.run(subtopics)
        time.sleep(1)  # Simulate work
        
        # Step 3: Fact Checking (60%)
        job_manager.update_progress(job_id, 60, "Fact checking")
        f_agent = FactCheckerAgent()
        verified_results = f_agent.run(research_results)
        time.sleep(1)  # Simulate work
        
        # Step 4: Synthesis (80%)
        job_manager.update_progress(job_id, 80, "Synthesizing summary")
        s_agent = SynthesizerAgent()
        summary = s_agent.run(verified_results, understanding['preferences'])
        time.sleep(1)  # Simulate work
        
        # Step 5: Action Plan (100%)
        job_manager.update_progress(job_id, 100, "Creating action plan")
        a_agent = ActionPlanAgent()
        action_plan = a_agent.run(summary, query)
        
        # Complete
        results = {
            'summary': summary,
            'action_plan': action_plan,
            'subtopics': subtopics
        }
        
        job_manager.complete_job(job_id, results)
        print(f"[DeepResearch] Job {job_id} completed successfully")
        return results
        
    except Exception as e:
        job_manager.fail_job(job_id, str(e))
        print(f"[DeepResearch] Job {job_id} failed: {e}")
        return None