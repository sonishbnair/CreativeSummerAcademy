from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.config import SystemConfig
from app.config import settings
import json


class ConfigService:
    def __init__(self):
        pass
    
    def get_system_config(self, db: Session, key: str) -> Any:
        """Get system configuration value"""
        config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
        if config:
            return config.config_value
        return None
    
    def set_system_config(self, db: Session, key: str, value: Any) -> bool:
        """Set system configuration value"""
        config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
        
        if config:
            config.config_value = value
        else:
            config = SystemConfig(config_key=key, config_value=value)
            db.add(config)
        
        db.commit()
        return True
    
    def get_activity_limits(self, db: Session) -> Dict[str, Any]:
        """Get activity limits configuration"""
        return {
            "max_activities_per_day": settings.max_activities_per_day,
            "min_activity_duration": settings.min_activity_duration,
            "max_activity_duration": settings.max_activity_duration,
            "duration_increment": settings.duration_increment
        }
    
    def get_scoring_config(self, db: Session) -> Dict[str, Any]:
        """Get scoring configuration"""
        return {
            "min_score": 0,
            "max_score": 100,
            "extension_penalty": settings.extension_penalty
        }
    
    def get_materials_config(self, db: Session) -> Dict[str, Any]:
        """Get materials configuration"""
        return {
            "available_items": settings.available_materials,
            "min_selection": settings.min_materials_selection,
            "max_selection": settings.max_materials_selection
        }
    
    def get_learning_objectives(self, db: Session) -> List[str]:
        """Get available learning objectives"""
        return settings.learning_objectives
    
    def get_categories(self, db: Session) -> List[str]:
        """Get available activity categories"""
        return settings.categories
    
    def update_materials_list(self, db: Session, materials: List[str]) -> bool:
        """Update available materials list"""
        # This would require updating the settings, which might need a restart
        # For now, we'll store it in the database
        return self.set_system_config(db, "available_materials", materials)
    
    def get_full_config(self, db: Session) -> Dict[str, Any]:
        """Get full system configuration"""
        return {
            "activity_limits": self.get_activity_limits(db),
            "scoring": self.get_scoring_config(db),
            "materials": self.get_materials_config(db),
            "learning_objectives": self.get_learning_objectives(db),
            "categories": self.get_categories(db)
        } 