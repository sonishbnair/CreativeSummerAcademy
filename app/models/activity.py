from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ActivitySession(Base):
    __tablename__ = "activity_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="active")  # active, completed, scored
    
    # Child selections
    selected_duration = Column(Integer, nullable=False)
    selected_materials = Column(JSON, nullable=False)
    selected_objectives = Column(JSON, nullable=False)
    selected_category = Column(String(50), nullable=False)
    
    # Generated content
    anthropic_prompt = Column(Text)
    generated_activity = Column(JSON, nullable=False)
    generation_timestamp = Column(DateTime(timezone=True))
    
    # Session tracking
    start_time = Column(DateTime(timezone=True))
    pause_time = Column(DateTime(timezone=True))
    resume_time = Column(DateTime(timezone=True))
    actual_duration = Column(Integer)
    extensions_used = Column(Integer, default=0)
    max_possible_score = Column(Integer, default=100)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="activity_sessions")
    scores = relationship("ActivityScore", back_populates="session")
    
    def __repr__(self):
        return f"<ActivitySession(id={self.id}, user_id={self.user_id}, status='{self.status}')>" 