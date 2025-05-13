# AI-Powered QA Documentation Generator

An intelligent tool that automatically generates comprehensive test documentation by analyzing websites. It uses AI to identify UI elements and generate relevant test cases with detailed steps.

## Features

- **Website Crawling**: Automatically navigate to and analyze websites
- **UI Element Identification**: Detect interactive elements like buttons, forms, links
- **AI-Powered Test Case Generation**: Create comprehensive test cases using OpenAI's GPT models
- **Multiple Output Formats**: Generate documentation in both Markdown and JSON formats
- **Context-Aware Analysis**: Provide additional context to improve test case relevance
- **Authentication Support**: Handle basic HTTP and session-based authentication

## Requirements

- Python 3.9+
- MongoDB
- Redis
- OpenAI API Key

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/qa-documentation-generator.git
   cd qa-documentation-generator
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```
   playwright install chromium
   ```

5. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Running the Application

The application consists of three main components:
- FastAPI server: Provides the API for submitting jobs and retrieving results
- Celery worker: Processes the jobs in the background
- MongoDB: Stores job data and results
- Redis: Used for job queueing

### Start MongoDB and Redis

Make sure MongoDB and Redis are running on your system:

- **MongoDB**: Default URL is `mongodb://localhost:27017/`
- **Redis**: Default URL is `redis://localhost:6379/0`

You can use Docker to run these services if you don't have them installed locally:

```bash
docker run -d -p 27017:27017 --name qa-mongo mongo
docker run -d -p 6379:6379 --name qa-redis redis
```

### Running the Application

Use the provided run script to start all components:

```bash
python run.py start
```

This will start both the FastAPI server and Celery worker with appropriate logging.

### Testing the Application

To test the application with a website:

```bash
python run.py test
```

This will prompt you for:
1. A URL to analyze
2. Optional authentication details if the site requires it
3. Optional context information about the website to improve test case generation

You can also run the test script directly:

```bash
python test_qa_generator.py
```

## API Endpoints

- **POST /jobs**: Submit a new URL for analysis
  ```json
  {
    "url": "https://example.com",
    "auth": {
      "type": "basic",
      "username": "user",
      "password": "pass"
    },
    "website_context": {
      "type": "E-commerce",
      "current_page_description": "Product Detail Page",
      "user_goal_on_page": "Add product to cart and checkout"
    }
  }
  ```

- **GET /jobs/{job_id}/status**: Check the status of a job
- **GET /jobs/{job_id}/results**: Get the results of a completed job

## Customizing the Analysis

You can provide website context information to improve the relevance of generated test cases:

- **type**: Type of website (e.g., "E-commerce", "Blog", "SaaS Dashboard")
- **current_page_description**: Description of the current page (e.g., "Product Detail Page", "User Dashboard")
- **user_goal_on_page**: What users typically aim to achieve on this page (e.g., "Complete purchase", "Find information")

## Example Output

The tool generates two types of output:

1. **Markdown**: Human-readable documentation with test cases and UI element details
2. **JSON**: Structured data for integration with test management systems

Both formats include:
- Test case IDs, titles, and types
- Detailed test steps with actions and expected results
- UI element selectors and properties
- Context information used for analysis

## License

[MIT License](LICENSE) 