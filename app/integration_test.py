import asyncio
import logging
from typing import Dict, Any
from app.ai_strategist import AIStrategist
from app.crawler import WebsiteCrawler
from app.models import ScanStrategy
import json
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_website_crawl(url: str, prompt: str) -> Dict[str, Any]:
    """
    Test function that combines AIStrategist and WebsiteCrawler to analyze a website.
    
    Args:
        url (str): The URL of the website to analyze
        prompt (str): The user's prompt describing what to look for
        
    Returns:
        Dict containing the test results
    """
    try:
        # First, get the scan strategy from AIStrategist
        logger.info(f"Generating scan strategy for prompt: {prompt}")
        strategist = AIStrategist()
        strategy = strategist.develop_scan_strategy(prompt, url)
        
        if not strategy:
            logger.error("Failed to generate scan strategy")
            return {"error": "Failed to generate scan strategy"}
            
        logger.info("Generated strategy:")
        logger.info(f"Focus areas: {strategy.focus_areas}")
        logger.info(f"Number of target elements: {len(strategy.target_elements_description)}")
        
        # Then use the WebsiteCrawler to execute the strategy
        logger.info(f"Starting crawl of {url}")
        async with WebsiteCrawler() as crawler:
            results = await crawler.crawl(url, strategy)
            
            if not results:
                logger.error("Crawler returned no results")
                return {"error": "Crawler returned no results"}
            
            # Process and format the results
            elements_by_type = {}
            for element in results['elements']:
                if element.element_type not in elements_by_type:
                    elements_by_type[element.element_type] = []
                elements_by_type[element.element_type].append(element)
            
            # Create summary statistics
            summary = {
                "url": url,
                "page_title": results['page_title'],
                "total_elements_found": len(results['elements']),
                "elements_by_type": {
                    etype: len(elements) 
                    for etype, elements in elements_by_type.items()
                },
                "strategy_focus_areas": strategy.focus_areas,
                "strategy_success_rate": len(results['elements']) / len(strategy.target_elements_description)
            }
            
            return {
                "summary": summary,
                "full_results": results,
                "strategy": strategy.model_dump()
            }
            
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        return {"error": str(e)}

def print_test_results(results: Dict[str, Any]):
    """Helper function to print test results in a readable format"""
    if "error" in results:
        print(f"\n❌ Test Failed: {results['error']}")
        return
        
    summary = results["summary"]
    print("\n=== Test Results ===")
    print(f"\nWebsite: {summary['url']}")
    print(f"Page Title: {summary['page_title']}")
    print(f"\nStrategy Focus Areas: {', '.join(summary['strategy_focus_areas'])}")
    print(f"Strategy Success Rate: {summary['strategy_success_rate']*100:.1f}%")
    
    print("\nElements Found:")
    for element_type, count in summary['elements_by_type'].items():
        print(f"  {element_type}: {count}")
    
    print(f"\nTotal Elements: {summary['total_elements_found']}")
    
    # Print detailed element information
    print("\n=== Detailed Element Information ===")
    elements_by_type = {}
    for element in results['full_results']['elements']:
        if element.element_type not in elements_by_type:
            elements_by_type[element.element_type] = []
        elements_by_type[element.element_type].append(element)
        
    for element_type, elements in elements_by_type.items():
        print(f"\n{element_type.upper()} Elements:")
        for element in elements:
            print(f"  - ID: {element.element_id}")
            print(f"    Selector: {element.selector}")
            if element.visible_text:
                print(f"    Text: {element.visible_text[:50]}...")
            print(f"    Attributes: {element.attributes}")
            print()

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Test parameters
    TEST_CASES = [
        {
            "url": "https://github.com",
            "prompt": "Check the navigation menu and all forms on the page, including their input fields and submit buttons"
        },
        {
            "url": "https://example.com",
            "prompt": "Analyze the page structure, including headers, main content areas, and any interactive elements"
        }
    ]
    
    async def run_tests():
        for test_case in TEST_CASES:
            print(f"\n{'='*50}")
            print(f"Testing {test_case['url']}")
            print(f"Prompt: {test_case['prompt']}")
            print('='*50)
            
            results = await test_website_crawl(test_case['url'], test_case['prompt'])
            print_test_results(results)
            
            # Save results to file for later analysis
            filename = f"test_results_{test_case['url'].replace('https://', '').replace('/', '_')}.json"
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nResults saved to {filename}")
    
    # Run the tests
    asyncio.run(run_tests()) 