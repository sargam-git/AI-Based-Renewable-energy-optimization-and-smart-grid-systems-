from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
@event.listens_for(engine, "connect")
def sqlite_settings(connection, _):
    cursor=connection.cursor(); cursor.execute("PRAGMA journal_mode=WAL"); cursor.execute("PRAGMA foreign_keys=ON"); cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
class Base(DeclarativeBase): pass
def get_db():
    with SessionLocal() as session:
        yield session
