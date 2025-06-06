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

        # First, do an initial crawl to get page structure and content
        async def initial_crawl():
            async with WebsiteCrawler() as crawler:
                # Create a basic strategy for initial content extraction
                basic_strategy = ScanStrategy(
                    focus_areas=["page_content"],
                    target_elements_description=[{"type": "*", "attributes": {}, "purpose": "initial_scan"}]
                )
                page_details = await crawler.crawl(url, basic_strategy, auth)
                return page_details

        # Get initial page data including structured content
        logger.info(f"Job {job_id}: Starting initial crawl to extract page content...")
        initial_crawl_result = loop.run_until_complete(initial_crawl())
        structured_content = initial_crawl_result.get('structured_content', {})
        html_snapshot = initial_crawl_result.get('html_snapshot', '')
        page_title = initial_crawl_result.get('page_title', '')

        # Now create an informed scan strategy using the actual page content
        strategist = AIStrategist()
        logger.info(f"Job {job_id}: Generating informed scan strategy using extracted content...")
        scan_strategy_obj: Optional[ScanStrategy] = strategist.develop_scan_strategy(
            user_prompt=user_prompt,
            url=url,
            structured_content=structured_content,
            page_html_snapshot=html_snapshot,
            existing_website_context=website_context,
        )

        if not scan_strategy_obj:
            logger.error(f"Job {job_id}: AI Strategist failed to develop a scan strategy.")
            # Handle failure: update job to FAILED, store error, and return
            jobs_collection.update_one(
                {'_id': job_id},
                {'$set': {
                    'status': JobStatus.FAILED,
                    'updated_at': datetime.utcnow(),
                    'error': "Failed to generate scan strategy"
                }}
            )
            return

        # Initialize components
        analyzer = TestCaseAnalyzer()
        generator = DocumentationGenerator()

        # Run second crawl with the informed strategy to get targeted elements
        async def targeted_crawl():
            async with WebsiteCrawler() as crawler:
                page_details = await crawler.crawl(url, scan_strategy_obj, auth)
                return page_details

        # Crawl the website with the informed strategy
        logger.info(f"Job {job_id}: Running targeted crawl with informed strategy...")
        crawl_result = loop.run_until_complete(targeted_crawl())
        elements = crawl_result['elements']
        
        # Use page title from either crawl (should be the same)
        final_page_title = crawl_result.get('page_title', page_title)
        loop.close()

        # Update website context with page title if available
        if website_context is None:
            website_context = {}
        
        if final_page_title and 'current_page_description' not in website_context:
            website_context['current_page_description'] = final_page_title
            
        logger.info(f"Job {job_id}: Processing {len(elements)} targeted elements with context: {website_context}")

        # Analyze elements and generate test cases
        test_cases = analyzer.analyze_elements(elements, website_context)
        logger.info(f"Job {job_id}: Generated {len(test_cases)} test cases")

        # Create analysis result
        result = AnalysisResult(
            source_url=url,
            analysis_timestamp=datetime.utcnow(),
            page_title=final_page_title,
            identified_elements=elements,
            generated_test_cases=test_cases,
            website_context=website_context
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
                'documentation': documentation
            }}
        )

        logger.info(f"Job {job_id}: Successfully completed processing")
        return job_id

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")
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