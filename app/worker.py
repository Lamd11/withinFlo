from celery import Celery
from .crawler import WebsiteCrawler
from .analyzer import TestCaseAnalyzer
from .generator import DocumentationGenerator
from .models import AnalysisResult, JobStatus, JobProgress
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
def process_url(job_id: str, url: str, auth: dict = None, website_context: dict = None):
    try:
        # Initialize progress tracking
        progress = JobProgress()
        
        def update_progress(log_message: str = None, phase_progress: float = None):
            if log_message:
                progress.logs.append(f"[{datetime.utcnow().isoformat()}] {log_message}")
            
            if phase_progress is not None:
                progress.phase_progress = phase_progress
                
            jobs_collection.update_one(
                {'_id': job_id},
                {'$set': {
                    'status': progress.current_phase,
                    'progress': progress.dict(),
                    'updated_at': datetime.utcnow()
                }}
            )

        # Update initial status with 0% progress
        progress.current_phase = JobStatus.PENDING
        update_progress("Initializing analysis...", 0)

        # Create instances of required components
        analyzer = TestCaseAnalyzer()
        generator = DocumentationGenerator()

        # Create and set event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            # Run async operations
            async def process_website(website_context):
                # Update to crawling phase with 0% progress
                progress.current_phase = JobStatus.CRAWLING
                update_progress("Starting website crawl...", 0)
                
                # Crawl the website
                async with WebsiteCrawler() as crawler:
                    # Update progress to show we're setting up the crawler
                    update_progress("Setting up crawler...", 20)
                    
                    # Start the crawl
                    update_progress("Crawling website...", 40)
                    crawl_result = await crawler.crawl(url, auth)
                    elements = crawl_result['elements']
                    page_title = crawl_result['page_title']

                    # Update progress to show we've found elements
                    update_progress(f"Found {len(elements)} elements to analyze", 100)
                    progress.total_elements = len(elements)

                # Update website context with page title if available
                if website_context is None:
                    website_context = {}
                
                if page_title and 'current_page_description' not in website_context:
                    website_context['current_page_description'] = page_title

                # Switch to analyzing phase
                progress.current_phase = JobStatus.ANALYZING
                update_progress("Starting element analysis...", 0)

                # Define progress callback
                async def progress_callback(completed: int, total: int):
                    progress.processed_elements = completed
                    phase_progress = int((completed / total) * 100)
                    update_progress(f"Analyzed {completed}/{total} elements", phase_progress)

                # Process elements concurrently using analyzer's semaphore
                test_cases = await analyzer.analyze_elements(elements, website_context, progress_callback)
                
                # Update progress
                progress.processed_elements = len(elements)
                progress.generated_test_cases = len(test_cases)
                update_progress(f"Completed analysis of {len(elements)} elements", 100)

                return elements, test_cases, page_title

            # Run everything in the event loop
            elements, test_cases, page_title = loop.run_until_complete(process_website(website_context))

            # Switch to generating phase
            progress.current_phase = JobStatus.GENERATING
            update_progress("Generating documentation...", 0)

            # Create analysis result
            result = AnalysisResult(
                source_url=url,
                analysis_timestamp=datetime.utcnow(),
                page_title=page_title,
                identified_elements=elements,
                generated_test_cases=test_cases,
                website_context=website_context
            )

            # Generate documentation with progress updates
            update_progress("Formatting documentation...", 50)
            documentation = generator.generate_documentation(result)
            update_progress("Documentation generated successfully", 100)

            # Update job with results and complete
            progress.current_phase = JobStatus.COMPLETED
            jobs_collection.update_one(
                {'_id': job_id},
                {'$set': {
                    'status': JobStatus.COMPLETED,
                    'progress': progress.dict(),
                    'updated_at': datetime.utcnow(),
                    'result': result.dict(),
                    'documentation': documentation
                }}
            )

            return job_id

        finally:
            # Clean up the event loop
            try:
                if loop.is_running():
                    loop.stop()
                if not loop.is_closed():
                    loop.close()
            except Exception as e:
                logger.warning(f"Error cleaning up event loop: {str(e)}")

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")
        # Update job with error
        progress.current_phase = JobStatus.FAILED
        jobs_collection.update_one(
            {'_id': job_id},
            {'$set': {
                'status': JobStatus.FAILED,
                'progress': progress.dict(),
                'updated_at': datetime.utcnow(),
                'error': str(e)
            }}
        )
        raise 