#!/usr/bin/env python3
"""
Development runner for Chatbot Service
"""
import uvicorn
import os
import sys
from dotenv import load_dotenv

def main():
    """Run the development server"""
    
    load_dotenv()
    
    print("🚀 Starting Chatbot Service in Development Mode")
    print("📍 Service will be available at: http://localhost:8001")
    print("📖 API docs at: http://localhost:8001/docs")
    print("🔍 Health check: http://localhost:8001/health")
    print("\n" + "="*50 + "\n")
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8001,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down Chatbot Service")
        sys.exit(0)

if __name__ == "__main__":
    main()