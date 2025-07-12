from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.parent import Parent
from app.services.scoring_service import ScoringService
from app.config import settings
from fastapi.templating import Jinja2Templates
import bcrypt
import secrets

router = APIRouter()
templates = Jinja2Templates(directory="templates")
scoring_service = ScoringService()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login page"""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    user_type: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle login for both children and parents"""
    if user_type == "child":
        # Simple child login - just create/get user
        user = db.query(User).filter(User.name == username).first()
        if not user:
            user = User(name=username)
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Set session
        request.session["user_id"] = user.id
        request.session["user_type"] = "child"
        return RedirectResponse(url="/dashboard/child", status_code=302)
    
    elif user_type == "parent":
        # Parent login with password verification
        parent = db.query(Parent).filter(Parent.name == username).first()
        if not parent:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not scoring_service.verify_parent_password(db, parent.id, password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Set session
        request.session["user_id"] = parent.id
        request.session["user_type"] = "parent"
        return RedirectResponse(url="/dashboard/parent", status_code=302)
    
    raise HTTPException(status_code=400, detail="Invalid user type")


@router.get("/logout")
async def logout(request: Request):
    """Logout user"""
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=302)


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request, db: Session = Depends(get_db)):
    """Show initial setup page with existing users"""
    # Get existing children and parents
    existing_children = db.query(User).all()
    existing_parents = db.query(Parent).all()
    
    return templates.TemplateResponse("auth/setup.html", {
        "request": request,
        "existing_children": existing_children,
        "existing_parents": existing_parents
    })


@router.post("/setup")
async def setup(
    request: Request,
    setup_type: str = Form(...),
    parent_name: str = Form(None),
    parent_password: str = Form(None),
    parent_confirm_password: str = Form(None),
    child_id: str = Form(None),
    new_child_name: str = Form(None),
    child_name: str = Form(None),
    parent_id: str = Form(None),
    new_parent_name: str = Form(None),
    new_parent_password: str = Form(None),
    new_parent_confirm_password: str = Form(None),
    db: Session = Depends(get_db)
):
    """Initial setup - create accounts based on setup type"""
    
    if setup_type == "parent":
        # Parent registration
        if not parent_name or not parent_password or not parent_confirm_password:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Validate password confirmation
        if parent_password != parent_confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        
        # Create parent account
        password_hash = bcrypt.hashpw(parent_password.encode('utf-8'), bcrypt.gensalt())
        parent = Parent(name=parent_name, password_hash=password_hash.decode('utf-8'))
        db.add(parent)
        db.commit()
        db.refresh(parent)
        
        # Handle child creation if requested
        if child_id == "new" and new_child_name:
            child = User(name=new_child_name)
            db.add(child)
            db.commit()
            db.refresh(child)
        
        # Set parent session
        request.session["user_id"] = parent.id
        request.session["user_type"] = "parent"
        
        return RedirectResponse(url="/dashboard/parent", status_code=302)
        
    elif setup_type == "child":
        # Child registration
        if not child_name:
            raise HTTPException(status_code=400, detail="Missing child name")
        
        # Create child user
        child = User(name=child_name)
        db.add(child)
        db.commit()
        db.refresh(child)
        
        # Handle parent creation if requested
        if parent_id == "new" and new_parent_name and new_parent_password:
            if new_parent_password != new_parent_confirm_password:
                raise HTTPException(status_code=400, detail="Passwords do not match")
            
            password_hash = bcrypt.hashpw(new_parent_password.encode('utf-8'), bcrypt.gensalt())
            parent = Parent(name=new_parent_name, password_hash=password_hash.decode('utf-8'))
            db.add(parent)
            db.commit()
            db.refresh(parent)
        
        # Set child session
        request.session["user_id"] = child.id
        request.session["user_type"] = "child"
        
        return RedirectResponse(url="/dashboard/child", status_code=302)
    
    raise HTTPException(status_code=400, detail="Invalid setup type") 