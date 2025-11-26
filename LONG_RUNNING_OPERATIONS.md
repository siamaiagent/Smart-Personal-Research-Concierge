# 🔄 Long-Running Operations

This project supports long-running research operations with pause/resume capability.

## Overview

Long-running operations allow you to:
- Start research jobs that run asynchronously
- Pause jobs and resume them later
- Track progress in real-time
- Persist job state to disk (`jobs.json`)

## How It Works

### 1. Start a Deep Research Job
```python
from src.long_running import LongRunningJobManager

job_manager = LongRunningJobManager()
job_id = job_manager.start_deep_research("Your research query here")
print(f"Job started: {job_id}")
```

### 2. Check Job Status
```python
status = job_manager.check_status(job_id)
print(f"Status: {status['status']}")
print(f"Progress: {status['progress']}%")
```

### 3. Resume a Paused Job
```python
job_manager.resume_job(job_id)
# Job continues from where it left off
```

### 4. Get Results
```python
job = job_manager.get_job(job_id)
if job['status'] == 'completed':
    results = job['results']
    print(results['summary'])
```

## Running the Demo
```bash
python demo_long_running.py
```

This will demonstrate:
1. Creating a new job
2. Checking status
3. Running the job through multiple steps
4. Viewing results

## Job States

- **queued**: Job created but not started
- **running**: Job is currently executing
- **paused**: Job paused, can be resumed
- **completed**: Job finished successfully
- **failed**: Job encountered an error

## Progress Tracking

Jobs report progress through 5 steps:
1. **20%** - Understanding query
2. **40%** - Conducting research
3. **60%** - Fact checking
4. **80%** - Synthesizing summary
5. **100%** - Creating action plan

## Job Persistence

All job state is saved to `jobs.json` and persists between program runs.

**View saved jobs:**
```bash
cat jobs.json       # Mac/Linux
type jobs.json      # Windows
```

## Use Cases

- **Deep Research**: Comprehensive research that takes several minutes
- **Batch Processing**: Process multiple queries sequentially
- **Interrupted Work**: Resume work after system restart
- **Background Tasks**: Start jobs and check results later