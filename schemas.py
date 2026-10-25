from datetime import date

from pydantic import BaseModel, ConfigDict, Field

class TaskBase(BaseModel):
    task_name : str = Field(min_length=1, max_length=100)
    deadline : date # "2026-10-25"; junk -> automatic 422
    completed: bool = False


class TaskCreate(TaskBase):
    """client never sends id - the DB owns it."""

class TaskUpdate(BaseModel):
    task_name : str | None = Field(default=None,min_length=1, max_length=100)
    deadline : date | None = None
    completed: bool | None = None


class TaskOut(TaskBase):
    id : int
    model_config = ConfigDict(from_attributes=True) # lets FastAPI read an ORM object