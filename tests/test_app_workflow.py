import asyncio
import os
from dotenv import load_dotenv
import logging
from app.ai_strategist import AIStrategist
from app.crawler import WebsiteCrawler
from app.analyzer import TestCaseAnalyzer
from app.generator import DocumentationGenerator
from app.models import AnalysisResult, JobStatus, ScanStrategy
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_full_workflow():
    """
    Test the entire application workflow by:
    1. Using AIStrategist to generate a scan strategy
    2. Using WebsiteCrawler to find elements
    3. Using TestCaseAnalyzer to analyze elements
    4. Using DocumentationGenerator to create documentation
    """
    # Test URL
    url = "https://github.com"
    user_prompt = "Find navigation elements and make test cases for them"

    try:
        # Step 1: Generate scan strategy
        logger.info("Step 1: Generating scan strategy...")
        strategist = AIStrategist()
        strategy = strategist.develop_scan_strategy(
            user_prompt=user_prompt,
            url=url
        )
        
        if not strategy:
            logger.error("Failed to generate scan strategy")
            return
            
        logger.info(f"Generated strategy with {len(strategy.target_elements_description)} target elements")
        logger.info(f"Focus areas: {strategy.focus_areas}")

        # Step 2: Crawl website
        logger.info("\nStep 2: Crawling website...")
        async with WebsiteCrawler() as crawler:
            crawl_results = await crawler.crawl(url, strategy)
            
        if not crawl_results:
            logger.error("Failed to crawl website")
            return
            
        elements = crawl_results['elements']
        page_title = crawl_results['page_title']
        logger.info(f"Found {len(elements)} elements on {url}")
        logger.info(f"Page title: {page_title}")

        # Step 3: Analyze elements
        logger.info("\nStep 3: Analyzing elements...")
        analyzer = TestCaseAnalyzer()
        test_cases = analyzer.analyze_elements(elements)
        logger.info(f"Generated {len(test_cases)} test cases")

        # Step 4: Generate documentation
        logger.info("\nStep 4: Generating documentation...")
        generator = DocumentationGenerator()
        result = AnalysisResult(
            source_url=url,
            page_title=page_title,
            identified_elements=elements,
            generated_test_cases=test_cases,
            website_context={"page_type": "homepage"},
            analysis_timestamp=datetime.utcnow()
        )
        documentation = generator.generate_documentation(result)
        logger.info("Documentation generated successfully")

        # Print summary
        print("\n=== Test Results ===")
        print(f"URL: {url}")
        print(f"Page Title: {page_title}")
        print(f"Elements found: {len(elements)}")
        print(f"Test cases generated: {len(test_cases)}")
        print("\nElement types found:")
        element_types = {}
        for element in elements:
            if element.element_type not in element_types:
                element_types[element.element_type] = 0
            element_types[element.element_type] += 1
        for element_type, count in element_types.items():
            print(f"  {element_type}: {count}")

        return True

    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        raise

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable is not set!")
        print("Please set it before running the test.")
        exit(1)
    
    # Run the test
    print("Starting full workflow test...")
    asyncio.run(test_full_workflow()) 