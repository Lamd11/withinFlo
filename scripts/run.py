import os
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor
import signal
import time

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def start_fastapi():
    print("Starting FastAPI server...")
    fastapi_process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Run from project root
    )
    return fastapi_process

def start_celery():
    print("Starting Celery worker...")
    celery_process = subprocess.Popen(
        ["celery", "-A", "app.worker", "worker", "--loglevel=info"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Run from project root
    )
    return celery_process

def monitor_process(process, name):
    try:
        for line in process.stdout:
            print(f"[{name}] {line.strip()}")
    except Exception as e:
        print(f"Error monitoring {name}: {str(e)}")

def print_usage():
    print("\nQA Documentation Generator")
    print("=========================")
    print("\nThis script helps you start all necessary components.")
    print("\nPrerequisites:")
    print("  1. Make sure MongoDB is running on localhost:27017")
    print("  2. Make sure Redis is running on localhost:6379")
    print("  3. Set OPENAI_API_KEY in your environment or .env file")
    print("\nCommands:")
    print("  start    - Start the FastAPI server and Celery worker")
    print("  test     - Run the test script to analyze a website")
    print("  help     - Show this help message")
    print("\nExample:")
    print("  python scripts/run.py start")
    print("  python scripts/run.py test")

def signal_handler(sig, frame):
    print("\nShutting down gracefully...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    
    if len(sys.argv) < 2 or sys.argv[1] == "help":
        print_usage()
        sys.exit(0)
        
    command = sys.argv[1]
    
    if command == "start":
        try:
            # Ensure output directories exist
            os.makedirs("output/json", exist_ok=True)
            os.makedirs("output/markdown", exist_ok=True)
            
            # Check for prerequisites
            if not os.getenv("OPENAI_API_KEY"):
                print("WARNING: OPENAI_API_KEY environment variable is not set!")
                print("Please set it before starting the applications.")
                sys.exit(1)
                
            # Start FastAPI and Celery
            fastapi_process = start_fastapi()
            time.sleep(2)  # Give FastAPI time to start
            celery_process = start_celery()
            
            # Monitor output in separate threads
            with ThreadPoolExecutor(max_workers=2) as executor:
                executor.submit(monitor_process, fastapi_process, "FastAPI")
                executor.submit(monitor_process, celery_process, "Celery")
                
            # Wait for processes to complete (they won't unless terminated)
            fastapi_process.wait()
            celery_process.wait()
            
        except KeyboardInterrupt:
            print("\nShutting down...")
            if 'fastapi_process' in locals():
                fastapi_process.terminate()
            if 'celery_process' in locals():
                celery_process.terminate()
            sys.exit(0)
            
    elif command == "test":
        try:
            # Run the test script from current directory
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_qa_generator.py")
            subprocess.run([sys.executable, script_path], check=True)
            
        except Exception as e:
            print(f"Error running test: {str(e)}")
            sys.exit(1)
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1) 