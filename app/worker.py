from celery import Celery
from .crawler import WebsiteCrawler
from .analyzer import TestCaseAnalyzer
from .generator import DocumentationGenerator
from .ai_strategist import AIStrategist
from .models import AnalysisResult, JobStatus
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

        # Create ScanStrategy to send to analyzer afterwards

        strategist = AIStrategist()
        strategist.develop_scan_strategy

        # Initialize components
        analyzer = TestCaseAnalyzer()
        generator = DocumentationGenerator()

        # Run async crawl
        async def crawl_website():
            async with WebsiteCrawler() as crawler:
                page_details = await crawler.crawl(url, auth)
                return page_details

        # Crawl the website
        crawl_result = loop.run_until_complete(crawl_website())
        elements = crawl_result['elements']
        page_title = crawl_result['page_title']
        loop.close()

        # Update website context with page title if available
        if website_context is None:
            website_context = {}
        
        if page_title and 'current_page_description' not in website_context:
            website_context['current_page_description'] = page_title
            
        logger.info(f"Processing {len(elements)} elements with context: {website_context}")

        # Analyze elements and generate test cases
        test_cases = analyzer.analyze_elements(elements, website_context)
        logger.info(f"Generated {len(test_cases)} test cases")

        # Create analysis result
        result = AnalysisResult(
            source_url=url,
            analysis_timestamp=datetime.utcnow(),
            page_title=page_title,
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