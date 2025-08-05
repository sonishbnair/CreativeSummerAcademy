from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.reimbursement_service import ReimbursementService
from app.services.scoring_service import ScoringService
from fastapi.templating import Jinja2Templates
import logging

logger = logging.getLogger('app.routers.reimbursement')

router = APIRouter()
templates = Jinja2Templates(directory="templates")
reimbursement_service = ReimbursementService()
scoring_service = ScoringService()


@router.get("/", response_class=HTMLResponse)
async def reimbursement_page(request: Request, db: Session = Depends(get_db)):
    """Show reimbursement page with available items"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "child":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    logger.info(f"Child {user_id} accessed reimbursement page")
    
    # Get available reimbursement items
    items = reimbursement_service.get_reimbursement_items()
    
    # Get user's total points
    total_points = reimbursement_service.get_user_total_points(db, user_id)
    
    # Get weekly status
    weekly_status = reimbursement_service.get_weekly_status(db, user_id)
    
    # Get error message from query parameter if any
    error = request.query_params.get("error", "")
    success = request.query_params.get("success", "")
    
    return templates.TemplateResponse("child/reimbursement.html", {
        "request": request,
        "items": items,
        "total_points": total_points,
        "weekly_status": weekly_status,
        "error": error,
        "success": success
    })


@router.get("/confirm/{item_name}", response_class=HTMLResponse)
async def reimbursement_confirm_page(
    request: Request, 
    item_name: str, 
    db: Session = Depends(get_db)
):
    """Show confirmation page for reimbursement"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "child":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    logger.info(f"Child {user_id} confirming reimbursement for {item_name}")
    
    # Validate the reimbursement
    validation = reimbursement_service.validate_reimbursement(db, user_id, item_name)
    
    if not validation["valid"]:
        return RedirectResponse(
            url=f"/reimbursement?error={validation['error']}", 
            status_code=302
        )
    
    return templates.TemplateResponse("child/reimbursement_confirm.html", {
        "request": request,
        "item": validation["item"],
        "user_points": validation["user_points"],
        "remaining_points": validation["remaining_points"]
    })


@router.post("/process", response_class=HTMLResponse)
async def process_reimbursement(
    request: Request,
    item_name: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process the reimbursement"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "child":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    logger.info(f"Child {user_id} processing reimbursement for {item_name}")
    
    # Process the reimbursement
    result = reimbursement_service.process_reimbursement(db, user_id, item_name)
    
    if result["success"]:
        success_message = result["message"]
        return RedirectResponse(
            url=f"/reimbursement?success={success_message}", 
            status_code=302
        )
    else:
        return RedirectResponse(
            url=f"/reimbursement?error={result['error']}", 
            status_code=302
        )


@router.get("/history", response_class=HTMLResponse)
async def reimbursement_history_page(request: Request, db: Session = Depends(get_db)):
    """Show reimbursement history page"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    
    if not user_id or user_type != "child":
        return RedirectResponse(url="/auth/login", status_code=302)
    
    logger.info(f"Child {user_id} accessed reimbursement history")
    
    # Get user's reimbursement history
    history = reimbursement_service.get_user_reimbursement_history(db, user_id)
    
    # Get total points
    total_points = reimbursement_service.get_user_total_points(db, user_id)
    
    return templates.TemplateResponse("child/reimbursement_history.html", {
        "request": request,
        "history": history,
        "total_points": total_points
    }) 