"""Shopping Requests Router"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
import uuid
import json
import asyncio
from datetime import datetime

from api.models.request import ShoppingRequest, RequestStatus, ShoppingResult
from api.services.agent_service import AgentService
from api.services.database_service import DatabaseService

router = APIRouter()

# In-memory storage for request status (in production, use Redis or database)
request_store: Dict[str, RequestStatus] = {}

@router.post("/requests", response_model=Dict[str, str])
async def create_shopping_request(
    request: ShoppingRequest,
    background_tasks: BackgroundTasks
):
    """Create a new shopping request"""
    try:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Create initial status
        status = RequestStatus(
            request_id=request_id,
            status="pending",
            progress=0.0,
            current_step="Initializing request",
            result=None,
            error=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Store status
        request_store[request_id] = status
        
        # Process request in background
        background_tasks.add_task(
            process_shopping_request,
            request_id,
            request
        )
        
        return {
            "request_id": request_id,
            "status": "pending",
            "message": "Request created successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create request: {str(e)}"
        )

@router.get("/requests/{request_id}", response_model=RequestStatus)
async def get_request_status(request_id: str):
    """Get request status by ID"""
    if request_id not in request_store:
        raise HTTPException(
            status_code=404,
            detail="Request not found"
        )
    
    return request_store[request_id]

@router.get("/requests/{request_id}/stream")
async def stream_request_status(request_id: str):
    """Stream real-time request status updates"""
    if request_id not in request_store:
        raise HTTPException(
            status_code=404,
            detail="Request not found"
        )
    
    async def generate_status_stream():
        """Generate SSE stream for request status"""
        while True:
            if request_id in request_store:
                status = request_store[request_id]
                data = {
                    "request_id": status.request_id,
                    "status": status.status,
                    "progress": status.progress,
                    "current_step": status.current_step,
                    "updated_at": status.updated_at.isoformat()
                }
                
                yield f"data: {json.dumps(data)}\n\n"
                
                # Stop streaming if request is completed or failed
                if status.status in ["completed", "failed"]:
                    break
                    
            await asyncio.sleep(1)  # Update every second
    
    return StreamingResponse(
        generate_status_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@router.delete("/requests/{request_id}")
async def cancel_request(request_id: str):
    """Cancel a pending or processing request"""
    if request_id not in request_store:
        raise HTTPException(
            status_code=404,
            detail="Request not found"
        )
    
    status = request_store[request_id]
    
    if status.status in ["completed", "failed"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel completed or failed request"
        )
    
    # Update status to cancelled
    status.status = "failed"
    status.error = "Request cancelled by user"
    status.updated_at = datetime.utcnow()
    
    return {"message": "Request cancelled successfully"}

async def process_shopping_request(request_id: str, request: ShoppingRequest):
    """Background task to process shopping request using existing agent system"""
    try:
        # Update status to processing
        status = request_store[request_id]
        status.status = "processing"
        status.progress = 0.1
        status.current_step = "Initializing agent system"
        status.updated_at = datetime.utcnow()
        
        # Initialize agent service
        agent_service = AgentService()
        
        # Update progress
        status.progress = 0.2
        status.current_step = "Processing shopping request"
        status.updated_at = datetime.utcnow()
        
        # Process request using existing agent system
        result = agent_service.process_shopping_request(request_id, request.query)
        
        # Update status to completed
        status.status = "completed"
        status.progress = 1.0
        status.current_step = "Request completed"
        status.result = result
        status.updated_at = datetime.utcnow()
        
    except Exception as e:
        # Update status to failed
        status = request_store[request_id]
        status.status = "failed"
        status.error = str(e)
        status.updated_at = datetime.utcnow()

def update_progress(request_id: str, step: str, progress: float):
    """Update request progress"""
    if request_id in request_store:
        status = request_store[request_id]
        status.current_step = step
        status.progress = progress
        status.updated_at = datetime.utcnow()