import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.reimbursement import ReimbursementHistory, WeeklyReimbursementStatus, PointDeduction
from app.models.user import User
from app.models.daily_stats import DailyStats
from app.services.scoring_service import ScoringService

logger = logging.getLogger(__name__)


class ReimbursementService:
    def __init__(self):
        self.json_file_path = "app/reimbursement_items.json"
        self.scoring_service = ScoringService()
    
    def _load_reimbursement_items(self) -> List[Dict[str, Any]]:
        """Load reimbursement items from JSON file"""
        try:
            with open(self.json_file_path, 'r') as f:
                items = json.load(f)
            return [item for item in items if item.get("is_active", True)]
        except FileNotFoundError:
            logger.error(f"Reimbursement items file not found: {self.json_file_path}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing reimbursement items JSON: {e}")
            return []
    
    def get_reimbursement_items(self) -> List[Dict[str, Any]]:
        """Get all active reimbursement items"""
        return self._load_reimbursement_items()
    
    def get_item_by_name(self, item_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific reimbursement item by name"""
        items = self._load_reimbursement_items()
        for item in items:
            if item["name"] == item_name:
                return item
        return None
    
    def get_user_total_points(self, db: Session, user_id: int) -> int:
        """Get total points earned by user (after reimbursements)"""
        # Get total points from daily stats
        total_points = db.query(func.coalesce(func.sum(DailyStats.total_points), 0)).filter(
            DailyStats.user_id == user_id
        ).scalar()
        
        # Get total deductions from reimbursements
        total_deductions = db.query(func.coalesce(func.sum(PointDeduction.points_deducted), 0)).filter(
            PointDeduction.user_id == user_id
        ).scalar()
        
        # Calculate final total
        final_points = total_points - total_deductions
        
        # Ensure points don't go negative
        if final_points < 0:
            final_points = 0
            
        return int(final_points)
    
    def can_user_reimburse_this_week(self, db: Session, user_id: int) -> bool:
        """Check if user can reimburse this week (Friday reset)"""
        today = datetime.now().date()
        
        # Find the most recent Friday (or today if it's Friday)
        days_since_friday = (today.weekday() - 4) % 7  # Friday is 4
        if days_since_friday == 0:
            week_start = today
        else:
            week_start = today - timedelta(days=days_since_friday)
        
        # Check if user has already reimbursed this week
        status = db.query(WeeklyReimbursementStatus).filter(
            WeeklyReimbursementStatus.user_id == user_id,
            WeeklyReimbursementStatus.week_start_date == week_start
        ).first()
        
        if not status:
            # No record for this week, user can reimburse
            return True
        
        return status.can_reimburse
    
    def validate_reimbursement(self, db: Session, user_id: int, item_name: str) -> Dict[str, Any]:
        """Validate if user can reimburse the specified item"""
        # Check if item exists and is active
        item = self.get_item_by_name(item_name)
        if not item:
            return {
                "valid": False,
                "error": "Item not found or not available"
            }
        
        # Check weekly limit
        if not self.can_user_reimburse_this_week(db, user_id):
            return {
                "valid": False,
                "error": "You have already used your weekly reimbursement this week. Try again next Friday!"
            }
        
        # Check if user has enough points
        user_points = self.get_user_total_points(db, user_id)
        if user_points < item["points_cost"]:
            return {
                "valid": False,
                "error": f"You need {item['points_cost']} points for this item, but you only have {user_points} points"
            }
        
        return {
            "valid": True,
            "item": item,
            "user_points": user_points,
            "remaining_points": user_points - item["points_cost"]
        }
    
    def process_reimbursement(self, db: Session, user_id: int, item_name: str) -> Dict[str, Any]:
        """Process the reimbursement and update database"""
        # Validate first
        validation = self.validate_reimbursement(db, user_id, item_name)
        if not validation["valid"]:
            return validation
        
        item = validation["item"]
        user_points = validation["user_points"]
        
        try:
            # Create reimbursement history record
            history = ReimbursementHistory(
                user_id=user_id,
                item_name=item["name"],
                points_cost=item["points_cost"]
            )
            db.add(history)
            db.flush()  # Flush to get the ID without committing
            
            # Update weekly status
            today = datetime.now().date()
            days_since_friday = (today.weekday() - 4) % 7
            if days_since_friday == 0:
                week_start = today
            else:
                week_start = today - timedelta(days=days_since_friday)
            
            status = db.query(WeeklyReimbursementStatus).filter(
                WeeklyReimbursementStatus.user_id == user_id,
                WeeklyReimbursementStatus.week_start_date == week_start
            ).first()
            
            if not status:
                status = WeeklyReimbursementStatus(
                    user_id=user_id,
                    week_start_date=week_start,
                    can_reimburse=False,
                    last_reimbursement_date=datetime.now()
                )
                db.add(status)
            else:
                status.can_reimburse = False
                status.last_reimbursement_date = datetime.now()
            
            # Create point deduction record
            point_deduction = PointDeduction(
                user_id=user_id,
                points_deducted=item["points_cost"],
                reimbursement_id=history.id
            )
            db.add(point_deduction)
            
            db.commit()
            
            logger.info(f"Reimbursement processed: user_id={user_id}, item={item['name']}, points={item['points_cost']}")
            
            return {
                "success": True,
                "item": item,
                "points_spent": item["points_cost"],
                "remaining_points": user_points - item["points_cost"],
                "message": f"Successfully redeemed {item['name']} for {item['points_cost']} points!"
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing reimbursement: {e}")
            return {
                "success": False,
                "error": "An error occurred while processing your reimbursement. Please try again."
            }
    
    def get_user_reimbursement_history(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Get user's reimbursement history"""
        history = db.query(ReimbursementHistory).filter(
            ReimbursementHistory.user_id == user_id
        ).order_by(ReimbursementHistory.redeemed_at.desc()).all()
        
        return [
            {
                "item_name": record.item_name,
                "points_cost": record.points_cost,
                "redeemed_at": record.redeemed_at
            }
            for record in history
        ]
    
    def get_weekly_status(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get user's current weekly reimbursement status"""
        today = datetime.now().date()
        days_since_friday = (today.weekday() - 4) % 7
        if days_since_friday == 0:
            week_start = today
        else:
            week_start = today - timedelta(days=days_since_friday)
        
        status = db.query(WeeklyReimbursementStatus).filter(
            WeeklyReimbursementStatus.user_id == user_id,
            WeeklyReimbursementStatus.week_start_date == week_start
        ).first()
        
        if not status:
            return {
                "can_reimburse": True,
                "last_reimbursement": None,
                "next_reset": week_start + timedelta(days=7)
            }
        
        return {
            "can_reimburse": status.can_reimburse,
            "last_reimbursement": status.last_reimbursement_date,
            "next_reset": week_start + timedelta(days=7)
        } 