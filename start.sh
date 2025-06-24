#!/bin/bash

# Exit on any error
set -e

echo "🚀 Starting QA Documentation Generator API..."

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

# Set default port if not provided
export PORT=${PORT:-8000}

echo "✅ Environment variables verified"
echo "🌐 Starting server on port $PORT"

# Start the FastAPI application
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 