# Deployment Guide - Free Tier Setup

## Overview
This guide will help you deploy your application using completely free services:
- **Frontend**: Vercel (Free tier)
- **Backend**: Render (Free tier) 
- **Database**: MongoDB Atlas (Free tier - 512MB)
- **Cache**: Redis Cloud (Free tier - 30MB)

**Total Monthly Cost: $0**

## Prerequisites
- GitHub account
- Vercel account
- Render account
- MongoDB Atlas account
- Redis Cloud account

## Step 1: Database Setup

### MongoDB Atlas
1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create free account and new cluster (M0 Sandbox - FREE)
3. Create database user: Database Access → Add New Database User
4. Allow network access: Network Access → Add IP Address → Allow Access from Anywhere (0.0.0.0/0)
5. Get connection string: Clusters → Connect → Connect your application
6. Save as: `mongodb+srv://username:password@cluster.mongodb.net/withinflo?retryWrites=true&w=majority`

### Redis Cloud
1. Go to [Redis Cloud](https://redis.com/try-free/)
2. Create free account and new database (30MB FREE)
3. Get connection details from database dashboard
4. Save as: `redis://default:password@endpoint:port`

## Step 2: Backend Deployment (Render)

1. **Prepare Repository**
   - Ensure `render.yaml` is in your root directory
   - Ensure `requirements.txt` has all dependencies

2. **Deploy to Render**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Select your repository and branch (main)
   - Render will automatically detect the `render.yaml` configuration

3. **Set Environment Variables**
   ```
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/withinflo?retryWrites=true&w=majority
   REDIS_URL=redis://default:password@endpoint:port
   OPENAI_API_KEY=sk-your-openai-api-key
   ENVIRONMENT=production
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)
   - Note your backend URL: `https://your-app-name.onrender.com`

## Step 3: Frontend Deployment (Vercel)

1. **Set Environment Variables in Vercel**
   ```
   NEXT_PUBLIC_API_URL=https://your-app-name.onrender.com
   NODE_ENV=production
   ```

2. **Deploy**
   - Push to GitHub main branch
   - Vercel will automatically deploy
   - Your app will be available at: `https://your-app-name.vercel.app`

## Step 4: Testing

1. Visit your Vercel app URL
2. Test the URL analysis functionality
3. Check that results are being saved to MongoDB
4. Verify PDF generation works

## Important Notes

### Render Free Tier Limitations
- **Sleep Policy**: Service sleeps after 15 minutes of inactivity
- **Cold Start**: Takes 30-60 seconds to wake up from sleep
- **Monthly Limit**: 750 hours/month (enough for full-time usage)

### Alternative Free Options

If Render doesn't work for you, consider:

1. **Fly.io** (Very generous free tier)
2. **PythonAnywhere** (Python-focused)
3. **Convert to Vercel Serverless** (Same platform as frontend)

## Troubleshooting

### Backend Won't Start
- Check Render logs for Python/dependency errors
- Ensure all environment variables are set
- Verify `requirements.txt` includes all dependencies

### Frontend Can't Connect to Backend
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check CORS settings in FastAPI backend
- Test backend URL directly in browser

### Database Connection Issues
- Verify MongoDB connection string format
- Check IP whitelist includes 0.0.0.0/0
- Ensure database user has read/write permissions

## Performance Optimization

To minimize cold starts on Render:
1. Use a uptime monitoring service (like UptimeRobot - free) to ping your backend every 14 minutes
2. This keeps the service awake during active hours
3. Set up monitoring only during your expected usage hours

## Cost Monitoring

All services have usage dashboards:
- **Render**: Monitor build minutes and bandwidth
- **Vercel**: Monitor function executions and bandwidth  
- **MongoDB Atlas**: Monitor storage and operations
- **Redis**: Monitor memory usage

Stay within free tier limits to maintain $0/month cost.
