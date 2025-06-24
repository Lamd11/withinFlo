# Railway Deployment Guide

## Overview
This guide will help you deploy your FastAPI backend to Railway so your Vercel frontend can communicate with it.

## Prerequisites
1. Railway account ([railway.app](https://railway.app))
2. MongoDB database (MongoDB Atlas recommended)
3. Redis instance (Railway Redis add-on or external)
4. OpenAI API key

## Deployment Steps

### 1. Connect Repository to Railway
1. Go to [railway.app](https://railway.app) and sign in
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect your GitHub account and select this repository

### 2. Set Environment Variables
In your Railway project dashboard, go to Variables and set:

```
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/qa_doc_generator
REDIS_URL=redis://default:password@host:port
OPENAI_API_KEY=sk-your-openai-api-key-here
```

**Important Notes:**
- `PORT` is automatically set by Railway, don't set it manually
- Make sure your MongoDB allows connections from Railway's IPs (0.0.0.0/0 for testing)

### 3. Add Railway Redis (Optional)
If you don't have an external Redis:
1. In your Railway project, click "New Service"
2. Select "Database" → "Add Redis"
3. Copy the connection URL to your `REDIS_URL` environment variable

### 4. Deploy
Railway will automatically deploy using the `Dockerfile`. The deployment process:
1. Builds the Docker image
2. Installs Python dependencies
3. Installs Playwright browsers
4. Starts the server

### 5. Get Your API URL
After deployment, Railway will provide a URL like:
`https://your-app-name.railway.app`

### 6. Update Frontend CORS (Important!)
Update your Vercel frontend to use the Railway API URL instead of localhost.

In your frontend code, replace:
```javascript
const API_URL = 'http://localhost:8000'
```

With:
```javascript
const API_URL = 'https://your-app-name.railway.app'
```

## API Endpoints
Your deployed API will have these endpoints:
- `GET /` - Root endpoint
- `GET /docs` - FastAPI documentation
- `POST /jobs` - Create analysis job
- `GET /jobs/{job_id}/status` - Get job status
- `GET /jobs/{job_id}/results` - Get job results
- `GET /jobs/{job_id}/results/pdf` - Download PDF

## Celery Workers
**Note:** This current deployment runs the FastAPI web server only. For background job processing, you'll need to deploy a separate Celery worker service or use Railway's job queues.

To add a Celery worker:
1. Create a new service in your Railway project
2. Use the same repository but override the start command to: `celery -A app.worker worker --loglevel=info`

## Troubleshooting

### Build Failures
- Check Railway logs in the deployment tab
- Ensure all environment variables are set
- Verify `requirements.txt` is valid

### Runtime Errors
- Check application logs for error details
- Verify MongoDB connection string
- Ensure Redis is accessible
- Check OpenAI API key validity

### Connection Issues
- Check if the app is starting correctly
- Verify all environment variables are set

## Monitoring
- Use Railway's built-in metrics and logs
- Monitor the root `/` endpoint
- Check MongoDB and Redis connection status

## Security Notes
1. Restrict CORS origins to your actual Vercel domain in production
2. Use environment variables for all secrets
3. Enable MongoDB authentication
4. Use strong Redis passwords 