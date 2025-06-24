from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import logging
import asyncio
import io
import os
from datetime import datetime
from bson import ObjectId

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="QA Documentation Generator",
             description="AI-powered tool for generating test documentation from website analysis")

# Add CORS middleware - Configure for your Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins for now - you should restrict this to your Vercel domain
        "https://*.vercel.app",
        "http://localhost:3000",  # For local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "QA Documentation Generator API", "status": "running", "docs": "/docs"}

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {"status": "healthy", "message": "QA Documentation Generator API is running"}

# Import other modules after FastAPI setup to handle potential import errors gracefully
try:
    from app.models import JobRequest, JobResponse, JobStatus, AnalysisResult
    from app.worker import process_url, jobs_collection
    from app.generator import DocumentationGenerator
    logger.info("All modules imported successfully")
except ImportError as e:
    logger.error(f"Import error: {e}")
    # For now, we'll just log the error but allow the app to start
    # This allows the health check to work even if some dependencies are missing

@app.post("/jobs", response_model=JobResponse)
async def create_job(request: JobRequest):
    try:
        # Create job document
        job_id = str(ObjectId())
        job_doc = {
            '_id': job_id,
            'url': str(request.url),
            'auth': request.auth.dict() if request.auth else None,
            'website_context': request.website_context,
            'status': JobStatus.PENDING,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert job into MongoDB
        jobs_collection.insert_one(job_doc)
        
        # Start processing task
        process_url.delay(job_id, str(request.url), 
                          request.auth.dict() if request.auth else None,
                          request.website_context)
        
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
            error=job.get('error'),
            progress=job.get('progress')
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

@app.get("/jobs/{job_id}/results/pdf")
async def get_job_results_pdf(job_id: str):
    try:
        job = jobs_collection.find_one({'_id': job_id})
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        if job['status'] != JobStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Job is not completed or has failed")
            
        analysis_result_data = job.get('result')
        if not analysis_result_data:
            raise HTTPException(status_code=404, detail="Analysis result data not found for this job")

        analysis_result = AnalysisResult(**analysis_result_data)

        doc_generator = DocumentationGenerator()
        pdf_bytes = doc_generator.generate_pdf(analysis_result)

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={ "Content-Disposition": f"attachment; filename=qa_documentation_{job_id}.pdf" }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job PDF result: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 