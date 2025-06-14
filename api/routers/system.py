"""System Status and Monitoring Router"""

import os
import sys
import psutil
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from api.services.agent_service import AgentService
from api.models.request import SystemConfigRequest

router = APIRouter()

@router.get("/monitoring", response_model=Dict[str, Any])
async def get_monitoring_status():
    """Get monitoring status - alias for system status"""
    return await get_system_status()

@router.get("/system/status", response_model=Dict[str, Any])
async def get_system_status():
    """Get comprehensive system status"""
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get agent system status
        agent_service = AgentService()
        agent_status = agent_service.get_system_status()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "system": {
                "cpu_usage": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "process_id": os.getpid()
            },
            "agents": agent_status,
            "database": {
                "status": "connected",
                "type": "sqlite"
            },
            "ai_model": {
                "provider": "gemini",
                "status": "available"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system status: {str(e)}"
        )

@router.get("/system/health", response_model=Dict[str, Any])
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "shopping-agent-api",
        "version": "1.0.0"
    }

@router.get("/system/metrics", response_model=Dict[str, Any])
async def get_system_metrics():
    """Get detailed system performance metrics"""
    try:
        # CPU metrics
        cpu_times = psutil.cpu_times()
        cpu_count = psutil.cpu_count()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk metrics
        disk_usage = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        
        # Network metrics
        network_io = psutil.net_io_counters()
        
        # Process metrics
        process = psutil.Process()
        process_memory = process.memory_info()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": {
                "count": cpu_count,
                "percent": psutil.cpu_percent(interval=1),
                "times": {
                    "user": cpu_times.user,
                    "system": cpu_times.system,
                    "idle": cpu_times.idle
                }
            },
            "memory": {
                "virtual": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                },
                "swap": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percent": swap.percent
                },
                "process": {
                    "rss": process_memory.rss,
                    "vms": process_memory.vms
                }
            },
            "disk": {
                "usage": {
                    "total": disk_usage.total,
                    "used": disk_usage.used,
                    "free": disk_usage.free,
                    "percent": (disk_usage.used / disk_usage.total) * 100
                },
                "io": {
                    "read_count": disk_io.read_count if disk_io else 0,
                    "write_count": disk_io.write_count if disk_io else 0,
                    "read_bytes": disk_io.read_bytes if disk_io else 0,
                    "write_bytes": disk_io.write_bytes if disk_io else 0
                }
            },
            "network": {
                "bytes_sent": network_io.bytes_sent,
                "bytes_recv": network_io.bytes_recv,
                "packets_sent": network_io.packets_sent,
                "packets_recv": network_io.packets_recv
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system metrics: {str(e)}"
        )

@router.get("/system/config", response_model=Dict[str, Any])
async def get_system_config():
    """Get system configuration"""
    try:
        agent_service = AgentService()
        config = agent_service.get_system_config()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "config": config,
            "environment": {
                "python_version": sys.version,
                "platform": os.name,
                "working_directory": os.getcwd()
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system config: {str(e)}"
        )

@router.post("/system/config", response_model=Dict[str, Any])
async def update_system_config(config_request: SystemConfigRequest):
    """Update system configuration"""
    try:
        agent_service = AgentService()
        updated_config = agent_service.update_system_config(config_request.config_updates)
        
        return {
            "message": "Configuration updated successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "updated_config": updated_config
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update system config: {str(e)}"
        )

@router.get("/system/logs", response_model=Dict[str, Any])
async def get_system_logs(
    level: str = "INFO",
    limit: int = 100,
    offset: int = 0
):
    """Get system logs"""
    try:
        # This would need to be implemented to read from log files
        # For now, return a placeholder
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "logs": [],
            "level": level,
            "limit": limit,
            "offset": offset,
            "total": 0,
            "message": "Log retrieval not yet implemented"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system logs: {str(e)}"
        )