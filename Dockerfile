FROM python:3.9-slim

WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libmupdf-dev \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Copy the application
COPY . .

# Make the startup script executable
RUN chmod +x start.sh

# Expose port (Railway will set the PORT environment variable)
EXPOSE $PORT

# Use the startup script
CMD ["./start.sh"] 