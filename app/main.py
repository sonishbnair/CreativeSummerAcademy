from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db, create_tables
from app.config import settings
from app.routers import auth, activities, scoring, dashboard, admin
from starlette.middleware.sessions import SessionMiddleware
import os

# Create FastAPI app
app = FastAPI(
    title="Creative Summer Academy",
    description="A gamified web application for kids' summer activities with AI-generated crafts",
    version="0.1.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(activities.router, prefix="/activities", tags=["activities"])
app.include_router(scoring.router, prefix="/scoring", tags=["scoring"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    create_tables()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - redirect to child dashboard"""
    return RedirectResponse(url="/dashboard/child")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "app": "Creative Summer Academy"}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 handler"""
    return templates.TemplateResponse(
        "shared/404.html",
        {"request": request},
        status_code=404
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """Custom 500 handler"""
    return templates.TemplateResponse(
        "shared/500.html",
        {"request": request},
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 