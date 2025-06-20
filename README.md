# withinFlo - Web Analysis & Test Case Generation

A full-stack application that analyzes websites and generates comprehensive test case documentation using AI.

## 🚀 Quick Start

### Prerequisites
- **Node.js** (v18 or higher)
- **Python** (v3.8 or higher)
- **yarn** or **npm**

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd withinFlo
```

### 2. Backend Setup (Python/FastAPI)
```bash
# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables (create .env file)
# Add your OpenAI API key and other config

# Run the backend server
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup (Next.js/React)
```bash
# Navigate to frontend directory
cd frontend/my-app

# Install Node.js dependencies
yarn install
# or: npm install

# Run the development server
yarn dev
# or: npm run dev
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📦 Dependencies

### Frontend (Next.js)
- **@react-pdf/renderer** - PDF generation
- **@heroicons/react** - Icons
- **react-markdown** - Markdown rendering
- **@tailwindcss/typography** - Styling
- **react-syntax-highlighter** - Code highlighting

### Backend (Python)
- **FastAPI** - Web framework
- **Playwright** - Web scraping
- **OpenAI** - AI integration
- **PyMuPDF** - PDF processing
- **Redis** - Caching
- **MongoDB** - Database

## 🔧 Building for Production

### Frontend
```bash
cd frontend/my-app
yarn build
yarn start
```

### Backend
```bash
# Use uvicorn with production settings
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 🌐 Deployment

The application is ready for deployment on platforms like:
- **Vercel** (Frontend)
- **Railway/Render** (Backend)
- **Docker** (Full stack)

## 📄 Features

- Website crawling and analysis
- AI-powered test case generation
- PDF export functionality
- Real-time progress tracking
- Interactive test case viewer

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `yarn build` & `pip install -r requirements.txt`
5. Submit a pull request
