"""
Integrated Spatial Robot Controller - Entry Point

This is the main entry point for the server application.
All functionality is organized in the 'server' package.

Usage:
    python server.py
    or
    uvicorn server:app --host 0.0.0.0 --port 8080 --reload
"""
from server import app
import os

if __name__ == "__main__":
    print("Initializing Integrated Spatial Robot Controller Server...")
    print(f"Current Agent Mode : {os.getenv("LLM_INPUT_MODE")}")
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)