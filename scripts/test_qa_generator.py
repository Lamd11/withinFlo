import requests
import time
import json
from datetime import datetime
import asyncio
import aiohttp
import os

async def test_qa_generator(url: str, auth=None, website_context=None):
    """
    Test the QA Documentation Generator with a given URL.
    
    Args:
        url (str): The URL to analyze
        auth (dict, optional): Authentication configuration
        website_context (dict, optional): Additional context about the website
    """
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        # Submit job
        print(f"\nSubmitting URL for analysis: {url}")
        request_data = {
            "url": url, 
            "auth": auth
        }
        
        if website_context:
            request_data["website_context"] = website_context
            print(f"With context: {json.dumps(website_context, indent=2)}")
            
        async with session.post(
            f"{base_url}/jobs",
            json=request_data
        ) as response:
            response.raise_for_status()
            job_data = await response.json()
            job_id = job_data["job_id"]
            print(f"Job created with ID: {job_id}")
        
        # Poll for status
        while True:
            async with session.get(f"{base_url}/jobs/{job_id}/status") as response:
                response.raise_for_status()
                status = await response.json()
                
                print(f"\rCurrent status: {status['status']}", end="")
                
                if status['status'] in ['completed', 'failed']:
                    print("\n")
                    break
                    
                await asyncio.sleep(2)
        
        if status['status'] == 'failed':
            print(f"Job failed: {status.get('error', 'Unknown error')}")
            return
        
        # Get results
        print("\nFetching results...")
        async with session.get(f"{base_url}/jobs/{job_id}/results") as response:
            response.raise_for_status()
            results = await response.json()
        
        # Create output directories if they don't exist
        os.makedirs("../output/markdown", exist_ok=True)
        os.makedirs("../output/json", exist_ok=True)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        markdown_file = f"../output/markdown/qa_documentation_{timestamp}.md"
        json_file = f"../output/json/qa_documentation_{timestamp}.json"
        
        with open(markdown_file, "w", encoding="utf-8") as f:
            f.write(results["markdown"])
        
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results["json"], f, indent=2)
        
        print(f"\nDocumentation saved to:")
        print(f"- Markdown: {markdown_file}")
        print(f"- JSON: {json_file}")

if __name__ == "__main__":
    # Example usage
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