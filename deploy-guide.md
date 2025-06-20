# Deployment Checklist

## 1. MongoDB Atlas Setup
- [ ] Create free M0 cluster
- [ ] Create database user with Atlas admin privileges  
- [ ] Allow access from anywhere (0.0.0.0/0)
- [ ] Copy connection string

## 2. Redis Cloud Setup  
- [ ] Create free 30MB database
- [ ] Copy endpoint and password
- [ ] Format as redis://default:password@endpoint:port

## 3. Vercel Deployment (Frontend)
- [ ] Connect GitHub repository
- [ ] Set root directory to "frontend/my-app"
- [ ] Add environment variables:
  - MONGODB_URI
  - REDIS_URL
  - OPENAI_API_KEY
  - NEXT_PUBLIC_API_URL

## 4. Railway Deployment (Backend)
- [ ] Connect GitHub repository
- [ ] Add environment variables:
  - MONGODB_URI
  - REDIS_URL
  - OPENAI_API_KEY
  - PORT=8000

## 5. Final Steps
- [ ] Update NEXT_PUBLIC_API_URL in Vercel with Railway URL
- [ ] Test the deployed application
- [ ] Monitor logs for any issues

## URLs to Keep
- Frontend: https://your-app.vercel.app
- Backend: https://your-app.railway.app
- MongoDB: Atlas Dashboard
- Redis: Redis Cloud Dashboard
