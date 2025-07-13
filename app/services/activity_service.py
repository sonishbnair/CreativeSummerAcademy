import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.activity import ActivitySession
from app.models.user import User
from app.services.anthropic_service import AnthropicService
from app.services.template_service import TemplateService
from app.config import settings
import json
import uuid
from datetime import datetime
import re

# Set up logging
logger = logging.getLogger(__name__)

class ActivityService:
    def __init__(self):
        self.anthropic_service = AnthropicService()
        self.template_service = TemplateService()
    
    async def generate_activity(
        self,
        db: Session,
        user_id: int,
        selected_duration: int,
        selected_materials: List[str],
        selected_objectives: List[str],
        selected_category: str
    ) -> Dict[str, Any]:
        """
        Generate a new activity based on child selections
        """
        logger.info(f"ActivityService.generate_activity called with user_id={user_id}, duration={selected_duration}")
        
        try:
            # Get recent activities for uniqueness check
            logger.info("Getting recent activities")
            recent_activities = self._get_recent_activities(db, user_id)
            recent_activities_summary = self._format_recent_activities(recent_activities)
            logger.info(f"Recent activities summary: {recent_activities_summary}")
            
            # Prepare template variables
            variables = {
                "selected_duration": selected_duration,
                "selected_materials": self.template_service.format_materials_list(selected_materials),
                "selected_objectives": self.template_service.format_objectives_list(selected_objectives),
                "selected_category": selected_category,
                "min_materials_count": len(selected_materials) - 1,
                "recent_activities_summary": recent_activities_summary
            }
            logger.info(f"Template variables prepared: {variables}")
            
            # Generate prompt
            logger.info("Generating prompt from template")
            prompt = self.template_service.populate_template(variables)
            logger.info(f"Generated prompt length: {len(prompt)}")
            logger.info(f"Full generated prompt:\n{prompt}")
            
            # Generate activity with retry
            logger.info("Calling anthropic service")
            result = await self.anthropic_service.generate_activity_with_retry(prompt)
            logger.info(f"Anthropic service result: {result}")
            
            if not result["success"]:
                logger.error(f"Anthropic service failed: {result['error']}")
                return {
                    "success": False,
                    "error": result["error"]
                }
            
            # Parse the generated content
            logger.info("Parsing generated activity")
            parsed_activity = self._parse_generated_activity(result["content"])
            logger.info(f"Parsed activity: {parsed_activity}")
            
            # Create activity session
            logger.info("Creating activity session in database")
            session = ActivitySession(
                user_id=user_id,
                selected_duration=selected_duration,
                selected_materials=selected_materials,
                selected_objectives=selected_objectives,
                selected_category=selected_category,
                anthropic_prompt=prompt,
                generated_activity=parsed_activity,
                generation_timestamp=datetime.utcnow()
            )
            
            db.add(session)
            db.commit()
            db.refresh(session)
            logger.info(f"Activity session created with ID: {session.id}")
            
            return {
                "success": True,
                "session_id": session.id,
                "activity": parsed_activity,
                "usage": result.get("usage", {})
            }
            
        except Exception as e:
            logger.error(f"Error in generate_activity: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Activity generation failed: {str(e)}"
            }
    
    def _get_recent_activities(self, db: Session, user_id: int, limit: int = 5) -> List[ActivitySession]:
        """Get recent activities for uniqueness check"""
        return db.query(ActivitySession)\
            .filter(ActivitySession.user_id == user_id)\
            .order_by(ActivitySession.created_at.desc())\
            .limit(limit)\
            .all()
    
    def _format_recent_activities(self, activities: List[ActivitySession]) -> str:
        """Format recent activities for template"""
        if not activities:
            return "No recent activities"
        
        summaries = []
        for i, activity in enumerate(activities, 1):
            title = activity.generated_activity.get("title", f"Activity {i}")
            summaries.append(f"{i}. {title}")
        
        return "; ".join(summaries)
    
    def _parse_generated_activity(self, content: str) -> Dict[str, Any]:
        """
        Parse the generated activity content into structured format
        """
        import re
        activity = {
            "title": "",
            "description": "",
            "steps": [],
            "materials_used": [],
            "safety_notes": [],
            "estimated_time": "",
            "raw_content": content
        }

        # Extract title (first non-empty line)
        lines = content.split('\n')
        for line in lines:
            if line.strip():
                activity["title"] = line.strip()
                break

        # Extract description (all lines after title up to first numbered step)
        desc_lines = []
        found_title = False
        for line in lines:
            if not found_title and line.strip():
                found_title = True
                continue
            if found_title:
                if re.match(r"^\s*\d+\. ", line):
                    break
                desc_lines.append(line)
        activity["description"] = ' '.join([l.strip() for l in desc_lines if l.strip()])

        # Extract steps (lines starting with a number and period)
        step_lines = re.findall(r"^\s*\d+\.\s*(.*)", content, re.MULTILINE)
        activity["steps"] = [s.strip() for s in step_lines if s.strip()]

        return activity
    
    def get_activity_session(self, db: Session, session_id: int) -> Optional[ActivitySession]:
        """Get activity session by ID"""
        return db.query(ActivitySession).filter(ActivitySession.id == session_id).first()
    
    def start_activity(self, db: Session, session_id: int) -> bool:
        """Start an activity session"""
        session = self.get_activity_session(db, session_id)
        if session:
            if not session.start_time:
                session.start_time = datetime.utcnow()
            session.status = "active"
            db.commit()
            return True
        return False
    
    def extend_activity(self, db: Session, session_id: int) -> Dict[str, Any]:
        """Extend activity time"""
        session = self.get_activity_session(db, session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        if session.extensions_used >= settings.max_extensions_per_activity:
            return {"success": False, "error": "Maximum extensions reached"}
        
        session.extensions_used += 1
        session.max_possible_score -= settings.extension_penalty
        db.commit()
        
        return {
            "success": True,
            "extensions_used": session.extensions_used,
            "max_possible_score": session.max_possible_score
        }
    
    def complete_activity(self, db: Session, session_id: int, actual_duration: int) -> bool:
        """Mark activity as completed"""
        session = self.get_activity_session(db, session_id)
        if session:
            session.status = "completed"
            session.actual_duration = actual_duration
            db.commit()
            return True
        return False 