from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ReimbursementItem(Base):
    """Model for reimbursement items configuration"""
    __tablename__ = "reimbursement_items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    points_cost = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReimbursementHistory(Base):
    """Model for tracking reimbursement history"""
    __tablename__ = "reimbursement_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_name = Column(String, nullable=False)
    points_cost = Column(Integer, nullable=False)
    redeemed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="reimbursements")
    point_deduction = relationship("PointDeduction", back_populates="reimbursement", uselist=False)


class WeeklyReimbursementStatus(Base):
    """Model for tracking weekly reimbursement status"""
    __tablename__ = "weekly_reimbursement_status"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_start_date = Column(Date, nullable=False)  # Friday of the week
    can_reimburse = Column(Boolean, default=True)
    last_reimbursement_date = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="weekly_reimbursement_status")


class PointDeduction(Base):
    """Model for tracking point deductions from reimbursements"""
    __tablename__ = "point_deductions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    points_deducted = Column(Integer, nullable=False)
    deduction_date = Column(DateTime(timezone=True), server_default=func.now())
    reimbursement_id = Column(Integer, ForeignKey("reimbursement_history.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="point_deductions")
    reimbursement = relationship("ReimbursementHistory", back_populates="point_deduction") 