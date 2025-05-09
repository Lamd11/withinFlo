# AI-Powered QA Documentation Generator

An intelligent tool that automatically generates comprehensive test documentation from website analysis.

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install
```

4. Create a `.env` file with your configuration:
```bash
OPENAI_API_KEY=your_openai_api_key
MONGODB_URI=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379
```

5. Start Redis (if running locally):
```bash
# On Windows, download and run Redis from https://github.com/microsoftarchive/redis/releases
# On Linux/Mac:
redis-server
```

6. Start MongoDB (if running locally):
```bash
# On Windows, download and install MongoDB from https://www.mongodb.com/try/download/community
# On Linux/Mac:
mongod
```

7. Start the Celery worker:
```bash
celery -A app.worker worker --loglevel=info
```

8. Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

## Usage

### API Endpoints

1. Submit a URL for analysis:
```bash
curl -X POST "http://localhost:8000/jobs" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com", "auth": null}'
```

2. Check job status:
```bash
curl "http://localhost:8000/jobs/{job_id}/status"
```

3. Get results:
```bash
curl "http://localhost:8000/jobs/{job_id}/results"
```

### Example Python Script

```python
import requests

# Submit a URL for analysis
response = requests.post(
    "http://localhost:8000/jobs",
    json={"url": "https://example.com"}
)
job_id = response.json()["job_id"]

# Check status
status = requests.get(f"http://localhost:8000/jobs/{job_id}/status").json()

# Get results when complete
if status["status"] == "completed":
    results = requests.get(f"http://localhost:8000/jobs/{job_id}/results").json()
    print(results)
```

## Project Structure

```
.
├── app/
│   ├── main.py              # FastAPI application
│   ├── worker.py            # Celery worker
│   ├── crawler.py           # Website crawler
│   ├── analyzer.py          # LLM analysis
│   ├── generator.py         # Documentation generator
│   └── models.py            # Pydantic models
├── templates/               # Jinja2 templates
├── requirements.txt         # Python dependencies
└── README.md               # This file
``` 