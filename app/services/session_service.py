from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.activity import ActivitySession
from app.models.user import User
from datetime import datetime, timedelta
import json


class SessionService:
    def __init__(self):
        pass
    
    def get_active_session(self, db: Session, user_id: int) -> Optional[ActivitySession]:
        """Get user's active activity session"""
        return db.query(ActivitySession).filter(
            ActivitySession.user_id == user_id,
            ActivitySession.status.in_(["active", "completed"])
        ).order_by(ActivitySession.created_at.desc()).first()
    
    def create_session_data(self, session: ActivitySession) -> Dict[str, Any]:
        """Create session data for frontend storage"""
        return {
            "session_id": session.id,
            "status": session.status,
            "selected_duration": session.selected_duration,
            "start_time": session.start_time.isoformat() if session.start_time else None,
            "extensions_used": session.extensions_used,
            "max_possible_score": session.max_possible_score,
            "activity": session.generated_activity
        }
    
    def recover_session(self, db: Session, user_id: int, session_data: Dict[str, Any]) -> Optional[ActivitySession]:
        """Recover session from stored data"""
        session_id = session_data.get("session_id")
        if not session_id:
            return None
        
        session = db.query(ActivitySession).filter(
            ActivitySession.id == session_id,
            ActivitySession.user_id == user_id
        ).first()
        
        if not session:
            return None
        
        # Update session with any stored data
        if "start_time" in session_data and session_data["start_time"]:
            try:
                session.start_time = datetime.fromisoformat(session_data["start_time"])
            except ValueError:
                pass
        
        if "extensions_used" in session_data:
            session.extensions_used = session_data["extensions_used"]
        
        if "max_possible_score" in session_data:
            session.max_possible_score = session_data["max_possible_score"]
        
        db.commit()
        return session
    

    
    def can_extend_activity(self, session: ActivitySession) -> bool:
        """Check if activity can be extended"""
        if session.extensions_used >= 2:  # Max 2 extensions
            return False
        
        # Check if we're past the original duration
        if not session.start_time:
            return False
        
        elapsed = datetime.utcnow() - session.start_time
        elapsed_minutes = int(elapsed.total_seconds() / 60)
        
        return elapsed_minutes >= session.selected_duration
    
    def is_activity_complete(self, session: ActivitySession) -> bool:
        """Check if activity time has elapsed"""
        if not session.start_time:
            return False
        
        elapsed = datetime.utcnow() - session.start_time
        elapsed_minutes = int(elapsed.total_seconds() / 60)
        
        total_allowed_time = session.selected_duration + (session.extensions_used * 5)
        return elapsed_minutes >= total_allowed_time
    
    def get_session_summary(self, session: ActivitySession) -> Dict[str, Any]:
        """Get session summary for display"""
        return {
            "id": session.id,
            "title": session.generated_activity.get("title", "Space Activity"),
            "category": session.selected_category,
            "duration": session.selected_duration,
            "materials": session.selected_materials,
            "objectives": session.selected_objectives,
            "status": session.status,
            "extensions_used": session.extensions_used,
            "max_possible_score": session.max_possible_score,
            "start_time": session.start_time.isoformat() if session.start_time else None,
            "actual_duration": session.actual_duration
        } 