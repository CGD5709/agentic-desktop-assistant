"""
Backward-compatibility alias for the Reasoning Engine server.
The primary application entry point has moved to main.py following Layered Architecture.
"""
import uvicorn
from main import app  # noqa: F401

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
