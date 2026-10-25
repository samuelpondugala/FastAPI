# FastAPI Learning Repository — Full Documentation

This repository contains two FastAPI projects that build on each other:

| Project | Folder | What it teaches |
|---|---|---|
| **Hello_world** | `FASTAPI/Hello_world/` | The absolute basics: a FastAPI app, a Pydantic model, and CRUD against an in-memory Python list (data is lost on restart). |
| **Task_manager** | `FASTAPI/Task_manager/` | The "real" project: a JSON REST API **and** a server-rendered HTML UI, both backed by the same SQLite database through SQLAlchemy ORM, with Pydantic validation and Jinja2 templates. |

Everything below is documented line-by-line / symbol-by-symbol: every module, every
variable, every class, every function, every route ("view"), every page (template),
every CSS rule group, every dependency — and **why** each one exists.

---

## Table of contents

1. [Repository layout](#1-repository-layout)
2. [Core concepts & vocabulary (every keyword explained)](#2-core-concepts--vocabulary-every-keyword-explained)
3. [Project 1 — Hello_world](#3-project-1--hello_world)
4. [Project 2 — Task_manager](#4-project-2--task_manager)
   - [4.1 Architecture & request lifecycle](#41-architecture--request-lifecycle)
   - [4.2 `database.py` — engine, session, dependency](#42-databasepy--engine-session-dependency)
   - [4.3 `models.py` — the ORM model (the database table)](#43-modelspy--the-orm-model-the-database-table)
   - [4.4 `schemas.py` — the Pydantic models (the API contract)](#44-schemaspy--the-pydantic-models-the-api-contract)
   - [4.5 `main.py` — the JSON API + app assembly](#45-mainpy--the-json-api--app-assembly)
   - [4.6 `web.py` — the HTML views (browser routes)](#46-webpy--the-html-views-browser-routes)
   - [4.7 Templates (the pages)](#47-templates-the-pages)
   - [4.8 `static/style.css` — the stylesheet](#48-staticstylecss--the-stylesheet)
   - [4.9 `.gitignore`](#49-gitignore)
5. [Complete route/endpoint reference](#5-complete-routeendpoint-reference)
6. [Dependencies — every package and why it is installed](#6-dependencies--every-package-and-why-it-is-installed)
7. [How to run both projects](#7-how-to-run-both-projects)
8. [Manual test recipes (curl)](#8-manual-test-recipes-curl)
9. [Design decisions & gotchas](#9-design-decisions--gotchas)
10. [Ideas for extension](#10-ideas-for-extension)
11. [Appendix A — every variable in the project](#11-appendix-a--every-variable-in-the-project)
12. [Appendix B — every imported symbol, method and attribute called](#12-appendix-b--every-imported-symbol-method-and-attribute-called)
13. [Appendix C — HTML elements & attributes glossary](#13-appendix-c--html-elements--attributes-glossary)
14. [Appendix D — CSS properties & colour palette glossary](#14-appendix-d--css-properties--colour-palette-glossary)

---

## 1. Repository layout

```
personell/
├── README.md                      <- this document
└── FASTAPI/
    ├── Hello_world/
    │   ├── main.py                <- single-file demo API ("teas")
    │   └── requirement.txt        <- pinned dependencies for this demo
    └── Task_manager/
        ├── .gitignore             <- keeps the SQLite file and caches out of git
        ├── database.py            <- engine + SessionLocal + Base + get_db()
        ├── models.py              <- SQLAlchemy ORM model: Task  -> table "tasks"
        ├── schemas.py             <- Pydantic models: TaskBase/Create/Update/Out
        ├── main.py                <- FastAPI app, JSON API at /tasks, mounts /static, includes web router
        ├── web.py                 <- APIRouter with HTML routes under /ui
        ├── requirement.txt        <- pinned dependencies
        ├── templates/
        │   ├── base.html          <- layout shell (header, <head>, blocks)
        │   ├── tasks.html         <- page: add-form + table of all tasks
        │   └── edit.html          <- page: pre-filled single-task edit form
        └── static/
            └── style.css          <- all styling (no framework, no JS build step)
        (tasks.db is created automatically at first run; it is git-ignored)
```

**Why this split?** Each file has exactly one responsibility:

- `database.py` = *how* we talk to the DB (connection + sessions).
- `models.py` = *what* the DB looks like (tables/columns).
- `schemas.py` = *what the outside world is allowed to send and receive*.
- `main.py` = JSON API + application wiring.
- `web.py` = HTML views for browsers.
- `templates/` + `static/` = presentation.

This is the standard FastAPI project shape. It keeps the storage layer swappable
(SQLite → Postgres) and keeps API validation independent of table structure.

---

## 2. Core concepts & vocabulary (every keyword explained)

### Python / language keywords used in this repo

| Keyword / syntax | Where used | Meaning & why |
|---|---|---|
| `from X import Y` | all modules | Imports only the needed names, so the code reads `select(...)` instead of `sqlalchemy.select(...)`. |
| `import models`, `import schemas`, `import web` | `main.py` | Module-level imports so we can write `models.Task`, `schemas.TaskOut`. Keeps the origin of a name obvious. These are **flat/absolute imports**, which is why the app must be started *from inside* `Task_manager/`. |
| `class X(Y):` | models, schemas | Class definition with inheritance. `Task(Base)` makes a mapped ORM class; `TaskOut(TaskBase)` reuses fields. |
| `def` | every route & helper | Defines a normal (synchronous) function. FastAPI runs `def` endpoints in a **threadpool**, which is correct here because SQLAlchemy's classic `Session` is blocking/synchronous. (If we had used `async def` with a blocking DB call, we would block the event loop.) |
| `return` | routes | Produces the response body. FastAPI serializes dicts/lists/Pydantic/ORM objects to JSON automatically. |
| `yield` | `get_db()` | Makes `get_db` a **generator dependency**. Code before `yield` runs before the request handler, code after `yield` (here the `finally:` block) runs after the response — the standard FastAPI setup/teardown pattern. |
| `try: / finally:` | `get_db()` | Guarantees `db.close()` runs even if the endpoint raises, so connections are never leaked. |
| `raise` | routes | Used with `HTTPException` to abort the request and return an error status instead of a normal body. |
| `None` | schemas, routes | Python's null. In `str \| None` it marks a field as optional; `if task is None:` is the identity check used to detect "row not found". |
| `is` | `if task is None` | Identity comparison. Preferred over `== None` and safe even if a model defined a weird `__eq__`. |
| `not` | `task.completed = not task.completed` | Boolean negation — the whole implementation of "toggle". |
| `for ... in ...` | `main.py` update/patch, `Hello_world` | Loop. In `update_task`/`patch_task` it iterates the validated payload's fields to copy them onto the ORM object. |
| `enumerate` | `Hello_world/main.py` | Gives `(index, item)` pairs so an item in a list can be replaced in place or popped by index. |
| `else` on a `for` (Jinja only) | `tasks.html` | Jinja2's `{% for %}...{% else %}` renders the `else` branch when the sequence is empty — used for the "No tasks yet" row. (Note: Python's `for/else` has different semantics; this one is a Jinja feature.) |
| `f"{...}"` | `Hello_world/main.py` | f-string interpolation for the confirmation messages. |
| `**payload.model_dump()` | `main.py` `add_task` | Dict unpacking into keyword arguments: `models.Task(task_name=..., deadline=..., completed=...)`. Short, and it automatically follows the schema's fields. |
| `list[schemas.TaskOut]` | `main.py` | Built-in generic typing (Python 3.9+). Declares "a JSON array of TaskOut objects" to FastAPI and to OpenAPI. |
| `str \| None` | `schemas.py` | PEP 604 union syntax (Python 3.10+) = `Optional[str]`. Used for PATCH fields that may be omitted. |
| `List[Tea]` from `typing` | `Hello_world/main.py` | The older generic form; kept there to show the historic style. |
| `@decorator` | everywhere | `@app.get(...)`, `@router.post(...)` register a function as a route; the decorator reads the function's type hints to build validation and docs. |
| Type hints (`task_id: int`) | routes | Not just documentation: FastAPI **uses** them to parse/validate/convert input and to generate OpenAPI. `task_id: int` turns `/tasks/abc` into an automatic `422`. |
| Default values (`skip: int = 0`) | routes | A defaulted scalar parameter that is not in the path becomes an optional **query parameter**. |
| Docstrings (`"""..."""`) | modules & functions | Module docstrings explain architecture; endpoint docstrings are picked up by FastAPI and shown as the endpoint description in `/docs`. |

### Web / HTTP vocabulary

| Term | Why it matters here |
|---|---|
| **REST** | Resource-oriented URL design: a collection `/tasks` and items `/tasks/{id}`; the HTTP verb expresses the action. |
| **GET** | Read. Safe and idempotent, may be cached/prefetched — which is exactly why delete is *not* a GET in `web.py`. |
| **POST** | Create (or, in the HTML UI, "do a write" generally, because forms only support GET/POST). |
| **PUT** | Full replacement of a resource. In `main.py` it takes `TaskCreate`, so **all** fields must be sent. |
| **PATCH** | Partial update. In `main.py` it takes `TaskUpdate` (all fields optional) and uses `exclude_unset=True`. |
| **DELETE** | Remove a resource; returns `204 No Content`. |
| **201 Created** | Returned by `POST /tasks` to signal a new resource was created. |
| **204 No Content** | Returned by `DELETE /tasks/{id}`. The response **must not** have a body, hence `return None`. |
| **303 See Other** | Returned after every HTML form write. It tells the browser "now do a GET on this other URL", which implements **POST/Redirect/GET** so refreshing the page doesn't resubmit the form. 303 (not 302) guarantees the follow-up request is a GET. |
| **404 Not Found** | Raised via `HTTPException` when `db.get(...)` returns `None`. |
| **422 Unprocessable Entity** | FastAPI's automatic validation error (bad date, missing field, empty name, non-integer id). You never write this yourself. |
| **`application/x-www-form-urlencoded`** | What an HTML `<form>` sends. Parsed by `python-multipart` and received with `Form(...)` — *not* with a Pydantic body model. |
| **Query parameter** | `?skip=0&limit=10` on `GET /tasks`, used for pagination. |
| **Path parameter** | `{task_id}` in the URL, typed as `int`. |
| **Dependency injection** | `db: Session = Depends(get_db)`: FastAPI builds the value, injects it, and cleans it up. Keeps session management out of every endpoint. |
| **OpenAPI / Swagger UI / ReDoc** | Auto-generated schema at `/openapi.json`, interactive docs at `/docs`, reference docs at `/redoc`. Generated *from your type hints* — the main reason FastAPI was chosen. |
| **ASGI** | The async server interface FastAPI speaks; `uvicorn` is the ASGI server that actually listens on the socket. |
| **ORM** | Object-Relational Mapper. SQLAlchemy lets us use `models.Task` Python objects instead of hand-written SQL strings. |

---

## 3. Project 1 — Hello_world

File: `FASTAPI/Hello_world/main.py`

A deliberately minimal CRUD API over a Python list. **No database** — restarting the
server empties the data. Its only job is to show the shape of a FastAPI app.

### Imports

| Import | Why |
|---|---|
| `from fastapi import FastAPI` | The application class. |
| `from pydantic import BaseModel` | Base class for request/response data models with validation. |
| `from typing import List` | Older generic syntax used to annotate the storage list. |

### Variables

| Name | Type | Purpose |
|---|---|---|
| `app` | `FastAPI` | The application instance. Every `@app.<verb>` decorator registers onto it; `uvicorn main:app` looks for exactly this name. |
| `teas` | `List[Tea]` | In-memory "database". A module-level list, so it lives as long as the process. |

### Model (class)

```python
class Tea(BaseModel):
    id: int
    name: str
    origin: str
```

- **`Tea`** — a Pydantic model used **both** as the request body schema and as the
  stored object. All three fields are required.
- `id: int` — client-supplied here (contrast with `Task_manager`, where the DB owns the id).
- `name: str`, `origin: str` — required strings.
- Because it's a Pydantic model, a bad payload (e.g. `id: "abc"`) is rejected with a
  `422` before your function ever runs.

### Functions (views)

| Function | Route | Behaviour |
|---|---|---|
| `read_root()` | `GET /` | Returns `{"message": "Welcome to Chai Code"}` — a liveness/greeting endpoint. |
| `get_teas()` | `GET /teas` | Returns the whole `teas` list. FastAPI serializes each `Tea` to JSON. |
| `add_tea(tea: Tea)` | `POST /teas` | The `tea` parameter is a Pydantic model, so FastAPI reads it from the **JSON body**. Appends it and returns a confirmation string. |
| `update_tea(tea_id: int, updated_tea: Tea)` | `PUT /teas/{tea_id}` | Linear scan with `enumerate`; replaces the matching element. Returns `{"error": ...}` if not found. |
| `delete_tea(tea_id: int)` | `DELETE /teas/{tea_id}` | Linear scan, `teas.pop(index)`, returns a confirmation string. |

**Known teaching limitations (fixed in Task_manager):** the "not found" cases return
`200` with an error dict instead of a real `404`; the list is `O(n)` and not persistent;
duplicate ids are possible. `Task_manager` solves all three with SQLite + `HTTPException`.

---

## 4. Project 2 — Task_manager

### 4.1 Architecture & request lifecycle

One database, **two faces**:

```
  curl / Postman     +------------------------------+
  /docs          --> |  main.py   JSON API  /tasks  | --+
                     +------------------------------+   |
                                                        +--> get_db() --> SessionLocal --> engine --> tasks.db
  Browser            +------------------------------+   |                                      ^
  (HTML forms)   --> |  web.py    HTML UI   /ui/... | --+                                      |
                     +---------------+--------------+                           models.Task ---+
                                     | renders
                     templates/base.html + tasks.html / edit.html
                                     | styled by
                                 static/style.css
```

**Lifecycle of `GET /ui/tasks`:**

1. Uvicorn receives the HTTP request and hands an ASGI scope to FastAPI/Starlette.
2. The router matches the path to `web.tasks_page`.
3. FastAPI resolves dependencies: it runs `get_db()` up to its `yield`, producing a `Session`.
4. `tasks_page` runs `SELECT * FROM tasks ORDER BY deadline` and gets ORM `Task` objects.
5. `Jinja2Templates.TemplateResponse` renders `tasks.html` (which `extends base.html`) to HTML.
6. The response is returned; `get_db()` resumes past the `yield` and closes the session.
7. The browser then requests `/static/style.css`, served by `StaticFiles`.

**Lifecycle of a form write, e.g. "Delete":**

`POST /ui/tasks/3/delete` → row deleted + `db.commit()` → `303` to `/ui/tasks` →
browser issues a fresh `GET /ui/tasks` → table re-rendered without row 3.

---

### 4.2 `database.py` — engine, session, dependency

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine(
    "sqlite:///./tasks.db",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    """One session per request, always closed afterwards"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

| Symbol | Type | Explanation / why |
|---|---|---|
| `create_engine` | function | Creates the central SQLAlchemy object that owns the DBAPI connection pool and the SQL dialect. Called **once** per process — creating engines per request would destroy pooling. |
| `"sqlite:///./tasks.db"` | connection URL | `sqlite` = dialect; `///` = relative path; `./tasks.db` = a file in the **current working directory**. SQLite is chosen because it needs zero setup — no server, no credentials. Swapping to Postgres means changing only this one string. |
| `connect_args={"check_same_thread": False}` | dict | SQLite normally refuses to let a connection be used from a thread other than the one that created it. FastAPI runs `def` endpoints in a threadpool, so the connection legitimately moves between threads. Disabling the check is the standard, documented FastAPI+SQLite combination (safe here because each request still uses its own `Session`). |
| `engine` | `Engine` | The shared connection factory, imported by `main.py` to run `create_all`. |
| `sessionmaker(...)` | factory | Produces a configured `Session` class. We store the **factory**, not a session, so each request can cheaply create its own. |
| `autocommit=False` | flag | Writes are only persisted when you call `db.commit()`. Gives you explicit transactions: several `add`/`delete` calls can succeed or fail as a unit. |
| `autoflush=False` | flag | SQLAlchemy won't silently emit pending INSERT/UPDATEs before every query. Makes the exact moment SQL runs predictable (important while learning, and avoids surprise constraint errors mid-query). |
| `SessionLocal` | session factory | Named by convention (FastAPI docs) to distinguish it from SQLAlchemy's `Session` class. |
| `declarative_base()` | function | Returns the base class that collects table metadata from subclasses. |
| `Base` | class | Parent of every ORM model. `Base.metadata` holds all table definitions, which is how `Base.metadata.create_all()` can create them. |
| `get_db` | generator function | The **dependency**. `SessionLocal()` opens a session, `yield db` hands it to the endpoint, and `finally: db.close()` returns the connection to the pool no matter what happened. One session per request = no state leaking between users. |

**Why a separate `database.py`?** Both `main.py` and `web.py` need `get_db`, and
`models.py` needs `Base`. Putting them here avoids circular imports and gives a
single place to change the database.

---

### 4.3 `models.py` — the ORM model (the database table)

```python
from sqlalchemy import Boolean, Column, Date, Integer, String
from database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(100), nullable=False)
    deadline = Column(Date, nullable=False)
    completed = Column(Boolean, nullable=False, default=False)
```

| Symbol | Explanation / why |
|---|---|
| `Task` | The ORM **model** class. One instance = one row. Inheriting `Base` registers it in `Base.metadata` so the table can be auto-created. |
| `__tablename__ = "tasks"` | Required by SQLAlchemy's declarative system: the physical table name. Plural table name, singular class name — the usual convention. |
| `Column` | Declares a mapped column; also acts as a descriptor so `models.Task.deadline` can be used in queries (`order_by(models.Task.deadline)`). |
| `id = Column(Integer, primary_key=True, index=True)` | The surrogate primary key. In SQLite an `INTEGER PRIMARY KEY` is an alias for `ROWID`, so it **autoincrements** — the client never supplies it (that's why `TaskCreate` has no `id`). `index=True` is redundant for a PK but harmless and explicit about lookup intent. |
| `task_name = Column(String(100), nullable=False)` | The task text. Length `100` documents intent and is enforced by other databases (SQLite ignores the length — which is exactly why `schemas.py` also caps it at `max_length=100`: **validate at the edge, don't trust the DB alone**). `nullable=False` = `NOT NULL`. |
| `deadline = Column(Date, nullable=False)` | Stored as a real date, **not** a string. Consequences: SQLAlchemy returns a Python `datetime.date`, so templates can call `task.deadline.strftime(...)` / `.isoformat()`, and `ORDER BY deadline` sorts chronologically instead of alphabetically. |
| `completed = Column(Boolean, nullable=False, default=False)` | Done flag. `default=False` is a **Python-side default** applied on INSERT when the attribute wasn't set, so the column is never `NULL` and the UI never has to handle three states. |

---

### 4.4 `schemas.py` — the Pydantic models (the API contract)

```python
from datetime import date
from pydantic import BaseModel, ConfigDict, Field

class TaskBase(BaseModel):
    task_name: str = Field(min_length=1, max_length=100)
    deadline: date          # "2026-10-25"; junk -> automatic 422
    completed: bool = False

class TaskCreate(TaskBase):
    """client never sends id - the DB owns it."""

class TaskUpdate(BaseModel):
    task_name: str | None = Field(default=None, min_length=1, max_length=100)
    deadline: date | None = None
    completed: bool | None = None

class TaskOut(TaskBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
```

**Why separate "schemas" from "models"?** The ORM model describes *storage*; the
Pydantic schemas describe *the HTTP contract*. Keeping them apart lets you hide
internal columns, require different fields for create vs. update, and change the
database without breaking clients. It also means validation errors happen before
any SQL runs.

| Symbol | Explanation / why |
|---|---|
| `date` (from `datetime`) | The field type. Pydantic parses `"2026-10-25"` into a `date` and rejects `"tomorrow"` or `"2026-13-45"` with a `422` — zero hand-written validation. |
| `BaseModel` | Pydantic's base class: gives parsing, validation, serialization and JSON-Schema generation (which FastAPI turns into OpenAPI docs). |
| `Field(...)` | Attaches constraints/metadata to a field. |
| `min_length=1` | Blocks `""` as a task name. |
| `max_length=100` | Mirrors `String(100)` in the model, enforced here because SQLite does not enforce it. |
| `ConfigDict` | Pydantic v2's typed config object (replaces the old inner `class Config`). |
| `from_attributes=True` | **Key setting.** Lets Pydantic read values off arbitrary objects' attributes instead of requiring a dict. Without it, returning an ORM `Task` from an endpoint declared `response_model=TaskOut` would fail. (Pydantic v1 called this `orm_mode`.) |
| `TaskBase` | Holds the three fields shared by input and output. Written once, inherited — no duplication to drift out of sync. |
| `TaskCreate(TaskBase)` | The **POST/PUT request** schema. Deliberately identical to `TaskBase` and deliberately **without** `id`: the database generates ids, so accepting one from a client would be a bug/security hole. Existing as its own name means create-only rules can be added later without touching output. |
| `TaskUpdate` | The **PATCH** schema. Note it inherits `BaseModel`, *not* `TaskBase`, because every field must become optional (`\| None` + `default=None`). Combined with `model_dump(exclude_unset=True)` in the endpoint, this gives true partial updates: fields the client never mentioned are left untouched, and a field explicitly sent as `null` is distinguishable from an omitted one. |
| `TaskOut(TaskBase)` | The **response** schema: the three base fields **plus** `id`. Declaring it as `response_model` makes FastAPI filter/convert the ORM object and document the exact response shape. |
| `completed: bool = False` | Default on input, so clients can create a task with only name + deadline. |

**Field-by-field summary**

| Field | Type | Required? | Constraints | Appears in |
|---|---|---|---|---|
| `id` | `int` | output only | DB-generated | `TaskOut` |
| `task_name` | `str` | yes (optional in PATCH) | 1–100 chars | Base, Create, Update, Out |
| `deadline` | `date` | yes (optional in PATCH) | ISO `YYYY-MM-DD` | Base, Create, Update, Out |
| `completed` | `bool` | no (defaults `False`) | — | Base, Create, Update, Out |

---

### 4.5 `main.py` — the JSON API + app assembly

#### Module docstring
States the two-faces design: this module serves JSON at `/tasks`, `web.py` serves
HTML at `/ui/tasks`, both on one SQLite file.

#### Imports

| Import | Why |
|---|---|
| `Path` (pathlib) | Build paths relative to *this file*, not the shell's cwd. |
| `Depends` | Declare the `get_db` dependency. |
| `FastAPI` | The app class. |
| `HTTPException` | Raise `404`s. |
| `Query` | Attach validation to a query parameter (`le=100`). |
| `status` | Named constants (`HTTP_201_CREATED`) instead of magic numbers. |
| `RedirectResponse` | Send `/` to the UI. |
| `StaticFiles` | Serve `style.css`. |
| `select` (SQLAlchemy) | Build the 2.0-style `SELECT` statement. |
| `Session` | Type hint for the injected DB session (gives editor autocomplete and documents intent). |
| `models`, `schemas`, `web` | The project's own modules. |
| `Base, engine, get_db` | Table creation + the request-scoped session dependency. |

#### Module-level variables / wiring

| Statement | Why |
|---|---|
| `BASE_DIR = Path(__file__).resolve().parent` | Absolute path to `Task_manager/`. `__file__` = this module's path, `.resolve()` makes it absolute and symlink-free, `.parent` strips the filename. Used so `static/` is found regardless of the working directory. |
| `Base.metadata.create_all(bind=engine)` | Issues `CREATE TABLE IF NOT EXISTS` for every model registered on `Base`. Creates `tasks.db` on first run — zero-setup bootstrapping. (It does **not** alter existing tables; for real schema evolution you'd add Alembic migrations.) |
| `app = FastAPI(title="TaskManager API")` | The application. `title` shows up as the heading in `/docs` and in `openapi.json`. |
| `app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")` | Mounts a sub-application that serves files from disk. `name="static"` is what makes `url_for('static', path='/style.css')` work inside the Jinja templates — that's the whole reason the name is given. |
| `app.include_router(web.router)` | Copies all HTML routes from `web.py` into the app (keeping their `/ui` prefix and `web` tag). This is how the two modules become one server. |

#### Endpoints (views)

**`get_root()` — `GET /`**
```python
@app.get("/", include_in_schema=False)
def get_root():
    return RedirectResponse("/ui/tasks")
```
- Redirects the site root to the HTML UI so a human who types the bare URL lands on
  something useful instead of a JSON blob.
- `include_in_schema=False` hides this plumbing route from `/docs`.
- Default redirect status is `307`, which is fine for a GET→GET hop.

**`get_all_tasks()` — `GET /tasks`**
```python
@app.get("/tasks", response_model=list[schemas.TaskOut])
def get_all_tasks(skip: int = 0, limit: int = Query(default=10, le=100),
                  db: Session = Depends(get_db)):
    stmt = select(models.Task).offset(skip).limit(limit)
    return db.scalars(stmt).all()
```
| Element | Why |
|---|---|
| `response_model=list[schemas.TaskOut]` | Documents and enforces a JSON array of tasks; converts ORM rows via `from_attributes`. |
| `skip: int = 0` | Query param = pagination offset ("how many rows to jump over"). |
| `limit: int = Query(default=10, le=100)` | Page size, **hard-capped at 100** (`le` = less-than-or-equal). Protects the server from `?limit=10000000`; violations become automatic `422`s. |
| `select(models.Task)` | SQLAlchemy 2.0 statement style (the modern replacement for `db.query(...)`). |
| `.offset(skip).limit(limit)` | Translates to SQL `OFFSET`/`LIMIT` — paging happens in the database, not in Python. |
| `db.scalars(stmt)` | Returns the first column of each row, i.e. actual `Task` objects rather than 1-tuples. |
| `.all()` | Materializes the result into a list. |

**`get_task_with_id()` — `GET /tasks/{task_id}`**
- `db.get(models.Task, task_id)` is the fastest primary-key lookup and can even be
  served from the session's identity map.
- `if task is None: raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")` —
  a genuine `404` with a JSON `{"detail": "Task not found"}` body.

**`add_task()` — `POST /tasks` → `201`**
| Line | Why |
|---|---|
| `payload: schemas.TaskCreate` | A Pydantic model parameter ⇒ FastAPI reads the **JSON body** and validates it. |
| `status_code=status.HTTP_201_CREATED` | Correct REST semantics for "resource created". |
| `models.Task(**payload.model_dump())` | `model_dump()` (Pydantic v2; v1's `.dict()`) → plain dict → unpacked into the ORM constructor. |
| `db.add(task)` | Stages the INSERT in the session. |
| `db.commit()` | Writes it to SQLite and ends the transaction. |
| `db.refresh(task)` | Re-SELECTs the row to pull back DB-generated values — here the new `id`. Without it, `task.id` would be expired/unset and the response couldn't include it. |

**`update_task()` — `PUT /tasks/{task_id}`**
- Takes `TaskCreate`, so **all** fields are required: PUT means *full replacement*.
- `for field, value in payload.model_dump().items(): setattr(task, field, value)` —
  copies every field generically. Adding a new column later requires no change here.
- `db.commit()` then `db.refresh(task)` to return the stored state.
- `404` if the id doesn't exist (this implementation does not "upsert").

**`patch_task()` — `PATCH /tasks/{task_id}`**
- Takes `TaskUpdate`, so every field is optional.
- `payload.model_dump(exclude_unset=True)` is the heart of PATCH: it returns **only the
  keys the client actually sent**, so omitted fields are not overwritten with `None`.
- Everything else mirrors `update_task`.

**`delete_task()` — `DELETE /tasks/{task_id}` → `204`**
- `404` if missing, otherwise `db.delete(task)` + `db.commit()`.
- `status_code=status.HTTP_204_NO_CONTENT` and `return None` because a `204` response
  must have an empty body.

---

### 4.6 `web.py` — the HTML views (browser routes)

#### Why this module exists (from its docstring)
An HTML `<form>` can only issue **GET** and **POST**, and it submits
`application/x-www-form-urlencoded`, not JSON. A browser therefore *cannot* use the
JSON `PUT`/`PATCH`/`DELETE` endpoints without JavaScript. So `web.py` exposes a
parallel set of GET/POST routes that hit the **same** `get_db()` dependency and the
**same** `models.Task` table. After every write it answers with a `303` redirect
(POST/Redirect/GET) so pressing F5 never re-submits the form.

#### Imports and module variables

| Symbol | Why |
|---|---|
| `date` | Type hint for the `deadline` form field, so `"2026-11-01"` is converted/validated automatically. |
| `Path` | For `BASE_DIR`. |
| `APIRouter` | Groups related routes in their own module; included into the app later. Keeps `main.py` from becoming a 500-line file. |
| `Form` | Marks a parameter as coming from an urlencoded form body (requires `python-multipart`). |
| `Request` | Starlette's request object — **required** by `Jinja2Templates` so `url_for()` works inside templates. |
| `HTMLResponse` | Used as `response_class` so `/docs` and the `Content-Type` header say `text/html`, not JSON. |
| `RedirectResponse` | Implements the post-write redirect. |
| `Jinja2Templates` | Starlette's integration of the Jinja2 template engine. |
| `select`, `Session` | Query building + type hint. |
| `models`, `get_db` | Shared table and shared session dependency — the two faces really do share one database. |
| `BASE_DIR = Path(__file__).resolve().parent` | So templates are found no matter where the server was started. |
| `templates = Jinja2Templates(directory=BASE_DIR / "templates")` | The renderer. Created once at import time (compiling the environment per request would be wasteful). |
| `router = APIRouter(prefix="/ui", tags=["web"])` | `prefix="/ui"` means every route below is automatically under `/ui`, which cleanly separates HTML URLs from the JSON `/tasks` URLs (no collisions). `tags=["web"]` groups them in `/docs`. |

#### Views (pages & actions)

**`tasks_page()` — `GET /ui/tasks` → renders `tasks.html`**
```python
tasks = db.scalars(select(models.Task).order_by(models.Task.deadline)).all()
return templates.TemplateResponse(request=request, name="tasks.html",
                                  context={"tasks": tasks})
```
- `order_by(models.Task.deadline)` — soonest deadline first. Works correctly because
  `deadline` is a real `Date` column.
- No pagination here (unlike the JSON API) — the page intentionally shows everything.
- `request=request` is mandatory for `url_for()` in `base.html`.
- `context={"tasks": tasks}` is the dict of variables the template can see; inside
  `tasks.html` it is simply `tasks`.
- `TemplateResponse` renders the template to a `text/html` response.

**`create_task_form()` — `POST /ui/tasks`**
| Element | Why |
|---|---|
| `task_name: str = Form(..., min_length=1, max_length=100)` | Reads the form field; `...` (Ellipsis) means **required**; the constraints duplicate the Pydantic/DB rules so the HTML path is validated too (browser `required`/`maxlength` attributes are only a convenience and can be bypassed). |
| `deadline: date = Form(...)` | `<input type="date">` submits `YYYY-MM-DD`, which converts straight into a `date`. |
| `models.Task(..., completed=False)` | New tasks always start unfinished; the add-form has no checkbox. |
| `RedirectResponse("/ui/tasks", status_code=303)` | POST/Redirect/GET. |

**`edit_page()` — `GET /ui/tasks/{task_id}/edit` → renders `edit.html`**
- Loads one task with `db.get`, `404`s if absent, and passes it to the template as
  `task` so the form can be **pre-filled** with current values.

**`edit_task_form()` — `POST /ui/tasks/{task_id}/edit`**
| Element | Why |
|---|---|
| `completed: bool = Form(False)` | **Critical detail:** an unchecked checkbox sends *nothing at all*. Without the `False` default, unchecking the box would make the field missing and produce a `422`. The default turns "absent" into "not completed". |
| `task.task_name = ... / task.deadline = ... / task.completed = ...` | Explicit assignment. SQLAlchemy's change tracking turns this into an `UPDATE`. |
| `db.commit()` | Persist. (No `refresh` needed — we redirect instead of returning the object.) |
| `303` redirect | Back to the table. |

**`toggle_task()` — `POST /ui/tasks/{task_id}/toggle`**
- `task.completed = not task.completed` — one-click done/undone directly from a table row,
  without opening the edit page.
- POST (not GET) because it **changes state**; GETs must stay safe.

**`delete_task_form()` — `POST /ui/tasks/{task_id}/delete`**
- Docstring says it all: *"POST, not GET: a plain `<a href>` could be fired by a
  prefetch/crawler."* Making deletion a POST prevents accidental destruction by
  browser prefetching, link scanners, or a stray bookmark.
- `404` if missing, else `db.delete` + `commit` + `303`.

---

### 4.7 Templates (the pages)

Jinja2 syntax used in this project:

| Syntax | Meaning |
|---|---|
| `{{ ... }}` | Print an expression. **Auto-escaped**, so a task named `<script>alert(1)</script>` renders as harmless text — built-in XSS protection. |
| `{% ... %}` | A statement/tag: `extends`, `block`, `for`, `if`. |
| `{# ... #}` | A template comment; never sent to the browser. |
| `{% extends "base.html" %}` | Template inheritance: this page fills in the parent's blocks. |
| `{% block name %}...{% endblock %}` | A named, overridable region. Write the HTML shell once, override only `title` and `content`. |
| `{% for x in seq %}...{% else %}...{% endfor %}` | Loop with an empty-sequence fallback branch. |
| `{{ 'a' if cond else 'b' }}` | Inline conditional expression. |
| `{% if cond %}...{% endif %}` | Conditional block. |
| `{{ seq \| length }}` | A **filter** — here the count of tasks. |
| `{{ url_for('static', path='/style.css') }}` | Starlette-provided helper that builds the URL for the mounted `static` app. Used instead of a hard-coded `/static/...` so the mount point can change safely. |

#### `templates/base.html` — the layout shell

| Part | Why |
|---|---|
| `<!DOCTYPE html>` / `<html lang="en">` | Standards mode; `lang` helps screen readers and translation. |
| `<meta charset="utf-8">` | Correct rendering of any non-ASCII task name. |
| `<meta name="viewport" content="width=device-width, initial-scale=1">` | Makes the page usable on phones instead of zoomed-out desktop width. |
| `<title>{% block title %}Task Manager{% endblock %}</title>` | Overridable per page, with a sensible default. |
| `<link rel="stylesheet" href="{{ url_for('static', path='/style.css') }}">` | Pulls in the single stylesheet via the named mount. |
| `<header>` with `<h1><a href="/ui/tasks">Task Manager</a></h1>` | A persistent "home" link back to the table. |
| `<nav><a href="/docs">JSON API docs</a></nav>` | Direct link from the UI to Swagger — makes the "two faces" idea discoverable. |
| `<main>{% block content %}{% endblock %}</main>` | Where each child page injects its body. `<main>` is the semantic landmark element. |

#### `templates/tasks.html` — page: list + add

| Part | Why |
|---|---|
| `{% extends "base.html" %}` | Reuse the shell. |
| `{% block title %}All tasks - Task Manager{% endblock %}` | Page-specific tab title. |
| First `<section>` — "Add a task" | `<form action="/ui/tasks" method="post" class="card">` posts to `create_task_form`. `method="post"` because it writes. |
| `<input type="text" name="task_name" required maxlength="100" placeholder="e.g. learn Jinja2">` | `name` must match the `Form` parameter name in `web.py`. `required`/`maxlength` give instant browser feedback (server still re-validates). `placeholder` shows an example. |
| `<input type="date" name="deadline" required>` | Gives a native date picker **and** guarantees `YYYY-MM-DD` on the wire, which is exactly what Pydantic's `date` wants. |
| `<button type="submit">Add task</button>` | Submits the form. |
| `<h2>All tasks ({{ tasks \| length }})</h2>` | Live count of rows. |
| `<table>` / `<thead>` / `<tbody>` | Tabular data in a real table: semantic and accessible. Columns: ID, Task, Deadline, Done, Actions. |
| `{% for task in tasks %}` | One `<tr>` per task. |
| `<tr class="{{ 'done' if task.completed else '' }}">` | Adds the `done` class so CSS can grey out and strike through finished tasks — styling driven by data. |
| `{{ task.id }}` / `{{ task.task_name }}` | Printed with auto-escaping (see the template comment about `<script>`). |
| `{{ task.deadline.strftime('%d %b %Y') }}` | Human-friendly "01 Nov 2026". Possible only because `deadline` is a real `date`. |
| `{{ "Yes" if task.completed else "No" }}` | Readable boolean instead of `True`/`False`. |
| `<td class="actions">` | Holds three controls per row. |
| Toggle form → `POST /ui/tasks/{{ task.id }}/toggle` | Tiny one-button form; POST because it mutates. |
| `<a href="/ui/tasks/{{ task.id }}/edit">Edit</a> ` | A link, because opening the edit page is a safe read-only GET. |
| Delete form → `POST .../delete` with `onsubmit="return confirm('Delete task {{ task.id }}?');"` | The only JavaScript in the project: a confirmation guard against accidental deletes. Returning `false` cancels submission. |
| `{% else %}<td colspan="5" class="empty">No tasks yet. Add one above.</td>` | Friendly empty state spanning all five columns, instead of a bare table. |

#### `templates/edit.html` — page: edit one task

| Part | Why |
|---|---|
| `{% block title %}Edit task #{{ task.id }} - Task Manager{% endblock %}` | Shows which task you're editing in the tab title. |
| `<form action="/ui/tasks/{{ task.id }}/edit" method="post" class="card">` | Posts to `edit_task_form` for this specific id. |
| `<input type="text" name="task_name" value="{{ task.task_name }}" required maxlength="100">` | Pre-filled with the current name via `value`. |
| `<input type="date" name="deadline" value="{{ task.deadline.isoformat() }}" required>` | **`.isoformat()`, not `.strftime('%d %b %Y')`.** `<input type="date">` only accepts `YYYY-MM-DD`; any other format makes the field render **empty** with no error — the "classic silent bug" called out in the template comment. |
| `<label class="inline"><input type="checkbox" name="completed" value="true" {% if task.completed %}checked{% endif %}>` | Checkbox reflecting current state. `value="true"` is what gets submitted when checked (parsed into `True`); when unchecked **nothing** is sent — which is why `web.py` uses `Form(False)`. `{% if %}checked{% endif %}` pre-checks it. `class="inline"` lays the label out horizontally. |
| `<button type="submit">Save</button>` | Submits the update. |
| `<a href="/ui/tasks" class="cancel">Cancel</a>` | A plain GET link back to the table — leaving a form must never write anything. |

---

### 4.8 `static/style.css` — the stylesheet

Hand-written CSS (no Bootstrap/Tailwind) so there is no build step and every rule is
explainable. Served by the `StaticFiles` mount at `/static`.

| Selector / rule group | What it does and why |
|---|---|
| `* { box-sizing: border-box; }` | Makes `width` include padding and border, so inputs and cells never overflow unexpectedly. The standard CSS reset line. |
| `body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }` | Uses the OS's native UI font — zero webfont download, looks native on Windows/macOS/Linux. |
| `body { margin: 2rem auto; padding: 0 1rem; max-width: 900px; }` | `auto` horizontal margin centers the page; `max-width` keeps lines readable; `padding` prevents text touching screen edges on mobile. |
| `body { color: #222; line-height: 1.5; }` | Soft black (less harsh than pure `#000`) and comfortable line spacing. |
| `header { display: flex; justify-content: space-between; align-items: baseline; }` | Flexbox pushes the title left and the nav link right, aligned on the text baseline. |
| `header { border-bottom: 2px solid #e5e7eb; padding-bottom: .5rem; margin-bottom: 1.5rem; }` | A visual rule separating the header from the content. |
| `header h1 { margin: 0; font-size: 1.6rem; }` | Removes the browser's default `h1` margin so flex alignment stays predictable. |
| `header h1 a { color: #111; text-decoration: none; }` | Makes the clickable title look like a title, not a link. |
| `header nav a { font-size: .85rem; color: #2563eb; }` | Small, blue, obviously a link (blue `#2563eb` is the project's accent colour). |
| `h2 { font-size: 1.1rem; margin: 1.5rem 0 .5rem; }` | Consistent section headings with breathing room above. |
| `.card { display: flex; gap: 1rem; align-items: flex-end; flex-wrap: wrap; }` | The form container: fields sit in a row, aligned on their bottom edge so labels stack above inputs and the button lines up; `flex-wrap` lets it reflow on narrow screens. |
| `.card { background: #f7f7f9; border: 1px solid #e5e7eb; padding: 1rem; border-radius: 8px; }` | Gives the form a light "panel" look that separates input from the data table. |
| `label { display: flex; flex-direction: column; gap: .25rem; }` | Stacks the caption above its input; wrapping the input inside `<label>` also makes the caption clickable (accessibility). |
| `label { font-size: .8rem; font-weight: 600; color: #4b5563; }` | Small, semi-bold, grey captions — secondary to the values. |
| `label.inline { flex-direction: row; align-items: center; gap: .4rem; }` | Override used by the "Completed" checkbox, where the box belongs *beside* the text. |
| `input[type="text"], input[type="date"] { padding/border/border-radius }` | Consistent, comfortable field styling across both input types. |
| `... { font: inherit; font-weight: 400; }` | Inputs otherwise use a tiny default browser font; `inherit` takes the body font, and `400` undoes the label's bold weight. |
| `input[type="text"] { min-width: 15rem; }` | Keeps the task-name field wide enough for a real sentence. |
| `button { padding/border:0/border-radius/background:#2563eb/color:#fff/font: inherit/cursor: pointer }` | The primary button: accent background, white text, inherited font, and a pointer cursor so it feels clickable. |
| `button:hover { filter: brightness(1.1); }` | One-line hover feedback that works for *every* button colour — no extra hover rule per variant. |
| `button.danger { background: #dc2626; }` | Red = destructive (Delete). Colour carries meaning. |
| `button.subtle { background: #64748b; }` | Grey = secondary action (Toggle), so it doesn't compete with "Add task". |
| `.cancel { font-size: .85rem; color: #6b7280; }` | The edit page's Cancel link: visibly de-emphasised. |
| `table { width: 100%; border-collapse: collapse; margin-top: .5rem; }` | Full-width table; `collapse` merges double borders into single clean lines. |
| `th, td { text-align: left; padding: .6rem .5rem; border-bottom: 1px solid #eee; vertical-align: middle; }` | Left-aligned readable columns, row separators, and vertically centred content. |
| `th { background: #f1f5f9; font-size: .8rem; text-transform: uppercase; letter-spacing: .03em; color: #475569; }` | A clearly distinct header row: tinted, small caps-style, slightly tracked out. |
| `tbody tr:hover { background: #fafafa; }` | Row highlight that helps you track which row's buttons you are about to press. |
| `tr.done td { color: #9ca3af; text-decoration: line-through; }` | The payoff of `class="{{ 'done' if task.completed }}"` in `tasks.html`: completed tasks are greyed and struck through at a glance. |
| `td.actions { display: flex; gap: .5rem; align-items: center; }` | Lays the Toggle / Edit / Delete controls out horizontally with even spacing. |
| `td.actions form { margin: 0; display: inline; }` | Each action is its own `<form>`; without this, default form margins would make the row tall and the buttons stack. |
| `td.actions button { padding: .3rem .6rem; font-size: .8rem; }` | Smaller in-row buttons so they don't dominate the table. |
| `td.actions a { font-size: .8rem; color: #2563eb; }` | Matches the Edit link to the small button size. |
| `td.empty { text-align: center; color: #9ca3af; padding: 1.5rem; }` | Styles the "No tasks yet" empty-state cell: centred, muted, roomy. |

---

### 4.9 `.gitignore`

```
# local SQLite database - data, not source
*.db
*.sqlite3

# python
__pycache__/
*.py[cod]
.venv/
venv/
```

| Pattern | Why |
|---|---|
| `*.db`, `*.sqlite3` | `tasks.db` is **runtime data**, not source. Committing it would create merge conflicts on every insert and could leak real data. It is recreated automatically by `create_all`. |
| `__pycache__/` | Compiled bytecode directories — machine-generated. |
| `*.py[cod]` | A glob covering `.pyc`, `.pyo`, `.pyd`. |
| `.venv/`, `venv/` | Virtual environments are large, platform-specific, and reproducible from `requirement.txt`. |

---

## 5. Complete route/endpoint reference

### JSON API (`main.py`) — for code, Postman, `/docs`

| Method | Path | Function | Input | Success | Errors |
|---|---|---|---|---|---|
| GET | `/` | `get_root` | — | `307` redirect → `/ui/tasks` | — |
| GET | `/tasks` | `get_all_tasks` | query `skip` (int, default 0), `limit` (int, default 10, ≤ 100) | `200` + `[TaskOut]` | `422` bad/oversized params |
| GET | `/tasks/{task_id}` | `get_task_with_id` | path `task_id: int` | `200` + `TaskOut` | `404`, `422` non-int id |
| POST | `/tasks` | `add_task` | JSON body `TaskCreate` | `201` + `TaskOut` | `422` invalid body |
| PUT | `/tasks/{task_id}` | `update_task` | JSON body `TaskCreate` (all fields) | `200` + `TaskOut` | `404`, `422` |
| PATCH | `/tasks/{task_id}` | `patch_task` | JSON body `TaskUpdate` (any subset) | `200` + `TaskOut` | `404`, `422` |
| DELETE | `/tasks/{task_id}` | `delete_task` | path `task_id: int` | `204` no body | `404`, `422` |

### HTML UI (`web.py`) — for browsers, prefix `/ui`

| Method | Path | Function | Input | Result |
|---|---|---|---|---|
| GET | `/ui/tasks` | `tasks_page` | — | `200` HTML page `tasks.html` (all tasks, ordered by deadline) |
| POST | `/ui/tasks` | `create_task_form` | form `task_name`, `deadline` | insert + `303` → `/ui/tasks` |
| GET | `/ui/tasks/{task_id}/edit` | `edit_page` | path id | `200` HTML page `edit.html` (pre-filled) or `404` |
| POST | `/ui/tasks/{task_id}/edit` | `edit_task_form` | form `task_name`, `deadline`, `completed` (optional) | update + `303` → `/ui/tasks` |
| POST | `/ui/tasks/{task_id}/toggle` | `toggle_task` | path id | flip `completed` + `303` |
| POST | `/ui/tasks/{task_id}/delete` | `delete_task_form` | path id | delete + `303` |

### Built-in routes provided by FastAPI

| Path | What |
|---|---|
| `/docs` | Swagger UI — interactive, lets you execute requests from the browser. |
| `/redoc` | ReDoc — clean read-only reference. |
| `/openapi.json` | The machine-readable OpenAPI 3 schema both docs pages are built from. |
| `/static/*` | Files from `Task_manager/static/` via the `StaticFiles` mount. |

---

## 6. Dependencies — every package and why it is installed

Most entries in `requirement.txt` are **transitive** (pulled in by something else).
Only four are directly imported by this code.

### Directly used

| Package | Used for |
|---|---|
| **fastapi** | `FastAPI`, `APIRouter`, `Depends`, `HTTPException`, `Query`, `Form`, `Request`, `status`, responses, `StaticFiles`, `Jinja2Templates`. The framework itself: routing, validation, dependency injection, OpenAPI. |
| **uvicorn** | The ASGI server that actually runs the app (`uvicorn main:app --reload`). FastAPI is only a framework; it does not listen on a port by itself. |
| **SQLAlchemy** | `create_engine`, `sessionmaker`, `declarative_base`, `Column`, `Integer`, `String`, `Date`, `Boolean`, `select`, `Session`. The ORM/database toolkit. |
| **pydantic** | `BaseModel`, `Field`, `ConfigDict` — all request/response validation and serialization. |
| **Jinja2** | The template engine behind `Jinja2Templates`, rendering `base/tasks/edit.html`. (Task_manager only.) |
| **python-multipart** | Required by Starlette to parse `application/x-www-form-urlencoded` / multipart bodies. Without it, every `Form(...)` parameter raises an error. (Task_manager only.) |

### Transitive / supporting

| Package | Why it's there |
|---|---|
| **starlette** | The ASGI toolkit FastAPI is built on: routing, `Request`/`Response`, redirects, `StaticFiles`, `TemplateResponse`, middleware. |
| **pydantic_core** | Pydantic v2's compiled (Rust) validation core — the reason validation is fast. |
| **annotated-types** | Supplies the constraint types (`Gt`, `MaxLen`, …) that `Field(min_length=..., le=...)` is built from. |
| **annotated-doc** | Helper for documentation metadata in `Annotated[...]` hints. |
| **typing_extensions** | Back-ports of newer typing features used by Pydantic/FastAPI. |
| **typing-inspection** | Lets Pydantic introspect complex type hints at runtime. |
| **anyio** | The async concurrency layer Starlette uses — including the threadpool that runs our `def` (sync) endpoints. |
| **h11** | Pure-Python HTTP/1.1 protocol implementation used by Uvicorn. |
| **click** | Builds Uvicorn's command-line interface (`--reload`, `--port`, …). |
| **idna** | Internationalised domain-name handling, required by `anyio`. |
| **MarkupSafe** | Provides the escaping primitives Jinja2 uses for auto-escaping (the XSS protection). |
| **opentelemetry-api** | Optional tracing hooks pulled in by the pinned FastAPI/Starlette versions; unused by this code. |
| **sqlite3** | Not in the file — it ships with the Python standard library, which is why SQLite needs no install. |

`FASTAPI/Hello_world/requirement.txt` is the same minus `SQLAlchemy`, `Jinja2`,
`MarkupSafe` and `python-multipart`, because that project has no database, no
templates and no forms.

---

## 7. How to run both projects

Requirements: **Python 3.10+** (the `str | None` syntax in `schemas.py` needs 3.10).

### Task_manager (the full app)

```cmd
cd FASTAPI\Task_manager
python -m venv .venv
.venv\Scripts\activate
pip install -r requirement.txt
uvicorn main:app --reload
```

Then open:

- <http://127.0.0.1:8000/> → redirects to the UI
- <http://127.0.0.1:8000/ui/tasks> → the HTML table
- <http://127.0.0.1:8000/docs> → Swagger UI for the JSON API

**You must `cd` into `Task_manager` first.** The modules use flat imports
(`import models`, `from database import ...`), so that folder has to be on
`sys.path` — which happens automatically when it is the working directory. The
SQLite URL `sqlite:///./tasks.db` is also relative to the working directory, so
running from elsewhere would silently create a second, empty database.

Command breakdown: `uvicorn` = the server, `main` = the module `main.py`,
`:app` = the `FastAPI` object inside it, `--reload` = restart on file change
(development only — never in production).

### Hello_world (the demo)

```cmd
cd FASTAPI\Hello_world
pip install -r requirement.txt
uvicorn main:app --reload
```

Open <http://127.0.0.1:8000/docs> and exercise the `/teas` endpoints.

---

## 8. Manual test recipes (curl)

```bash
# create
curl -X POST http://127.0.0.1:8000/tasks \
     -H "Content-Type: application/json" \
     -d "{\"task_name\":\"learn FastAPI\",\"deadline\":\"2026-11-01\"}"

# list (pagination)
curl "http://127.0.0.1:8000/tasks?skip=0&limit=5"

# read one
curl http://127.0.0.1:8000/tasks/1

# full replace (every field required)
curl -X PUT http://127.0.0.1:8000/tasks/1 \
     -H "Content-Type: application/json" \
     -d "{\"task_name\":\"learn FastAPI deeply\",\"deadline\":\"2026-12-01\",\"completed\":true}"

# partial update (only what you send changes)
curl -X PATCH http://127.0.0.1:8000/tasks/1 \
     -H "Content-Type: application/json" \
     -d "{\"completed\":true}"

# delete -> 204, empty body
curl -i -X DELETE http://127.0.0.1:8000/tasks/1

# validation demos
curl http://127.0.0.1:8000/tasks/abc            # 422 - task_id must be int
curl "http://127.0.0.1:8000/tasks?limit=9999"   # 422 - limit <= 100
curl http://127.0.0.1:8000/tasks/999999         # 404 - Task not found
```

---

## 9. Design decisions & gotchas

1. **Two faces, one database.** JSON and HTML are separate modules but share
   `get_db()` and `models.Task`, so a task added in the browser appears instantly in
   `GET /tasks`. Separation keeps a `303`-redirect-and-render concern out of the clean
   REST API.
2. **Forms can't do PUT/PATCH/DELETE.** That single HTML limitation is the entire
   reason `web.py` exists with `/toggle`, `/edit`, `/delete` POST endpoints.
3. **POST/Redirect/GET with `303`.** Every write answers with a redirect so F5 never
   re-submits and the back button behaves. `303` (not `302`) guarantees the follow-up
   request is a GET.
4. **Validate at the edge, twice if needed.** `max_length=100` appears in the model
   (`String(100)`), the schema (`Field`), the form (`Form(..., max_length=100)`) and the
   HTML (`maxlength="100"`). Browser checks are UX; server checks are security; SQLite
   doesn't enforce string length at all.
5. **`Form(False)` for checkboxes.** Unchecked checkboxes send nothing. Forgetting the
   default makes "uncheck + save" fail with a confusing `422`.
6. **`.isoformat()` vs `.strftime()` in templates.** `<input type="date">` accepts only
   `YYYY-MM-DD`; a prettified value renders an **empty** field with no error — a silent
   bug, which is why `edit.html` uses `.isoformat()` while `tasks.html` (display only)
   uses `.strftime('%d %b %Y')`.
7. **`db.refresh()` after `commit()`.** Needed in the JSON API to read back the
   DB-generated `id`. The HTML routes skip it because they redirect instead of
   serializing the object.
8. **`check_same_thread=False`.** Required only because sync endpoints run in a
   threadpool; each request still gets its own `Session`.
9. **`exclude_unset=True` is what makes PATCH a PATCH.** Without it, omitted fields
   would be written as `None` and PATCH would behave like a destructive PUT.
10. **`create_all` is not a migration tool.** It creates missing tables but never
    alters existing ones. Adding a column later needs Alembic or a dropped `tasks.db`.
11. **`name="static"` on the mount.** Omitting the name breaks
    `url_for('static', ...)` in `base.html` and the page loads unstyled.
12. **Sync (`def`) endpoints are deliberate.** The classic SQLAlchemy `Session` is
    blocking; using `async def` with it would stall the event loop.
13. **Flat imports require the right working directory.** See section 7.

---

## 10. Ideas for extension

| Idea | Touch points |
|---|---|
| Filter/sort the UI (all / pending / done) | query params in `tasks_page`, a filter bar in `tasks.html` |
| Pagination in the UI | reuse `offset`/`limit` from `get_all_tasks` |
| Users & authentication | new `User` model, foreign key on `Task`, session cookies or OAuth2 + JWT |
| Real schema migrations | add **Alembic** instead of `create_all` |
| Switch to PostgreSQL | change only the URL in `database.py`, drop `connect_args` |
| Automated tests | `pytest` + `fastapi.testclient.TestClient` with a dependency-override of `get_db` pointing at an in-memory SQLite |
| Flash messages ("Task deleted") | session middleware + a message block in `base.html` |
| Async stack | `sqlalchemy.ext.asyncio`, `AsyncSession`, and `async def` endpoints |

---

## 11. Appendix A — every variable in the project

Module-level ("global") variables are the long-lived objects; local variables are the
short-lived names inside each function. Both are listed exhaustively.

### `FASTAPI/Hello_world/main.py`

| Variable | Scope | Type | Why it exists |
|---|---|---|---|
| `app` | module | `FastAPI` | The application object every route decorator attaches to; `uvicorn main:app` looks up this exact name. |
| `teas` | module | `List[Tea]` | The in-memory store. A module-level list so the data survives between requests (but not between restarts). |
| `tea` | local (`add_tea`) | `Tea` | The validated request body FastAPI built from the JSON payload. |
| `tea` | local (loops) | `Tea` | The current item while scanning `teas`. |
| `index` | local (loops) | `int` | The position produced by `enumerate`, needed to replace (`teas[index] = ...`) or remove (`teas.pop(index)`) an element. |
| `tea_id` | local (path param) | `int` | The id taken from the URL; typed `int` so FastAPI converts and validates it. |
| `updated_tea` | local (`update_tea`) | `Tea` | The replacement object sent in the PUT body. |
| `deleted` | local (`delete_tea`) | `Tea` | The object returned by `pop()`, kept only so the confirmation message can name it. |

### `FASTAPI/Task_manager/database.py`

| Variable | Scope | Type | Why it exists |
|---|---|---|---|
| `engine` | module | `Engine` | Owns the connection pool and SQL dialect. One per process. |
| `SessionLocal` | module | session factory | Produces a new `Session` per request without re-reading configuration. |
| `Base` | module | declarative base class | Collects table metadata from every model so `create_all` can build the schema. |
| `db` | local (`get_db`) | `Session` | The request-scoped session that is yielded to the endpoint and closed afterwards. |

### `FASTAPI/Task_manager/models.py`

| Variable | Scope | Type | Why it exists |
|---|---|---|---|
| `__tablename__` | class attribute | `str` | Tells SQLAlchemy the physical table name (`"tasks"`). Mandatory in declarative mapping. |
| `id` | class attribute | `Column(Integer)` | Primary key, auto-generated by SQLite. |
| `task_name` | class attribute | `Column(String(100))` | The task text, `NOT NULL`. |
| `deadline` | class attribute | `Column(Date)` | The due date as a real date, `NOT NULL`. |
| `completed` | class attribute | `Column(Boolean)` | Done flag, `NOT NULL`, defaults to `False`. |

### `FASTAPI/Task_manager/schemas.py`

| Variable | Scope | Type | Why it exists |
|---|---|---|---|
| `task_name` | field (`TaskBase`, `TaskUpdate`) | `str` / `str \| None` | The validated name, 1–100 characters. |
| `deadline` | field (`TaskBase`, `TaskUpdate`) | `date` / `date \| None` | The validated ISO date. |
| `completed` | field (`TaskBase`, `TaskUpdate`) | `bool` / `bool \| None` | The validated flag; defaults to `False` on input. |
| `id` | field (`TaskOut`) | `int` | Present only in responses, because the database owns it. |
| `model_config` | class attribute (`TaskOut`) | `ConfigDict` | Pydantic v2 configuration holder; carries `from_attributes=True` so ORM objects can be serialized. |

### `FASTAPI/Task_manager/main.py`

| Variable | Scope | Type | Why it exists |
|---|---|---|---|
| `BASE_DIR` | module | `Path` | Absolute path to the project folder, so `static/` resolves regardless of the shell's working directory. |
| `app` | module | `FastAPI` | The application: routes, docs, mounts and the included web router all hang off it. |
| `skip` | local (query param) | `int` | Pagination offset. |
| `limit` | local (query param) | `int` | Pagination page size, capped at 100. |
| `db` | local (injected) | `Session` | The request's database session, supplied by `Depends(get_db)`. |
| `stmt` | local (`get_all_tasks`) | `Select` | The built `SELECT ... OFFSET ... LIMIT` statement, kept in a name for readability before execution. |
| `task_id` | local (path param) | `int` | The row id from the URL. |
| `task` | local (most endpoints) | `models.Task \| None` | The loaded or newly created ORM row; `None` triggers the `404`. |
| `payload` | local (write endpoints) | `TaskCreate` / `TaskUpdate` | The validated request body. |
| `field` | local (update/patch loop) | `str` | The attribute name being copied onto the ORM object. |
| `value` | local (update/patch loop) | any | The new value for that attribute. |

### `FASTAPI/Task_manager/web.py`

| Variable | Scope | Type | Why it exists |
|---|---|---|---|
| `BASE_DIR` | module | `Path` | Absolute path used to locate `templates/`. |
| `templates` | module | `Jinja2Templates` | The template renderer, built once at import time. |
| `router` | module | `APIRouter` | Collects the HTML routes under the `/ui` prefix so `main.py` can include them. |
| `request` | local (page views) | `Request` | Required by `Jinja2Templates` so templates can call `url_for()`. |
| `db` | local (injected) | `Session` | The request's database session. |
| `tasks` | local (`tasks_page`) | `list[Task]` | All rows ordered by deadline, handed to the template. |
| `task` | local | `models.Task \| None` | The single row being shown, edited, toggled or deleted. |
| `task_id` | local (path param) | `int` | The row id from the URL. |
| `task_name` | local (form field) | `str` | Submitted name, 1–100 characters. |
| `deadline` | local (form field) | `date` | Submitted date, parsed from `YYYY-MM-DD`. |
| `completed` | local (form field) | `bool` | Submitted checkbox, defaulting to `False` when absent. |

### Template variables (the render context)

| Variable | Available in | Supplied by | Why |
|---|---|---|---|
| `tasks` | `tasks.html` | `tasks_page` context | The list to loop over and count. |
| `task` | `tasks.html` (loop), `edit.html` (context) | loop variable / `edit_page` | The row being rendered or pre-filled into the form. |
| `request` | all templates | `TemplateResponse` | Backs `url_for()`. |
| `url_for` | all templates | Starlette | Builds URLs for the named `static` mount. |

---

## 12. Appendix B — every imported symbol, method and attribute called

### FastAPI / Starlette

| Symbol | Where | Why |
|---|---|---|
| `FastAPI(title=...)` | `main.py`, `Hello_world/main.py` | Creates the app; `title` labels the docs pages. |
| `APIRouter(prefix=..., tags=...)` | `web.py` | A modular route group; the prefix keeps HTML URLs under `/ui`. |
| `app.get / post / put / patch / delete` | both `main.py` files | Register a function for a method + path. |
| `router.get / router.post` | `web.py` | Same, on the router. |
| `app.mount(path, app, name)` | `main.py` | Attaches the `StaticFiles` sub-app; `name` enables `url_for`. |
| `app.include_router(router)` | `main.py` | Merges `web.py`'s routes into the application. |
| `Depends(get_db)` | all endpoints | Dependency injection of the per-request session. |
| `HTTPException(status_code, detail)` | all lookups | Aborts with a real HTTP error instead of a fake success body. |
| `Query(default=..., le=...)` | `get_all_tasks` | Declares and constrains a query parameter. |
| `Form(..., min_length=..., max_length=...)` | `web.py` | Declares a urlencoded form field; `...` means required. |
| `Request` | `web.py` page views | Needed by the template renderer. |
| `status.HTTP_201_CREATED / 204_NO_CONTENT / 303_SEE_OTHER / 404_NOT_FOUND` | both modules | Readable constants instead of bare numbers. |
| `RedirectResponse(url, status_code=...)` | `main.py`, `web.py` | Sends the browser somewhere else (root → UI, post-write → table). |
| `HTMLResponse` | `web.py` (`response_class`) | Declares the page routes as `text/html`. |
| `StaticFiles(directory=...)` | `main.py` | Serves `style.css` from disk. |
| `Jinja2Templates(directory=...)` | `web.py` | Creates the template environment. |
| `templates.TemplateResponse(request=, name=, context=)` | `web.py` | Renders a template into an HTTP response. |
| `response_model=` | JSON endpoints | Declares, filters and documents the response shape. |
| `status_code=` | POST/DELETE | Overrides the default `200`. |
| `include_in_schema=False` | `get_root` | Hides a plumbing route from the docs. |

### SQLAlchemy

| Symbol | Where | Why |
|---|---|---|
| `create_engine(url, connect_args=...)` | `database.py` | Builds the engine/connection pool. |
| `sessionmaker(bind=, autocommit=, autoflush=)` | `database.py` | Configured session factory. |
| `declarative_base()` | `database.py` | Base class that gathers table metadata. |
| `Column(...)` | `models.py` | Declares a mapped column and gives a queryable attribute. |
| `Integer`, `String`, `Date`, `Boolean` | `models.py` | The column types; `Date`/`Boolean` give real Python `date`/`bool` values back. |
| `primary_key=True` | `models.py` | Marks the PK (and makes SQLite autoincrement it). |
| `index=True` | `models.py` | Requests an index for fast lookup. |
| `nullable=False` | `models.py` | Enforces `NOT NULL`. |
| `default=False` | `models.py` | Python-side default applied on INSERT. |
| `Base.metadata.create_all(bind=engine)` | `main.py` | Creates missing tables (and the `.db` file) at startup. |
| `select(Model)` | `main.py`, `web.py` | SQLAlchemy 2.0 statement builder. |
| `.offset(n)` / `.limit(n)` | `get_all_tasks` | Database-side pagination. |
| `.order_by(Model.column)` | `tasks_page` | Sorts rows by deadline in SQL. |
| `db.scalars(stmt)` | both query sites | Yields model objects instead of one-element rows. |
| `.all()` | both query sites | Materializes the result into a list. |
| `db.get(Model, pk)` | every single-row lookup | Fast primary-key fetch; returns `None` when absent. |
| `db.add(obj)` | create endpoints | Stages an INSERT. |
| `db.delete(obj)` | delete endpoints | Stages a DELETE. |
| `db.commit()` | every write | Ends the transaction and persists the change. |
| `db.refresh(obj)` | `add_task`, `update_task`, `patch_task` | Re-reads the row to pick up DB-generated values (the new `id`). |
| `db.close()` | `get_db` teardown | Returns the connection to the pool. |
| `Session` | type hints | Documents the injected type and enables autocomplete. |

### Pydantic

| Symbol | Where | Why |
|---|---|---|
| `BaseModel` | `schemas.py`, `Hello_world` | Base class providing validation, serialization and JSON Schema. |
| `Field(default=, min_length=, max_length=)` | `schemas.py` | Per-field constraints and defaults. |
| `ConfigDict(from_attributes=True)` | `TaskOut` | Allows reading values from ORM object attributes. |
| `payload.model_dump()` | `add_task`, `update_task` | Converts the model to a plain dict for the ORM constructor / full overwrite. |
| `payload.model_dump(exclude_unset=True)` | `patch_task` | Returns only the fields the client actually sent — true partial update. |

### Python standard library

| Symbol | Where | Why |
|---|---|---|
| `pathlib.Path` | `main.py`, `web.py` | Path objects that support the `/` operator. |
| `Path(__file__).resolve().parent` | both | Absolute, symlink-free folder of the current module. |
| `datetime.date` | `schemas.py`, `web.py` | The deadline type; drives automatic parsing/validation. |
| `date.isoformat()` | `edit.html` | Emits `YYYY-MM-DD`, the only format `<input type="date">` accepts. |
| `date.strftime(fmt)` | `tasks.html` | Human-readable display format. |
| `setattr(obj, name, value)` | `update_task`, `patch_task` | Generic attribute assignment so the loop works for any field set. |
| `typing.List` | `Hello_world/main.py` | Legacy generic annotation for the storage list. |
| `list.append` / `list.pop` / `enumerate` | `Hello_world/main.py` | The in-memory CRUD primitives. |

---

## 13. Appendix C — HTML elements & attributes glossary

| Element / attribute | Where | Why |
|---|---|---|
| `<!DOCTYPE html>` | `base.html` | Forces standards mode. |
| `<html lang="en">` | `base.html` | Declares the language for assistive tech and translators. |
| `<head>` / `<body>` | `base.html` | Metadata vs visible content. |
| `<meta charset="utf-8">` | `base.html` | UTF-8 so any characters in a task name render correctly. |
| `<meta name="viewport" ...>` | `base.html` | Mobile-friendly scaling. |
| `<title>` | `base.html` (+ overrides) | The browser tab label. |
| `<link rel="stylesheet" href="...">` | `base.html` | Loads `style.css`. |
| `<header>` / `<nav>` / `<main>` / `<section>` | templates | Semantic landmarks instead of anonymous `<div>`s. |
| `<h1>` / `<h2>` | templates | Document heading hierarchy. |
| `<a href="...">` | templates | Navigation only — safe GET links (home, docs, Edit, Cancel). |
| `<form action="..." method="post">` | templates | Submits a write; `action` is the target route, `method="post"` keeps writes out of GET. |
| `<label>` wrapping its input | forms | Clicking the caption focuses the field (accessibility). |
| `<input type="text">` | both forms | Free-text task name. |
| `<input type="date">` | both forms | Native date picker that submits `YYYY-MM-DD`. |
| `<input type="checkbox">` | `edit.html` | The completed flag; sends nothing when unchecked. |
| `name="..."` | every field | Must match the `Form(...)` parameter name in `web.py` — this is the wire contract. |
| `value="..."` | edit fields, checkbox | Pre-fills the current value / defines what a checked box submits. |
| `required` | text & date fields | Instant browser-side validation (UX only; the server re-checks). |
| `maxlength="100"` | task-name fields | Mirrors the 100-character limit. |
| `placeholder="..."` | add form | Shows an example without pre-filling a value. |
| `checked` (conditional) | `edit.html` | Reflects the stored `completed` state. |
| `<button type="submit">` | every form | Triggers submission. |
| `class="card" / "inline" / "actions" / "danger" / "subtle" / "cancel" / "done" / "empty"` | templates | Hooks the CSS rules in `style.css`; `done` is set from data. |
| `<table>` / `<thead>` / `<tbody>` / `<tr>` / `<th>` / `<td>` | `tasks.html` | Proper tabular markup for tabular data. |
| `colspan="5"` | empty-state row | Makes one cell span all five columns. |
| `onsubmit="return confirm(...)"` | delete form | The project's only JavaScript: a guard against accidental deletion (returning `false` cancels the submit). |

---

## 14. Appendix D — CSS properties & colour palette glossary

### Properties used, and why

| Property | Why it is used here |
|---|---|
| `box-sizing: border-box` | Widths include padding/border, so fields and cells never overflow. |
| `font-family` | Picks the OS UI font stack — no webfont download. |
| `font-size` / `font-weight` / `font: inherit` | Builds the type hierarchy; `inherit` stops inputs from using the tiny browser default. |
| `line-height` | Readable spacing between lines of text. |
| `color` / `background` | Text and surface colours (see palette). |
| `margin` / `padding` | Outer and inner spacing; `margin: 2rem auto` also centres the page. |
| `max-width` | Caps line length for readability. |
| `display: flex` | Row/column layout for the header, labels, form card and action cells. |
| `flex-direction` | `column` stacks a label over its input; `row` puts the checkbox beside its text. |
| `flex-wrap: wrap` | Lets the form card reflow onto multiple lines on narrow screens. |
| `justify-content: space-between` | Pushes the header title and nav link to opposite ends. |
| `align-items` (`baseline` / `center` / `flex-end`) | Vertical alignment: text baselines in the header, centred checkbox, bottom-aligned form controls. |
| `gap` | Consistent spacing between flex children without margin hacks. |
| `border` / `border-bottom` / `border: 0` | Field outlines, the header rule and table row separators; `0` removes the default button border. |
| `border-radius` | Softened corners on the card, inputs and buttons. |
| `border-collapse: collapse` | Merges adjacent table borders into single clean lines. |
| `text-align` | Left-aligns table content; centres the empty-state message. |
| `vertical-align: middle` | Centres cell content vertically. |
| `text-transform: uppercase` / `letter-spacing` | Makes the table header row visually distinct. |
| `text-decoration: none` | Stops the clickable site title looking like a link. |
| `text-decoration: line-through` | Strikes through completed tasks. |
| `min-width` | Keeps the task-name input usably wide. |
| `cursor: pointer` | Signals that buttons are clickable. |
| `filter: brightness(1.1)` | A single hover effect that works for every button colour. |
| `width: 100%` | Makes the table span its container. |
| `display: inline` (on in-row forms) | Prevents each tiny action form from forcing a line break. |
| `:hover` pseudo-class | Feedback on buttons and table rows. |
| `*` universal selector | Applies the `box-sizing` reset everywhere. |
| Attribute selectors `input[type="text"]`, `input[type="date"]` | Style only the relevant input kinds. |
| Class selectors `.card`, `.inline`, `.danger`, `.subtle`, `.cancel`, `tr.done`, `td.actions`, `td.empty` | Target the exact hooks the templates emit. |

### Colour palette

| Colour | Role |
|---|---|
| `#222` | Default body text — softer than pure black. |
| `#111` | The site title. |
| `#2563eb` | Accent blue: links and the primary button. |
| `#dc2626` | Danger red: the Delete button. |
| `#64748b` | Neutral slate: the secondary Toggle button. |
| `#6b7280` | Muted grey: the Cancel link. |
| `#4b5563` | Form label text. |
| `#475569` | Table header text. |
| `#9ca3af` | Completed-task text and the empty-state message. |
| `#cbd5e1` | Input borders. |
| `#e5e7eb` | Card border and the header rule. |
| `#eee` | Table row separators. |
| `#f1f5f9` | Table header background. |
| `#f7f7f9` | Form card background. |
| `#fafafa` | Table row hover background. |
| `#fff` | Button text. |
