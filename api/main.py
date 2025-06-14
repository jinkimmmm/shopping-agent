"""FastAPI Main Application"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime

# Import routers
from api.routers import requests, history, system
from api.config import get_settings

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Shopping Agent API",
    description="AI-powered shopping assistant API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001"
    ],  # React dev server and API docs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(requests.router, prefix="/api/v1", tags=["requests"])
app.include_router(history.router, prefix="/api/v1", tags=["history"])
app.include_router(system.router, prefix="/api/v1", tags=["system"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Shopping Agent API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/api/docs"
    }

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "shopping-agent-api"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "type": "internal_server_error",
            "title": "Internal Server Error",
            "status": 500,
            "detail": str(exc),
            "instance": str(request.url)
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )