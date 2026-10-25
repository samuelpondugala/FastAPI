"""HTML (browser) routes for the Task Manager.

Why a separate module from the JSON API in main.py?

An HTML <form> can only send GET and POST, and it sends
"application/x-www-form-urlencoded" instead of JSON. So the browser cannot
reuse the PUT/PATCH/DELETE JSON endpoints. Instead we expose a parallel set of
GET/POST routes that talk to the *same* database through the same get_db()
dependency and the same models.Task table.

After every write we reply with a 303 redirect back to the table. This is the
"POST / Redirect / GET" pattern: it leaves the browser sitting on a plain GET,
so pressing F5 does not re-submit the form.
"""

from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
from database import get_db

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

router = APIRouter(prefix="/ui", tags=["web"])


@router.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request, db: Session = Depends(get_db)):
    """The table page, with the 'add task' form on top."""
    tasks = db.scalars(select(models.Task).order_by(models.Task.deadline)).all()
    # "request" is required by Jinja2Templates so url_for() works in templates.
    return templates.TemplateResponse(
        request=request,
        name="tasks.html",
        context={"tasks": tasks},
    )


@router.post("/tasks")
def create_task_form(
    task_name: str = Form(..., min_length=1, max_length=100),
    deadline: date = Form(...),  # <input type="date"> sends "2026-11-01"
    db: Session = Depends(get_db),
):
    db.add(models.Task(task_name=task_name, deadline=deadline, completed=False))
    db.commit()
    return RedirectResponse("/ui/tasks", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
def edit_page(task_id: int, request: Request, db: Session = Depends(get_db)):
    """A form pre-filled with the current values of one task."""
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    return templates.TemplateResponse(
        request=request,
        name="edit.html",
        context={"task": task},
    )


@router.post("/tasks/{task_id}/edit")
def edit_task_form(
    task_id: int,
    task_name: str = Form(..., min_length=1, max_length=100),
    deadline: date = Form(...),
    # An unchecked checkbox sends NOTHING at all, so a default is mandatory
    # here - without it unchecking the box would produce a 422.
    completed: bool = Form(False),
    db: Session = Depends(get_db),
):
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    task.task_name = task_name
    task.deadline = deadline
    task.completed = completed
    db.commit()
    return RedirectResponse("/ui/tasks", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/tasks/{task_id}/toggle")
def toggle_task(task_id: int, db: Session = Depends(get_db)):
    """Flip 'completed' straight from the table row."""
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    task.completed = not task.completed
    db.commit()
    return RedirectResponse("/ui/tasks", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/tasks/{task_id}/delete")
def delete_task_form(task_id: int, db: Session = Depends(get_db)):
    """POST, not GET: a plain <a href> could be fired by a prefetch/crawler."""
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    db.delete(task)
    db.commit()
    return RedirectResponse("/ui/tasks", status_code=status.HTTP_303_SEE_OTHER)