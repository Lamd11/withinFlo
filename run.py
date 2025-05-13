import os
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor
import signal
import time

def start_fastapi():
    print("Starting FastAPI server...")
    fastapi_process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    return fastapi_process

def start_celery():
    print("Starting Celery worker...")
    celery_process = subprocess.Popen(
        ["celery", "-A", "app.worker", "worker", "--loglevel=info"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
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
    print("  python run.py start")
    print("  python run.py test")

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
            from test_qa_generator import test_qa_generator
            import asyncio
            
            print("Starting test script...")
            # Example usage - directly invoke the test script
            test_url = input("Enter URL to analyze: ")
            
            # Optional: Ask for authentication
            use_auth = input("Does the website require authentication? (y/n): ").lower() == 'y'
            auth = None
            
            if use_auth:
                auth_type = input("Auth type (basic/session): ").lower()
                if auth_type == "basic":
                    username = input("Username: ")
                    password = input("Password: ")
                    auth = {
                        "type": "basic",
                        "username": username,
                        "password": password
                    }
                elif auth_type == "session":
                    token = input("Session token: ")
                    token_type = input("Token type (cookie/bearer): ").lower()
                    auth = {
                        "type": "session",
                        "token": token,
                        "token_type": token_type
                    }
            
            # Optional: Ask for website context
            use_context = input("Do you want to provide additional context about the website? (y/n): ").lower() == 'y'
            website_context = None
            
            if use_context:
                site_type = input("Website type (e.g., E-commerce, Blog, SaaS Dashboard): ")
                page_description = input("Current page description: ")
                user_goal = input("Main user goal on this page: ")
                
                website_context = {
                    "type": site_type,
                    "current_page_description": page_description,
                    "user_goal_on_page": user_goal
                }
            
            # Run the async function
            asyncio.run(test_qa_generator(test_url, auth, website_context))
            
        except Exception as e:
            print(f"Error running test: {str(e)}")
            sys.exit(1)
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1) 