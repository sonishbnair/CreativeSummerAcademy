from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ActivityScore(Base):
    __tablename__ = "activity_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("activity_sessions.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("parents.id"), nullable=False)
    score = Column(Integer, nullable=False)
    scored_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ActivitySession", back_populates="scores")
    parent = relationship("Parent", backref="scores")
    
    def __repr__(self):
        return f"<ActivityScore(id={self.id}, session_id={self.session_id}, score={self.score})>" 