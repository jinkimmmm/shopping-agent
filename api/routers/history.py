"""History Management Router"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from api.models.request import (
    Conversation, Message, ConversationResponse, 
    MessageResponse, SearchRequest, ConversationAnalytics
)
from api.services.database_service import DatabaseService

router = APIRouter()

@router.get("/conversations", response_model=Dict[str, Any])
async def get_conversations(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    user_id: Optional[str] = Query(None, description="Filter by user ID")
):
    """Get paginated list of conversations"""
    try:
        db_service = DatabaseService()
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get conversations
        conversations = db_service.get_conversations(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        # Get total count for pagination
        total_count = db_service.get_conversations_count(user_id=user_id)
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "conversations": conversations,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": limit,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve conversations: {str(e)}"
        )

@router.get("/conversations/{conversation_id}", response_model=Dict[str, Any])
async def get_conversation_detail(
    conversation_id: int
):
    """Get detailed conversation with all messages"""
    try:
        db_service = DatabaseService()
        
        # Check if conversation exists
        conversation = db_service.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get conversation history
        history = db_service.get_conversation_history(conversation_id)
        
        return {
            "conversation": conversation,
            "messages": history,
            "total_messages": len(history)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve conversation: {str(e)}"
        )

@router.post("/conversations/search", response_model=Dict[str, Any])
async def search_conversations(
    search_request: SearchRequest
):
    """Search conversations by keyword"""
    try:
        db_service = DatabaseService()
        
        # Perform search
        results = db_service.search_conversations(search_request)
        
        return {
            "results": results,
            "total": len(results),
            "keyword": search_request.keyword,
            "filters": search_request.filters
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/analytics/stats", response_model=Dict[str, Any])
async def get_analytics_stats(
    conversation_id: Optional[int] = Query(None, description="Filter by conversation ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze")
):
    """Get usage statistics and analytics"""
    try:
        db_service = DatabaseService()
        
        # Calculate date range
        date_from = datetime.utcnow() - timedelta(days=days)
        
        # Get analytics data
        analytics = db_service.get_analytics(
            conversation_id=conversation_id,
            days=days
        )
        
        return {
            "analytics": analytics,
            "period": {
                "days": days,
                "from": date_from.isoformat(),
                "to": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analytics: {str(e)}"
        )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int
):
    """Delete a conversation and all its messages"""
    try:
        db_service = DatabaseService()
        
        # Check if conversation exists
        conversation = db_service.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Delete conversation
        success = db_service.delete_conversation(conversation_id)
        
        if success:
            return {
                "message": "Conversation deleted successfully",
                "conversation_id": conversation_id
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail="Failed to delete conversation"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete conversation: {str(e)}"
        )

@router.post("/conversations/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: int
):
    """Archive a conversation"""
    try:
        db_service = DatabaseService()
        
        # Check if conversation exists
        conversation = db_service.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Archive conversation (update status)
        success = db_service.update_conversation_status(
            conversation_id, 
            status="archived"
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to archive conversation"
            )
        
        return {"message": "Conversation archived successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to archive conversation: {str(e)}"
        )