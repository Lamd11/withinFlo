#!/bin/bash

# Exit on any error
set -e

echo "🔄 Starting Celery Worker Service..."

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

echo "✅ Environment variables verified"
echo "🔄 Starting Celery worker..."

# Start the Celery worker
exec celery -A app.worker worker --loglevel=info --concurrency=2 