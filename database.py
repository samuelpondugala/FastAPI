from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


engine = create_engine("sqlite:///./tasks.db", connect_args={"check_same_thread":False},) # Sqlite only: FastAPI uses threads


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """One session perf request, always closed afterwards """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()