from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User
from app.models.activity import ActivitySession
from app.models.daily_stats import DailyStats
from app.models.scoring import ActivityScore
from app.services.session_service import SessionService
from app.services.scoring_service import ScoringService
from app.services.config_service import ConfigService
from app.config import settings
from fastapi.templating import Jinja2Templates
from datetime import date

router = APIRouter()
templates = Jinja2Templates(directory="templates")
session_service = SessionService()
scoring_service = ScoringService()
config_service = ConfigService()


@router.get("/child", response_class=HTMLResponse)
async def child_dashboard(request: Request, db: Session = Depends(get_db)):
    """Child dashboard"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Get active session
    active_session = session_service.get_active_session(db, user_id)
    
    # Get daily stats
    daily_stats = scoring_service.get_daily_stats(db, user_id)
    
    # Get total activities (scored)
    total_activities = db.query(ActivitySession).filter(ActivitySession.user_id == user_id, ActivitySession.status == "scored").count()
    # Get total points (sum of all days)
    total_points = db.query(func.coalesce(func.sum(DailyStats.total_points), 0)).filter(DailyStats.user_id == user_id).scalar()
    
    # Get recent activities with scores
    recent_activities = db.query(ActivitySession)\
        .filter(ActivitySession.user_id == user_id)\
        .order_by(ActivitySession.created_at.desc())\
        .limit(5)\
        .all()
    
    # Get scores and scored_at for recent activities
    for activity in recent_activities:
        if activity.status == "scored":
            score_record = db.query(ActivityScore).filter(ActivityScore.session_id == activity.id).first()
            activity.score = score_record.score if score_record else None
            activity.scored_at = score_record.scored_at if score_record else None
        else:
            activity.score = None
            activity.scored_at = None
    
    # Check if can start new activity
    can_start_new = scoring_service.can_start_new_activity(db, user_id)
    
    return templates.TemplateResponse("child/dashboard.html", {
        "request": request,
        "user": user,
        "active_session": active_session,
        "daily_stats": daily_stats,
        "recent_activities": recent_activities,
        "can_start_new": can_start_new,
        "total_activities": total_activities,
        "total_points": total_points
    })


@router.get("/parent", response_class=HTMLResponse)
async def parent_dashboard(request: Request, db: Session = Depends(get_db)):
    """Parent dashboard"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "parent":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Get all users (children)
    children = db.query(User).all()
    
    # Get pending activities that need scoring
    pending_activities = db.query(ActivitySession)\
        .filter(ActivitySession.status == "completed")\
        .all()
    
    # Get system configuration
    config = config_service.get_full_config(db)
    
    # Get current parent for admin check
    from app.models.parent import Parent
    current_parent = db.query(Parent).filter(Parent.id == user_id).first()
    
    return templates.TemplateResponse("parent/dashboard.html", {
        "request": request,
        "children": children,
        "pending_activities": pending_activities,
        "config": config,
        "current_parent": current_parent
    })


@router.get("/rules/child", response_class=HTMLResponse)
async def child_rules(request: Request):
    """Child rules page"""
    return templates.TemplateResponse("shared/rules_child.html", {"request": request})


@router.get("/rules/parent", response_class=HTMLResponse)
async def parent_rules(request: Request):
    """Parent rules page"""
    return templates.TemplateResponse("shared/rules_parent.html", {"request": request}) 