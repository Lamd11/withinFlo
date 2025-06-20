#!/usr/bin/env python3
"""
Simple test script to verify all imports work for deployment
"""

def test_imports():
    try:
        print("Testing FastAPI import...")
        from fastapi import FastAPI
        print("✅ FastAPI imported successfully")
        
        print("Testing app package import...")
        import app
        print("✅ App package imported successfully")
        
        print("Testing app.main import...")
        from app.main import app
        print("✅ App.main imported successfully")
        
        print("Testing models import...")
        from app.models import JobRequest, JobResponse, JobStatus
        print("✅ Models imported successfully")
        
        print("Testing essential dependencies...")
        import uvicorn
        import pymongo
        import fastapi
        print("✅ Essential dependencies imported successfully")
        
        print("\n🎉 All imports successful! Ready for deployment.")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

if __name__ == "__main__":
    test_imports() 