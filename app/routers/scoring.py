from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.activity import ActivitySession
from app.models.parent import Parent
from app.services.scoring_service import ScoringService
from app.config import settings
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")
scoring_service = ScoringService()


@router.get("/{session_id}", response_class=HTMLResponse)
async def scoring_page(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db)
):
    """Show scoring page for a completed activity"""
    session = db.query(ActivitySession).filter(ActivitySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    if session.status != "completed":
        raise HTTPException(status_code=400, detail="Activity not completed yet")
    
    parents = db.query(Parent).all()
    return templates.TemplateResponse("parent/scoring.html", {
        "request": request,
        "session": session,
        "activity": session.generated_activity,
        "parents": parents
    })


@router.post("/{session_id}/score")
async def submit_score(
    request: Request,
    session_id: int,
    parent_id: int = Form(...),
    password: str = Form(...),
    score: int = Form(...),
    db: Session = Depends(get_db)
):
    """Submit a score for an activity"""
    # Verify parent credentials
    if not scoring_service.verify_parent_password(db, parent_id, password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Submit score
    result = scoring_service.score_activity(db, session_id, parent_id, score)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return RedirectResponse(url="/dashboard/child", status_code=302) 