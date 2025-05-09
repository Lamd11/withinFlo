import requests
import time
import json
from datetime import datetime
import asyncio
import aiohttp

async def test_qa_generator(url: str, auth=None):
    """
    Test the QA Documentation Generator with a given URL.
    
    Args:
        url (str): The URL to analyze
        auth (dict, optional): Authentication configuration
    """
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        # Submit job
        print(f"\nSubmitting URL for analysis: {url}")
        async with session.post(
            f"{base_url}/jobs",
            json={"url": url, "auth": auth}
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
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        markdown_file = f"qa_documentation_{timestamp}.md"
        json_file = f"qa_documentation_{timestamp}.json"
        
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
    
    # Run the async function
    asyncio.run(test_qa_generator(test_url, auth)) 