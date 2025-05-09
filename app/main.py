from fastapi import FastAPI, HTTPException
from .models import JobRequest, JobResponse, JobStatus
from .worker import process_url, jobs_collection
from datetime import datetime
from bson import ObjectId
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="QA Documentation Generator",
             description="AI-powered tool for generating test documentation from website analysis")

@app.post("/jobs", response_model=JobResponse)
async def create_job(request: JobRequest):
    try:
        # Create job document
        job_id = str(ObjectId())
        job_doc = {
            '_id': job_id,
            'url': str(request.url),
            'auth': request.auth.dict() if request.auth else None,
            'status': JobStatus.PENDING,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert job into MongoDB
        jobs_collection.insert_one(job_doc)
        
        # Start processing task
        process_url.delay(job_id, str(request.url), request.auth.dict() if request.auth else None)
        
        return JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=job_doc['created_at'],
            updated_at=job_doc['updated_at']
        )
        
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}/status", response_model=JobResponse)
async def get_job_status(job_id: str):
    try:
        job = jobs_collection.find_one({'_id': job_id})
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        return JobResponse(
            job_id=job_id,
            status=job['status'],
            created_at=job['created_at'],
            updated_at=job['updated_at'],
            result=job.get('result'),
            error=job.get('error')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    try:
        job = jobs_collection.find_one({'_id': job_id})
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        if job['status'] != JobStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Job is not completed")
            
        return job.get('documentation', {})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 