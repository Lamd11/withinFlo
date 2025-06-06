from celery import Celery
from typing import Optional
from .crawler import WebsiteCrawler
from .analyzer import TestCaseAnalyzer
from .generator import DocumentationGenerator
from .ai_strategist import AIStrategist
from .models import AnalysisResult, JobStatus, ScanStrategy
from datetime import datetime
import os
import logging
from pymongo import MongoClient
import asyncio

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
        if not user_prompt:
            logger.warning(f"Job {job_id}: No user prompt provided. This may result in ineffective testing.")
            
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

        # Phase 1: Get comprehensive page map
        logger.info(f"Phase 1: Getting comprehensive page map for {url}")
        async def get_page_map():
            async with WebsiteCrawler() as crawler:
                page_map = await crawler.get_initial_content(url, auth)
                return page_map

        # Get initial page map
        page_map = loop.run_until_complete(get_page_map())
        
        # Update website context with page metadata and user prompt
        if website_context is None:
            website_context = {}
        website_context.update({
            'current_page_description': page_map['page_metadata']['title'],
            'user_prompt': user_prompt  # Add user prompt to context
        })

        # Phase 2: Create informed scan strategy using the page map
        logger.info("Phase 2: Developing informed scan strategy")
        scan_strategy_obj: Optional[ScanStrategy] = strategist.develop_scan_strategy(
            user_prompt=user_prompt,
            url=url,
            page_map=page_map,
            existing_website_context=website_context,
        )

        if not scan_strategy_obj:
            error_msg = "Failed to generate scan strategy"
            if not user_prompt:
                error_msg += " (no user prompt provided)"
            logger.error(f"Job {job_id}: {error_msg}")
            jobs_collection.update_one(
                {'_id': job_id},
                {'$set': {
                    'status': JobStatus.FAILED,
                    'updated_at': datetime.utcnow(),
                    'error': error_msg
                }}
            )
            return

        # Log strategy details
        logger.info(f"Generated strategy with {len(scan_strategy_obj.target_elements_description)} target elements")
        logger.info(f"Focus areas: {scan_strategy_obj.focus_areas}")

        # Phase 3: Execute targeted crawl with informed strategy
        logger.info("Phase 3: Executing targeted crawl with informed strategy")
        async def crawl_website():
            async with WebsiteCrawler() as crawler:
                crawl_result = await crawler.crawl(url, scan_strategy_obj, auth)
                return crawl_result

        # Crawl the website with the informed strategy
        crawl_result = loop.run_until_complete(crawl_website())
        loop.close()

        # Process results
        all_elements = []
        all_test_cases = []
        main_page_title = page_map['page_metadata']['title']

        for page_result in crawl_result['pages']:
            if not page_result.get('error'):
                # Elements are already UIElement objects from the crawler
                elements = page_result['elements']
                
                # Log found elements
                logger.info(f"Found {len(elements)} elements on page: {page_result['url']}")
                
                # Add page context to each element
                for element in elements:
                    element.page_url = page_result['url']
                    element.page_title = page_result['page_title']
                    all_elements.append(element)

                # Update website context with current page info
                page_context = website_context.copy()
                page_context.update({
                    'current_page_url': page_result['url'],
                    'current_page_title': page_result['page_title'],
                    'navigation_depth': page_result['depth']
                })

                # Analyze elements for this page
                page_test_cases = analyzer.analyze_elements(elements, page_context)
                all_test_cases.extend(page_test_cases)

        logger.info(f"Generated {len(all_test_cases)} test cases across {crawl_result['total_pages_scanned']} pages")

        # Create analysis result
        result = AnalysisResult(
            source_url=url,
            analysis_timestamp=datetime.utcnow(),
            page_title=main_page_title,
            identified_elements=all_elements,
            generated_test_cases=all_test_cases,
            website_context={
                **website_context,
                'total_pages_scanned': crawl_result['total_pages_scanned'],
                'scanned_urls': crawl_result['scanned_urls']
            }
        )

        # Generate documentation
        documentation = generator.generate_documentation(result)

        # Update job with results
        jobs_collection.update_one(
            {'_id': job_id},
            {'$set': {
                'status': JobStatus.COMPLETED,
                'updated_at': datetime.utcnow(),
                'result': result.dict(),
                'documentation': documentation,
                'page_map': page_map,  # Store the initial page map for reference
                'scan_strategy': scan_strategy_obj.dict()  # Store the strategy for reference
            }}
        )

        return job_id

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)
        # Update job with error
        jobs_collection.update_one(
            {'_id': job_id},
            {'$set': {
                'status': JobStatus.FAILED,
                'updated_at': datetime.utcnow(),
                'error': str(e)
            }}
        )
        raise 