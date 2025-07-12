from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.services.config_service import ConfigService
from app.config import settings
from fastapi.templating import Jinja2Templates
from typing import List
from datetime import date
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
config_service = ConfigService()


@router.get("/config", response_class=HTMLResponse)
async def admin_config(request: Request, db: Session = Depends(get_db)):
    """Admin configuration page"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "parent":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    config = config_service.get_full_config(db)
    
    return templates.TemplateResponse("parent/config.html", {
        "request": request,
        "config": config
    })


@router.post("/config/update")
async def update_config(
    request: Request,
    max_activities_per_day: int = Form(...),
    min_activity_duration: int = Form(...),
    max_activity_duration: int = Form(...),
    extension_penalty: int = Form(...),
    db: Session = Depends(get_db)
):
    """Update system configuration"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "parent":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Update configuration (in a real app, you'd want to persist these)
    # For now, we'll just redirect back
    return RedirectResponse(url="/admin/config", status_code=302)


@router.get("/reports", response_class=HTMLResponse)
async def admin_reports(request: Request, db: Session = Depends(get_db)):
    """Admin reports page"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "parent":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Get all users and their stats
    from app.models.user import User
    from app.models.daily_stats import DailyStats
    
    users = db.query(User).all()
    today = date.today()
    
    user_stats = []
    for user in users:
        stats = db.query(DailyStats).filter(
            DailyStats.user_id == user.id,
            DailyStats.date == today
        ).first()
        
        user_stats.append({
            "user": user,
            "stats": stats or {"activities_completed": 0, "total_points": 0, "total_time_minutes": 0}
        })
    
    return templates.TemplateResponse("parent/reports.html", {
        "request": request,
        "user_stats": user_stats
    })


@router.get("/activities", response_class=HTMLResponse)
async def admin_activities(request: Request, db: Session = Depends(get_db)):
    """Admin activities management page"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "parent":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Get all activity sessions with user info
    from app.models.activity import ActivitySession
    from app.models.user import User
    from app.models.scoring import ActivityScore
    from app.models.parent import Parent
    
    activities = db.query(ActivitySession).order_by(ActivitySession.created_at.desc()).all()
    
    # Get user names and scores for each activity
    for activity in activities:
        activity.user = db.query(User).filter(User.id == activity.user_id).first()
        
        # Get score info if scored
        if activity.status == "scored":
            score_record = db.query(ActivityScore).filter(ActivityScore.session_id == activity.id).first()
            if score_record:
                activity.score = score_record.score
                activity.scored_at = score_record.scored_at
                activity.scored_by = db.query(Parent).filter(Parent.id == score_record.parent_id).first()
            else:
                activity.score = None
                activity.scored_at = None
                activity.scored_by = None
        else:
            activity.score = None
            activity.scored_at = None
            activity.scored_by = None
    
    return templates.TemplateResponse("parent/activities.html", {
        "request": request,
        "activities": activities
    })


@router.post("/activities/{activity_id}/delete")
async def delete_activity(
    request: Request,
    activity_id: int,
    db: Session = Depends(get_db)
):
    """Delete an activity session"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "parent":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    from app.models.activity import ActivitySession
    from app.models.scoring import ActivityScore
    
    # Get the activity
    activity = db.query(ActivitySession).filter(ActivitySession.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    try:
        # Delete related scores first (due to foreign key constraint)
        db.query(ActivityScore).filter(ActivityScore.session_id == activity_id).delete()
        
        # Delete the activity
        db.delete(activity)
        db.commit()
        
        logger.info(f"Activity {activity_id} deleted by parent {user_id}")
        
        return RedirectResponse(url="/admin/activities", status_code=302)
        
    except Exception as e:
        logger.error(f"Error deleting activity {activity_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete activity") 