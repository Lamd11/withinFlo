from celery import Celery
from typing import Optional
from .crawler import WebsiteCrawler
from .analyzer import TestCaseAnalyzer
from .generator import DocumentationGenerator
from .ai_strategist import AIStrategist
from .element_mapper import ElementMapper
from .models import AnalysisResult, JobStatus, ScanStrategy, PageElementMap, DateTimeEncoder
from datetime import datetime
import os
import logging
from pymongo import MongoClient
import asyncio
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery('qa_doc_generator',
                    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
                    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

# Initialize MongoDB
mongo_client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = mongo_client['qa_doc_generator']
jobs_collection = db['jobs']

@celery_app.task
def process_url(job_id: str, url: str, auth: dict = None, website_context: dict = None, user_prompt: str = None):
    try:
        # Update job status to processing
        jobs_collection.update_one(
            {'_id': job_id},
            {'$set': {
                'status': JobStatus.PROCESSING,
                'updated_at': datetime.utcnow()
            }}
        )

        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Initialize components
        strategist = AIStrategist()
        analyzer = TestCaseAnalyzer()
        generator = DocumentationGenerator()
        element_mapper = ElementMapper()

        # Phase 1: Initial Discovery
        async def initial_discovery():
            async with WebsiteCrawler() as crawler:
                # Get initial website content
                content = await crawler.get_initial_content(url, auth)
                
                # Create comprehensive element map
                page = await crawler.browser.new_page()
                await page.goto(url, wait_until="networkidle")
                element_map = await element_mapper.create_element_map(page)
                await page.close()
                
                return content, element_map

        # Run initial discovery
        logger.info(f"Job {job_id}: Starting Phase 1 - Initial Discovery")
        website_content, element_map = loop.run_until_complete(initial_discovery())
        
        # Update website context with page title if available
        if website_context is None:
            website_context = {}
        if website_content.get('page_title') and 'current_page_description' not in website_context:
            website_context['current_page_description'] = website_content['page_title']

        # Phase 2: Create Informed Scan Strategy
        logger.info(f"Job {job_id}: Creating informed scan strategy with element map")
        scan_strategy_obj: Optional[ScanStrategy] = strategist.develop_scan_strategy(
            user_prompt=user_prompt,
            url=url,
            website_content=website_content,
            element_map=element_map,
            existing_website_context=website_context,
        )

        if not scan_strategy_obj:
            logger.error(f"Job {job_id}: AI Strategist failed to develop a scan strategy.")
            jobs_collection.update_one(
                {'_id': job_id},
                {'$set': {
                    'status': JobStatus.FAILED,
                    'updated_at': datetime.utcnow(),
                    'error': "Failed to generate scan strategy"
                }}
            )
            return

        # Phase 3: Targeted Crawl
        logger.info(f"Job {job_id}: Starting Phase 3 - Targeted Crawl")
        async def targeted_crawl():
            async with WebsiteCrawler() as crawler:
                page_details = await crawler.crawl(url, scan_strategy_obj, auth)
                return page_details

        # Crawl the website with the strategy
        crawl_result = loop.run_until_complete(targeted_crawl())
        loop.close()

        # Process multi-page results
        all_elements = []
        all_test_cases = []
        main_page_title = None

        for page_result in crawl_result['pages']:
            # Add page URL to element context
            for element in page_result['elements']:
                element.page_url = page_result['url']
                element.page_title = page_result['page_title']
                all_elements.append(element)

            # Set main page title from the initial page
            if page_result['url'] == url:
                main_page_title = page_result['page_title']

            # Update website context with current page info
            page_context = website_context.copy() if website_context else {}
            page_context.update({
                'current_page_url': page_result['url'],
                'current_page_title': page_result['page_title'],
                'navigation_depth': page_result['depth'],
                'element_map': element_map.dict()  # Use dict() method which handles datetime
            })

            # Analyze elements for this page
            page_test_cases = analyzer.analyze_elements(page_result['elements'], page_context)
            all_test_cases.extend(page_test_cases)

        logger.info(f"Generated {len(all_test_cases)} test cases across {crawl_result['total_pages_scanned']} pages")

        # Create analysis result
        result = AnalysisResult(
            source_url=url,
            analysis_timestamp=datetime.utcnow(),
            page_title=main_page_title or "Multiple Pages Analyzed",
            identified_elements=all_elements,
            generated_test_cases=all_test_cases,
            website_context={
                **website_context,
                'total_pages_scanned': crawl_result['total_pages_scanned'],
                'scanned_urls': list(crawl_result.get('scanned_urls', [])),
                'element_map': element_map.dict()  # Use dict() method which handles datetime
            }
        )

        # Generate documentation
        documentation = generator.generate_documentation(result)

        # Convert result to dict and ensure all datetime objects are serialized
        result_dict = json.loads(json.dumps(result.dict(), cls=DateTimeEncoder))
        element_map_dict = json.loads(json.dumps(element_map.dict(), cls=DateTimeEncoder))

        # Update job with results
        jobs_collection.update_one(
            {'_id': job_id},
            {'$set': {
                'status': JobStatus.COMPLETED,
                'updated_at': datetime.utcnow().isoformat(),  # Convert to ISO string
                'result': result_dict,
                'documentation': documentation,
                'element_map': element_map_dict
            }}
        )

        return job_id

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")
        # Update job with error
        jobs_collection.update_one(
            {'_id': job_id},
            {'$set': {
                'status': JobStatus.FAILED,
                'updated_at': datetime.utcnow().isoformat(),  # Convert to ISO string
                'error': str(e)
            }}
        )
        raise 