#!/usr/bin/env python
"""Run the API server: python run.py (or: uvicorn app.server:app)."""
import uvicorn

from app.config import settings

if __name__ == "__main__":
    uvicorn.run("app.server:app", host=settings.host, port=settings.port)
