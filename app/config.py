from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # Anthropic API Configuration
    anthropic_api_key: str
    anthropic_model: str = "claude-3-haiku-20240307"
    anthropic_max_tokens: int = 1500
    anthropic_temperature: float = 0.7
    
    # Database Configuration
    database_url: str = "sqlite:///./galactic_academy.db"
    
    # Application Configuration
    secret_key: str
    environment: str = "development"
    debug: bool = True
    
    # Activity Configuration
    max_activities_per_day: int = 3
    min_activity_duration: int = 1 
    max_activity_duration: int = 2 
    duration_increment: int = 1  
    extension_penalty: int = 5
    max_extensions_per_activity: int = 2
    regenerate_cooldown_minutes: int = 15
    
    # Materials Configuration
    min_materials_selection: int = 3
    max_materials_selection: int = 8
    
    # Available materials (configurable)
    available_materials: List[str] = [
        "cardboard", "scissors", "aluminum_foil", "markers",
        "glue", "string", "beads", "paint", "paper", "tape",
        "popsicle_sticks", "rubber_bands", "buttons", "yarn",
        "construction_paper", "pipe_cleaners", "googly_eyes"
    ]
    
    # Learning objectives
    learning_objectives: List[str] = [
        "engineering", "creativity", "following_directions",
        "problem_solving", "fine_motor_skills", "color_recognition",
        "spatial_awareness", "patience", "focus"
    ]
    
    # Activity categories
    categories: List[str] = [
        "building", "painting", "crafting", "jewelry_making"
    ]
    
    # Logging Configuration
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create settings instance
settings = Settings() 