import os
import time
from src.long_running import LongRunningJobManager, simulate_deep_research

api_key = os.environ.get('GOOGLE_API_KEY')
if not api_key:
    print("❌ ERROR: GOOGLE_API_KEY not set!")
    print("\nPlease run:")
    print("  $env:GOOGLE_API_KEY='your-key-here'  # Windows PowerShell")
    print("  export GOOGLE_API_KEY='your-key-here'  # Mac/Linux")
    exit(1)

print("✅ API Key loaded from environment")

# Initialize job manager
job_manager = LongRunningJobManager()

# Demo query
query = "What are the latest trends in AI automation for businesses?"

print("\n--- SCENARIO 1: Start a Deep Research Job ---")
job_id = job_manager.start_deep_research(query)
print(f"✅ Job created with ID: {job_id}")

# Check initial status
print("\n--- Check Job Status ---")
status = job_manager.check_status(job_id)
print(f"Status: {status['status']}")
print(f"Query: {status['query']}")

print("\n--- SCENARIO 2: Resume and Run Job ---")
print("Resuming job...")
if job_manager.resume_job(job_id):
    print(f"▶️  Job {job_id} is now running")
    
    # Simulate partial execution (pause after some steps)
    print("\n⏳ Simulating research... (this will take ~20 seconds)")
    print("Steps: Query Understanding → Research → Fact Check → Synthesis → Action Plan")
    print()
    
    # Run the deep research simulation
    results = simulate_deep_research(job_manager, job_id, query)
    
    if results:
        print("\n✅ Job completed successfully!")
        
        # Show results summary
        print("\n" + "="*80)
        print("📊 RESULTS")
        print("="*80)
        print(f"\nSummary (first 200 chars):")
        print(results['summary'][:200] + "...")
        
        print(f"\nAction Plan ({len(results['action_plan']['checklist'])} items):")
        for i, item in enumerate(results['action_plan']['checklist'][:3], 1):
            print(f"  {i}. {item}")

print("\n--- SCENARIO 3: Check Final Status ---")
final_status = job_manager.check_status(job_id)
print(f"Final Status: {final_status['status']}")
print(f"Progress: {final_status['progress']}%")

print("\n--- SCENARIO 4: List All Jobs ---")
all_jobs = job_manager.list_jobs()
print(f"Total jobs in system: {len(all_jobs)}")
for jid, job in all_jobs.items():
    print(f"  • {jid}: {job['status']} - {job['query'][:50]}...")

print("\n" + "="*80)
print("✨ Demo Complete! Check 'jobs.json' to see saved job state.")
print("="*80)