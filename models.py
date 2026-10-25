from sqlalchemy import Boolean, Column, Date, Integer, String

from database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index = True)   # SQLite autoincrements this
    task_name = Column(String(100), nullable=False )
    deadline = Column(Date, nullable= False)
    completed = Column(Boolean, nullable=False, default=False  )