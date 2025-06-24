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
DEFAULT_PORT=8000
PORT="${PORT:-$DEFAULT_PORT}"

echo "✅ Environment variables verified"
echo "🌐 Starting server on port $PORT"

# Start the FastAPI application with explicit port number
exec uvicorn app.main:app --host 0.0.0.0 --port="${PORT}" --workers 1 