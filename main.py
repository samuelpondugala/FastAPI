"""TaskManager - JSON API.

Two faces on one SQLite database:
  * this module  -> JSON API at /tasks   (for code, Postman, /docs)
  * web.py       -> HTML pages at /ui/tasks (for humans, via Jinja2 templates)
"""

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
import schemas
import web
from database import Base, engine, get_db

BASE_DIR = Path(__file__).resolve().parent

Base.metadata.create_all(bind=engine)   # creates tasks.db on first run

app = FastAPI(title="TaskManager API")

# Serve style.css. url_for('static', path='/style.css') in templates needs this.
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Attach the browser/HTML routes (all under /ui).
app.include_router(web.router)


@app.get("/", include_in_schema=False)
def get_root():
    """Send humans to the UI instead of a JSON greeting."""
    return RedirectResponse("/ui/tasks")


@app.get("/tasks", response_model=list[schemas.TaskOut])
def get_all_tasks(
    skip: int = 0,
    limit: int = Query(default=10, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(models.Task).offset(skip).limit(limit)
    return db.scalars(stmt).all()


@app.get("/tasks/{task_id}", response_model=schemas.TaskOut)
def get_task_with_id(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


@app.post("/tasks", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED)
def add_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    task = models.Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)        # pulls the generated id back from SQLite
    return task


@app.put("/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: int,
    payload: schemas.TaskCreate,          # PUT = full replacement
    db: Session = Depends(get_db),
):
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    for field, value in payload.model_dump().items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@app.patch("/tasks/{task_id}", response_model=schemas.TaskOut)
def patch_task(
    task_id: int,
    payload: schemas.TaskUpdate,          # PATCH = partial
    db: Session = Depends(get_db),
):
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    db.delete(task)
    db.commit()
    return None     # 204 must have no body