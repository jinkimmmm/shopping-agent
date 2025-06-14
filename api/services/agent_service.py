"""Agent Service for integrating with existing ShoppingAgentApp"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
import logging

# Import the existing agent
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from shopping_agent import ShoppingAgentApp
except ImportError:
    # Fallback for development
    class ShoppingAgentApp:
        def __init__(self):
            pass
        
        def run(self, query: str) -> Dict[str, Any]:
            # Mock implementation for development
            return {
                "products": [],
                "analysis": {},
                "recommendations": [],
                "execution_time": 0.0,
                "total_products_found": 0,
                "search_query": query
            }

from models.request import RequestStatus, ShoppingResult

logger = logging.getLogger(__name__)

class AgentService:
    """Service for managing shopping agent requests"""
    
    def __init__(self):
        self.agent = ShoppingAgentApp()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.active_requests: Dict[str, RequestStatus] = {}
        self.system_config = {
            "max_concurrent_requests": 10,
            "request_timeout": 300,
            "enable_logging": True,
            "log_level": "INFO"
        }
        
    async def create_request(self, query: str, context: Optional[Dict[str, Any]] = None, 
                           user_id: Optional[str] = None, session_id: Optional[str] = None) -> str:
        """Create a new shopping request"""
        request_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        status = RequestStatus(
            request_id=request_id,
            status="pending",
            progress=0.0,
            current_step="Initializing request",
            result=None,
            error=None,
            created_at=now,
            updated_at=now
        )
        
        self.active_requests[request_id] = status
        
        # Start processing in background
        asyncio.create_task(self._process_request(request_id, query, context, user_id, session_id))
        
        return request_id
    
    def process_shopping_request(self, request_id: str, query: str) -> Dict[str, Any]:
        """Process a shopping request (synchronous method for background execution)"""
        try:
            logger.info(f"Processing shopping request {request_id}")
            
            # Update status to processing
            if request_id in self.active_requests:
                self.active_requests[request_id].status = "processing"
                self.active_requests[request_id].updated_at = datetime.utcnow()
            
            # Run the shopping agent
            result = self.agent.run(query)
            
            # Update status to completed
            if request_id in self.active_requests:
                self.active_requests[request_id].status = "completed"
                self.active_requests[request_id].result = ShoppingResult(**result)
                self.active_requests[request_id].updated_at = datetime.utcnow()
            
            logger.info(f"Completed shopping request {request_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing request {request_id}: {str(e)}")
            
            # Update status to failed
            if request_id in self.active_requests:
                self.active_requests[request_id].status = "failed"
                self.active_requests[request_id].error = str(e)
                self.active_requests[request_id].updated_at = datetime.utcnow()
            
            raise e
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        import psutil
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get active requests info
        active_count = len([r for r in self.active_requests.values() if r.status in ["pending", "processing"]])
        completed_count = len([r for r in self.active_requests.values() if r.status == "completed"])
        failed_count = len([r for r in self.active_requests.values() if r.status == "failed"])
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": (disk.used / disk.total) * 100,
                "disk_free_gb": disk.free / (1024**3)
            },
            "requests": {
                "active": active_count,
                "completed": completed_count,
                "failed": failed_count,
                "total": len(self.active_requests)
            },
            "agent": {
                "status": "running",
                "version": "1.0.0"
            }
        }
    
    def get_system_config(self) -> Dict[str, Any]:
        """Get current system configuration"""
        return self.system_config.copy()
    
    def update_system_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update system configuration"""
        # Validate and update configuration
        valid_keys = set(self.system_config.keys())
        updates = {k: v for k, v in config.items() if k in valid_keys}
        
        self.system_config.update(updates)
        
        logger.info(f"Updated system configuration: {updates}")
        return self.system_config.copy()
    
    async def get_request_status(self, request_id: str) -> Optional[RequestStatus]:
        """Get the status of a request"""
        return self.active_requests.get(request_id)
    
    async def cancel_request(self, request_id: str) -> bool:
        """Cancel a request"""
        if request_id in self.active_requests:
            status = self.active_requests[request_id]
            if status.status in ["pending", "processing"]:
                status.status = "failed"
                status.error = "Request cancelled by user"
                status.updated_at = datetime.utcnow()
                return True
        return False
    
    async def stream_request_status(self, request_id: str) -> AsyncGenerator[RequestStatus, None]:
        """Stream real-time updates for a request"""
        while request_id in self.active_requests:
            status = self.active_requests[request_id]
            yield status
            
            if status.status in ["completed", "failed"]:
                break
                
            await asyncio.sleep(1)  # Poll every second
    
    async def _process_request(self, request_id: str, query: str, 
                             context: Optional[Dict[str, Any]] = None,
                             user_id: Optional[str] = None, 
                             session_id: Optional[str] = None):
        """Process a shopping request in background"""
        try:
            status = self.active_requests[request_id]
            
            # Update status to processing
            status.status = "processing"
            status.current_step = "Starting agent"
            status.progress = 0.1
            status.updated_at = datetime.utcnow()
            
            # Simulate progress updates
            await self._update_progress(request_id, 0.2, "Analyzing query")
            await asyncio.sleep(1)
            
            await self._update_progress(request_id, 0.4, "Searching products")
            await asyncio.sleep(1)
            
            await self._update_progress(request_id, 0.6, "Processing results")
            
            # Run the actual agent in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor, 
                self._run_agent_sync, 
                query, 
                context
            )
            
            await self._update_progress(request_id, 0.8, "Finalizing results")
            await asyncio.sleep(0.5)
            
            # Complete the request
            status.status = "completed"
            status.progress = 1.0
            status.current_step = "Completed"
            status.result = result
            status.updated_at = datetime.utcnow()
            
            logger.info(f"Request {request_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error processing request {request_id}: {str(e)}")
            status = self.active_requests[request_id]
            status.status = "failed"
            status.error = str(e)
            status.updated_at = datetime.utcnow()
    
    def _run_agent_sync(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run the agent synchronously"""
        try:
            # Call the existing agent
            result = self.agent.run(query)
            
            # Ensure the result matches our expected format
            if not isinstance(result, dict):
                result = {
                    "products": [],
                    "analysis": {},
                    "recommendations": [],
                    "execution_time": 0.0,
                    "total_products_found": 0,
                    "search_query": query
                }
            
            # Add any missing fields
            result.setdefault("products", [])
            result.setdefault("analysis", {})
            result.setdefault("recommendations", [])
            result.setdefault("execution_time", 0.0)
            result.setdefault("total_products_found", len(result.get("products", [])))
            result.setdefault("search_query", query)
            
            return result
            
        except Exception as e:
            logger.error(f"Agent execution failed: {str(e)}")
            # Return a default result structure
            return {
                "products": [],
                "analysis": {"error": str(e)},
                "recommendations": ["Please try a different search query"],
                "execution_time": 0.0,
                "total_products_found": 0,
                "search_query": query
            }
    
    async def _update_progress(self, request_id: str, progress: float, step: str):
        """Update request progress"""
        if request_id in self.active_requests:
            status = self.active_requests[request_id]
            status.progress = progress
            status.current_step = step
            status.updated_at = datetime.utcnow()
    
    def cleanup_completed_requests(self, max_age_hours: int = 24):
        """Clean up old completed requests"""
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        
        to_remove = []
        for request_id, status in self.active_requests.items():
            if (status.status in ["completed", "failed"] and 
                status.updated_at.timestamp() < cutoff_time):
                to_remove.append(request_id)
        
        for request_id in to_remove:
            del self.active_requests[request_id]
        
        logger.info(f"Cleaned up {len(to_remove)} old requests")

# Global instance
agent_service = AgentService()