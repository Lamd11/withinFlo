#!/bin/bash

# Exit on any error
set -e

echo "🚀 Starting QA Documentation Generator API (Web Server)..."

# Verify required environment variables
if [ -z "$MONGODB_URI" ]; then
    echo "❌ MONGODB_URI environment variable is not set"
    exit 1
fi

if [ -z "$REDIS_URL" ]; then
    echo "❌ REDIS_URL environment variable is not set"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY environment variable is not set"
    exit 1
fi

# Set port (Railway provides PORT env var)
PORT=${PORT:-8000}

echo "✅ Environment variables verified"
echo "🌐 Starting FastAPI server on port $PORT"
echo "ℹ️  Worker service will be deployed separately"

# Start the FastAPI application
exec uvicorn app.main:app --host 0.0.0.0 --port=$PORT --workers 1 