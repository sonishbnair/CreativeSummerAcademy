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
logger = logging.getLogger('app.routers.admin')

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
    
    # Get current parent for user banner
    from app.models.parent import Parent
    current_parent = db.query(Parent).filter(Parent.id == user_id).first()
    
    logger.info(f"Admin {user_id} accessed config page")
    return templates.TemplateResponse("parent/config.html", {
        "request": request,
        "config": config,
        "current_parent": current_parent
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
    
    # Get current parent for user banner
    current_parent = db.query(Parent).filter(Parent.id == user_id).first()
    
    logger.info(f"Admin {user_id} accessed reports page")
    return templates.TemplateResponse("parent/reports.html", {
        "request": request,
        "user_stats": user_stats,
        "current_parent": current_parent
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
    
    # Get current parent for user banner
    from app.models.parent import Parent
    current_parent = db.query(Parent).filter(Parent.id == user_id).first()
    
    logger.info(f"Admin {user_id} accessed activity management page")
    return templates.TemplateResponse("parent/activities.html", {
        "request": request,
        "activities": activities,
        "current_parent": current_parent
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
    from app.services.scoring_service import ScoringService
    
    # Get the activity
    activity = db.query(ActivitySession).filter(ActivitySession.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Store user_id and activity date for recalculation
    activity_user_id = activity.user_id
    activity_date = activity.created_at.date() if activity.created_at else None
    
    try:
        # Delete related scores first (due to foreign key constraint)
        db.query(ActivityScore).filter(ActivityScore.session_id == activity_id).delete()
        
        # Delete the activity
        db.delete(activity)
        db.commit()
        
        # Recalculate daily stats for the user if activity was scored
        if activity.status == "scored" and activity_date:
            scoring_service = ScoringService()
            scoring_service.recalculate_daily_stats(db, activity_user_id, activity_date)
            logger.info(f"Recalculated daily stats for user {activity_user_id} after deleting activity {activity_id}")
        
        logger.info(f"Activity {activity_id} deleted by parent {user_id}")
        
        return RedirectResponse(url="/admin/activities", status_code=302)
        
    except Exception as e:
        logger.error(f"Error deleting activity {activity_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete activity")


@router.post("/recalculate-stats/{user_id}")
async def recalculate_user_stats(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Manually recalculate daily stats for a user"""
    admin_user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not admin_user_id or user_type != "parent":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Check admin privileges
    from app.models.parent import Parent
    admin_parent = db.query(Parent).filter(Parent.id == admin_user_id).first()
    if not admin_parent or admin_parent.name != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    # Check if user exists
    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        from app.services.scoring_service import ScoringService
        scoring_service = ScoringService()
        
        # Recalculate stats for today
        today_stats = scoring_service.recalculate_daily_stats(db, user_id)
        
        logger.info(f"Recalculated daily stats for user {user_id} (name: {user.name}): {today_stats}")
        
        return RedirectResponse(url="/admin/activities", status_code=302)
        
    except Exception as e:
        logger.error(f"Error recalculating stats for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to recalculate stats")


@router.get("/users", response_class=HTMLResponse)
async def admin_users(request: Request, db: Session = Depends(get_db)):
    """Admin users management page - only accessible by 'admin' user"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "parent":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Check if the logged-in parent is named "admin"
    from app.models.parent import Parent
    admin_parent = db.query(Parent).filter(Parent.id == user_id).first()
    if not admin_parent or admin_parent.name != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    # Get all children and parents
    from app.models.user import User
    children = db.query(User).order_by(User.name).all()
    parents = db.query(Parent).order_by(Parent.name).all()
    
    # Get current parent for user banner
    current_parent = db.query(Parent).filter(Parent.id == user_id).first()
    
    logger.info(f"Admin {user_id} accessed user management page")
    return templates.TemplateResponse("parent/admin_users.html", {
        "request": request,
        "children": children,
        "parents": parents,
        "current_parent": current_parent
    })


@router.post("/users/child/add")
async def add_child(
    request: Request,
    child_name: str = Form(...),
    db: Session = Depends(get_db)
):
    """Add a new child user"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "parent":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Check admin privileges
    from app.models.parent import Parent
    admin_parent = db.query(Parent).filter(Parent.id == user_id).first()
    if not admin_parent or admin_parent.name != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    # Check if child name already exists
    from app.models.user import User
    existing_child = db.query(User).filter(User.name == child_name).first()
    if existing_child:
        raise HTTPException(status_code=400, detail="Child with this name already exists")
    
    # Create new child
    new_child = User(name=child_name)
    db.add(new_child)
    db.commit()
    db.refresh(new_child)
    
    logger.info(f"Child '{child_name}' added by admin {user_id}")
    return RedirectResponse(url="/admin/users", status_code=302)


@router.post("/users/child/{child_id}/delete")
async def delete_child(
    request: Request,
    child_id: int,
    db: Session = Depends(get_db)
):
    """Delete a child user"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "parent":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Check admin privileges
    from app.models.parent import Parent
    admin_parent = db.query(Parent).filter(Parent.id == user_id).first()
    if not admin_parent or admin_parent.name != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    # Get the child
    from app.models.user import User
    from app.models.activity import ActivitySession
    from app.models.daily_stats import DailyStats
    from app.models.scoring import ActivityScore
    
    child = db.query(User).filter(User.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    
    try:
        # Delete related data first (due to foreign key constraints)
        # Delete activity scores for this child's sessions
        child_sessions = db.query(ActivitySession).filter(ActivitySession.user_id == child_id).all()
        for session in child_sessions:
            db.query(ActivityScore).filter(ActivityScore.session_id == session.id).delete()
        
        # Delete activity sessions
        db.query(ActivitySession).filter(ActivitySession.user_id == child_id).delete()
        
        # Delete daily stats
        db.query(DailyStats).filter(DailyStats.user_id == child_id).delete()
        
        # Delete the child
        db.delete(child)
        db.commit()
        
        logger.info(f"Child '{child.name}' (ID: {child_id}) deleted by admin {user_id}")
        return RedirectResponse(url="/admin/users", status_code=302)
        
    except Exception as e:
        logger.error(f"Error deleting child {child_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete child")


@router.post("/users/parent/add")
async def add_parent(
    request: Request,
    parent_name: str = Form(...),
    parent_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Add a new parent user"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "parent":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Check admin privileges
    from app.models.parent import Parent
    admin_parent = db.query(Parent).filter(Parent.id == user_id).first()
    if not admin_parent or admin_parent.name != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    # Check if parent name already exists
    existing_parent = db.query(Parent).filter(Parent.name == parent_name).first()
    if existing_parent:
        raise HTTPException(status_code=400, detail="Parent with this name already exists")
    
    # Create new parent
    import bcrypt
    password_hash = bcrypt.hashpw(parent_password.encode('utf-8'), bcrypt.gensalt())
    new_parent = Parent(name=parent_name, password_hash=password_hash.decode('utf-8'))
    db.add(new_parent)
    db.commit()
    db.refresh(new_parent)
    
    logger.info(f"Parent '{parent_name}' added by admin {user_id}")
    return RedirectResponse(url="/admin/users", status_code=302)


@router.post("/users/parent/{parent_id}/delete")
async def delete_parent(
    request: Request,
    parent_id: int,
    db: Session = Depends(get_db)
):
    """Delete a parent user"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "parent":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Check admin privileges
    from app.models.parent import Parent
    admin_parent = db.query(Parent).filter(Parent.id == user_id).first()
    if not admin_parent or admin_parent.name != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    # Prevent admin from deleting themselves
    if parent_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")
    
    # Get the parent
    parent = db.query(Parent).filter(Parent.id == parent_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    
    try:
        # Delete related scores first (due to foreign key constraint)
        from app.models.scoring import ActivityScore
        db.query(ActivityScore).filter(ActivityScore.parent_id == parent_id).delete()
        
        # Delete the parent
        db.delete(parent)
        db.commit()
        
        logger.info(f"Parent '{parent.name}' (ID: {parent_id}) deleted by admin {user_id}")
        return RedirectResponse(url="/admin/users", status_code=302)
        
    except Exception as e:
        logger.error(f"Error deleting parent {parent_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete parent") 