import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User
from app.models.activity import ActivitySession
from app.models.daily_stats import DailyStats
from app.services.activity_service import ActivityService
from app.services.session_service import SessionService
from app.services.scoring_service import ScoringService
from app.config import settings
from fastapi.templating import Jinja2Templates
from typing import List
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger = logging.getLogger('app.routers.activities')

router = APIRouter()
templates = Jinja2Templates(directory="templates")
activity_service = ActivityService()
session_service = SessionService()
scoring_service = ScoringService()


@router.get("/setup", response_class=HTMLResponse)
async def activity_setup_page(request: Request, db: Session = Depends(get_db)):
    """Show activity setup page"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    logger.info(f"User {user_id} accessed activity setup page")

    # Stats for banner
    daily_stats = scoring_service.get_daily_stats(db, user_id)
    total_activities = db.query(ActivitySession).filter(ActivitySession.user_id == user_id, ActivitySession.status == "scored").count()
    total_points = db.query(func.coalesce(func.sum(DailyStats.total_points), 0)).filter(DailyStats.user_id == user_id).scalar()
    max_activities_per_day = settings.max_activities_per_day
    
    # Check if user can start new activity
    if not scoring_service.can_start_new_activity(db, user_id):
        today_stats = daily_stats
        session = db.query(ActivitySession).filter(
            ActivitySession.user_id == user_id,
            ActivitySession.status.in_(["active", "completed"])
        ).first()
        return templates.TemplateResponse(
            "child/daily_limit.html",
            {"request": request, "today_stats": today_stats, "max_activities_per_day": max_activities_per_day, "session": session, "daily_stats": daily_stats, "total_activities": total_activities, "total_points": total_points},
            status_code=400
        )
    
    # Get configuration
    materials = settings.available_materials
    objectives = settings.learning_objectives
    categories = settings.categories
    
    # Get duration options
    duration_options = list(range(
        settings.min_activity_duration,
        settings.max_activity_duration + 1,
        settings.duration_increment
    ))
    
    return templates.TemplateResponse("child/activity_setup.html", {
        "request": request,
        "materials": materials,
        "objectives": objectives,
        "categories": categories,
        "duration_options": duration_options,
        "min_materials": settings.min_materials_selection,
        "max_materials": settings.max_materials_selection,
        "daily_stats": daily_stats,
        "total_activities": total_activities,
        "total_points": total_points,
        "max_activities_per_day": max_activities_per_day
    })


@router.post("/generate")
async def generate_activity(
    request: Request,
    duration: int = Form(...),
    materials: List[str] = Form(...),
    objectives: List[str] = Form(...),
    category: str = Form(...),
    db: Session = Depends(get_db)
):
    """Generate a new activity"""
    logger.info("Starting activity generation")
    
    user_id = request.session.get("user_id")
    if not user_id:
        logger.error("No user_id in session")
        return RedirectResponse(url="/auth/login", status_code=302)
    
    logger.info(f"User {user_id} requested to generate a new activity: duration={duration}, materials={materials}, objectives={objectives}, category={category}")
    
    # Validate inputs
    if duration < settings.min_activity_duration or duration > settings.max_activity_duration:
        logger.error(f"Invalid duration: {duration}")
        raise HTTPException(status_code=400, detail="Invalid duration")
    
    if len(materials) < settings.min_materials_selection or len(materials) > settings.max_materials_selection:
        logger.error(f"Invalid number of materials: {len(materials)}")
        raise HTTPException(status_code=400, detail="Invalid number of materials")
    
    if category not in settings.categories:
        logger.error(f"Invalid category: {category}")
        raise HTTPException(status_code=400, detail="Invalid category")
    
    try:
        logger.info("Calling activity_service.generate_activity")
        # Generate activity
        result = await activity_service.generate_activity(
            db, user_id, duration, materials, objectives, category
        )
        
        logger.info(f"Activity generation result: {result}")
        
        if not result["success"]:
            logger.error(f"Activity generation failed: {result['error']}")
            raise HTTPException(status_code=500, detail=result["error"])
        
        logger.info(f"Activity generated successfully, session_id: {result['session_id']}")
        return RedirectResponse(url=f"/activities/{result['session_id']}/review", status_code=302)
        
    except Exception as e:
        logger.error(f"Error generating activity for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{session_id}/review", response_class=HTMLResponse)
async def review_activity(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db)
):
    """Review generated activity before starting"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    session = activity_service.get_activity_session(db, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    daily_stats = scoring_service.get_daily_stats(db, user_id)
    total_activities = db.query(ActivitySession).filter(ActivitySession.user_id == user_id, ActivitySession.status == "scored").count()
    total_points = db.query(func.coalesce(func.sum(DailyStats.total_points), 0)).filter(DailyStats.user_id == user_id).scalar()
    max_activities_per_day = settings.max_activities_per_day
    
    return templates.TemplateResponse("child/activity_review.html", {
        "request": request,
        "session": session,
        "activity": session.generated_activity,
        "daily_stats": daily_stats,
        "total_activities": total_activities,
        "total_points": total_points,
        "max_activities_per_day": max_activities_per_day
    })


@router.get("/{session_id}/view", response_class=HTMLResponse)
async def view_activity(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db)
):
    """View activity details (for all statuses)"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    session = activity_service.get_activity_session(db, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Get score, parent, and scored_at if activity is scored
    score = None
    parent_name = None
    scored_at = None
    if session.status == "scored":
        from app.models.scoring import ActivityScore
        from app.models.parent import Parent
        score_record = db.query(ActivityScore).filter(ActivityScore.session_id == session_id).first()
        if score_record:
            score = score_record.score
            scored_at = score_record.scored_at
            parent = db.query(Parent).filter(Parent.id == score_record.parent_id).first()
            parent_name = parent.name if parent else None

    daily_stats = scoring_service.get_daily_stats(db, user_id)
    total_activities = db.query(ActivitySession).filter(ActivitySession.user_id == user_id, ActivitySession.status == "scored").count()
    total_points = db.query(func.coalesce(func.sum(DailyStats.total_points), 0)).filter(DailyStats.user_id == user_id).scalar()
    max_activities_per_day = settings.max_activities_per_day
    
    return templates.TemplateResponse("child/activity_view.html", {
        "request": request,
        "session": session,
        "activity": session.generated_activity,
        "score": score,
        "parent_name": parent_name,
        "scored_at": scored_at,
        "daily_stats": daily_stats,
        "total_activities": total_activities,
        "total_points": total_points,
        "max_activities_per_day": max_activities_per_day
    })


@router.post("/{session_id}/start")
async def start_activity(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db)
):
    """Start an activity session"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    logger.info(f"User {user_id} started activity session {session_id}")

    session = activity_service.get_activity_session(db, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    if not activity_service.start_activity(db, session_id):
        raise HTTPException(status_code=400, detail="Cannot start activity")
    
    return RedirectResponse(url=f"/activities/{session_id}/active", status_code=302)


@router.get("/{session_id}/active", response_class=HTMLResponse)
async def active_activity(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db)
):
    """Show active activity page"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    session = activity_service.get_activity_session(db, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Ensure the session is started and start_time is set
    if not session.start_time:
        activity_service.start_activity(db, session_id)
        session = activity_service.get_activity_session(db, session_id)
    
    can_extend = session_service.can_extend_activity(session)
    
    daily_stats = scoring_service.get_daily_stats(db, user_id)
    total_activities = db.query(ActivitySession).filter(ActivitySession.user_id == user_id, ActivitySession.status == "scored").count()
    total_points = db.query(func.coalesce(func.sum(DailyStats.total_points), 0)).filter(DailyStats.user_id == user_id).scalar()
    max_activities_per_day = settings.max_activities_per_day
    
    return templates.TemplateResponse("child/activity_active.html", {
        "request": request,
        "session": session,
        "activity": session.generated_activity,
        "can_extend": can_extend,
        "daily_stats": daily_stats,
        "total_activities": total_activities,
        "total_points": total_points,
        "max_activities_per_day": max_activities_per_day
    })


@router.post("/{session_id}/extend")
async def extend_activity(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db)
):
    """Extend activity time"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = activity_service.extend_activity(db, session_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Add new timer duration to response for frontend
    result["new_timer_duration"] = 5 * 60  # 5 minutes in seconds
    result["extension_time"] = 5  # 5 minutes
    
    return JSONResponse(content=result)


@router.post("/{session_id}/complete")
async def complete_activity(
    request: Request,
    session_id: int,
    actual_duration: int = Form(...),
    db: Session = Depends(get_db)
):
    """Complete an activity"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    logger.info(f"User {user_id} completed activity session {session_id} with actual_duration={actual_duration}")

    session = activity_service.get_activity_session(db, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Validate actual_duration
    if actual_duration <= 0 or actual_duration > 180:  # Max 3 hours
        logger.warning(f"Invalid actual_duration: {actual_duration} for session {session_id}")
        # Use selected_duration as fallback
        actual_duration = session.selected_duration
    
    if not activity_service.complete_activity(db, session_id, actual_duration):
        raise HTTPException(status_code=400, detail="Cannot complete activity")
    
    return RedirectResponse(url=f"/scoring/{session_id}", status_code=302) 