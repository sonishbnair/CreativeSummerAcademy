from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.scoring import ActivityScore
from app.models.activity import ActivitySession
from app.models.daily_stats import DailyStats
from app.models.parent import Parent
from app.config import settings
from datetime import datetime, date
import bcrypt


class ScoringService:
    def __init__(self):
        pass
    
    def verify_parent_password(self, db: Session, parent_id: int, password: str) -> bool:
        """Verify parent password"""
        parent = db.query(Parent).filter(Parent.id == parent_id).first()
        if not parent:
            return False
        
        return bcrypt.checkpw(password.encode('utf-8'), parent.password_hash.encode('utf-8'))
    
    def score_activity(
        self,
        db: Session,
        session_id: int,
        parent_id: int,
        score: int
    ) -> Dict[str, Any]:
        """Score an activity"""
        session = db.query(ActivitySession).filter(ActivitySession.id == session_id).first()
        if not session:
            return {"success": False, "error": "Activity session not found"}
        
        if session.status != "completed":
            return {"success": False, "error": "Activity not completed yet"}
        
        if score > session.max_possible_score:
            return {"success": False, "error": f"Score cannot exceed {session.max_possible_score}"}
        
        if score < 0:
            return {"success": False, "error": "Score cannot be negative"}
        
        # Create score record
        score_record = ActivityScore(
            session_id=session_id,
            parent_id=parent_id,
            score=score
        )
        
        db.add(score_record)
        
        # Update session status
        session.status = "scored"
        
        # Update daily stats
        self._update_daily_stats(db, session.user_id, score, session.actual_duration or 0)
        
        db.commit()
        
        return {
            "success": True,
            "score": score,
            "max_possible": session.max_possible_score
        }
    
    def _update_daily_stats(self, db: Session, user_id: int, score: int, duration: int):
        """Update daily statistics"""
        today = date.today()
        
        stats = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date == today
        ).first()
        
        if stats:
            stats.activities_completed += 1
            stats.total_points += score
            stats.total_time_minutes += duration
        else:
            stats = DailyStats(
                user_id=user_id,
                date=today,
                activities_completed=1,
                total_points=score,
                total_time_minutes=duration
            )
            db.add(stats)
    
    def get_daily_stats(self, db: Session, user_id: int, target_date: date = None) -> Dict[str, Any]:
        """Get daily statistics for a user"""
        if target_date is None:
            target_date = date.today()
        
        stats = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date == target_date
        ).first()
        
        if stats:
            return {
                "activities_completed": stats.activities_completed,
                "total_points": stats.total_points,
                "total_time_minutes": stats.total_time_minutes,
                "date": stats.date.isoformat()
            }
        else:
            return {
                "activities_completed": 0,
                "total_points": 0,
                "total_time_minutes": 0,
                "date": target_date.isoformat()
            }
    
    def get_user_progress(self, db: Session, user_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Get user progress over the last N days"""
        from datetime import timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)
        
        stats = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date >= start_date,
            DailyStats.date <= end_date
        ).order_by(DailyStats.date).all()
        
        progress = []
        current_date = start_date
        
        while current_date <= end_date:
            day_stats = next((s for s in stats if s.date == current_date), None)
            
            if day_stats:
                progress.append({
                    "date": current_date.isoformat(),
                    "activities_completed": day_stats.activities_completed,
                    "total_points": day_stats.total_points,
                    "total_time_minutes": day_stats.total_time_minutes
                })
            else:
                progress.append({
                    "date": current_date.isoformat(),
                    "activities_completed": 0,
                    "total_points": 0,
                    "total_time_minutes": 0
                })
            
            current_date += timedelta(days=1)
        
        return progress
    
    def can_start_new_activity(self, db: Session, user_id: int) -> bool:
        """Check if user can start a new activity today and has no unscored session"""
        # Check daily limit
        today_stats = self.get_daily_stats(db, user_id)
        if today_stats["activities_completed"] >= settings.max_activities_per_day:
            return False
        # Check for any unscored session
        unscored = db.query(ActivitySession).filter(
            ActivitySession.user_id == user_id,
            ActivitySession.status.in_(["active", "completed"])
        ).first()
        return unscored is None 