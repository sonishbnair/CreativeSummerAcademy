from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.config_service import ConfigService
from app.config import settings
from fastapi.templating import Jinja2Templates
from typing import List
from datetime import date

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