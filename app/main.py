import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db, create_tables
from app.config import settings
from app.routers import auth, activities, scoring, dashboard, admin
from starlette.middleware.sessions import SessionMiddleware

# --- Logging Setup ---
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y-%m-%d')}.log")

log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

# Remove all handlers from root logger
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Set up file handler for app logs only
file_handler = TimedRotatingFileHandler(log_filename, when="midnight", backupCount=7, encoding="utf-8")
file_handler.setLevel(log_level)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))

# Get app logger and configure
app_logger = logging.getLogger("app")
app_logger.setLevel(log_level)
app_logger.handlers = [file_handler]
app_logger.propagate = False

# Optionally, set all app sub-loggers to use the same handler
for name in logging.root.manager.loggerDict:
    if name.startswith("app."):
        logger = logging.getLogger(name)
        logger.setLevel(log_level)
        logger.handlers = [file_handler]
        logger.propagate = False

# --- End Logging Setup ---

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