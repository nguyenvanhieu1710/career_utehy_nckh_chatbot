#!/usr/bin/env python3
"""
Development runner for Chatbot Service
"""
import uvicorn
import os
import sys
from dotenv import load_dotenv
from app.core.config import settings

def main():
    """Run the development server"""
    
    load_dotenv()
    
    print("🚀 Starting Chatbot Service in Development Mode")
    print(f"📍 Service will be available at: http://localhost:{settings.PORT}")
    print(f"📖 API docs at: http://localhost:{settings.PORT}/docs")
    print(f"🔍 Health check: http://localhost:{settings.PORT}/health")
    print("\n" + "="*50 + "\n")
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=settings.PORT,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down Chatbot Service")
        sys.exit(0)

if __name__ == "__main__":
    main()