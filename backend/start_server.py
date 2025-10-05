#!/usr/bin/env python3
"""
Startup script for the FastAPI RAG application.
"""
import os
import sys
import uvicorn

# Ensure we're in the backend directory and add it to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def main():
    """Start the FastAPI server"""
    print(f"Starting server from directory: {os.getcwd()}")
    print(f"Python path includes: {backend_dir}")
    
    try:
        # Import to test if everything is working
        from app.main import app
        print("✅ Successfully imported FastAPI app")
        
        from app.core.config import settings
        print(f"✅ Configuration loaded - Gemini API configured: {bool(settings.GEMINI_API_KEY)}")
        
        # Start the server
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()