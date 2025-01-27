from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

app = FastAPI(title="PostgreSQL Cluster Demo")

# Database configuration with read-write separation
PG_IS_IN_RECOVERY_QUERY = "SELECT pg_is_in_recovery()"
DB_USER = os.getenv("POSTGRES_USER", "customuser")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST", "pgpool")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "customdatabase")

if not DB_PASSWORD:
    raise ValueError("POSTGRES_PASSWORD environment variable must be set")

WRITE_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?target_session_attrs=read-write"
READ_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?target_session_attrs=any"

# Create separate engines for read and write operations
write_engine = create_engine(WRITE_DATABASE_URL)
read_engine = create_engine(READ_DATABASE_URL)

# Create separate session factories
WriteSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=write_engine)
ReadSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=read_engine)

Base = declarative_base()

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables (only needs write access)
Base.metadata.create_all(bind=write_engine)

def get_write_db():
    db = WriteSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_read_db():
    db = ReadSessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "PostgreSQL Cluster Demo API"}

@app.post("/notes/")
def create_note(content: str):
    db = WriteSessionLocal()
    try:
        # Verify we're on primary before writing
        result = db.execute(text(PG_IS_IN_RECOVERY_QUERY)).scalar()
        if result:
            raise HTTPException(status_code=500, detail="Attempted to write to replica node")
        
        note = Note(content=content)
        db.add(note)
        db.commit()
        db.refresh(note)
        return {
            "id": note.id,
            "content": note.content,
            "created_at": note.created_at,
            "written_to": "primary"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/notes/")
def read_notes():
    db = ReadSessionLocal()
    try:
        # Check if we're reading from primary or replica
        is_replica = db.execute(text(PG_IS_IN_RECOVERY_QUERY)).scalar()
        node_type = "replica" if is_replica else "primary"
        
        notes = db.query(Note).all()
        return {
            "notes": [{"id": note.id, "content": note.content, "created_at": note.created_at} for note in notes],
            "read_from": node_type
        }
    finally:
        db.close()

@app.get("/notes/{note_id}")
def read_note(note_id: int):
    db = ReadSessionLocal()
    try:
        # Check if we're reading from primary or replica
        is_replica = db.execute(text(PG_IS_IN_RECOVERY_QUERY)).scalar()
        node_type = "replica" if is_replica else "primary"
        
        note = db.query(Note).filter(Note.id == note_id).first()
        if note is None:
            raise HTTPException(status_code=404, detail="Note not found")
        return {
            "id": note.id,
            "content": note.content,
            "created_at": note.created_at,
            "read_from": node_type
        }
    finally:
        db.close()

@app.get("/cluster-status")
def get_cluster_status():
    write_db = WriteSessionLocal()
    read_db = ReadSessionLocal()
    status = {}
    
    try:
        # Check write connection (primary)
        write_result = write_db.execute(text("SELECT pg_is_in_recovery(), current_database(), inet_server_addr()")).first()
        status["write_connection"] = {
            "is_replica": write_result[0],
            "database": write_result[1],
            "server_addr": str(write_result[2])
        }
        
        # Check read connection
        read_result = read_db.execute(text("SELECT pg_is_in_recovery(), current_database(), inet_server_addr()")).first()
        status["read_connection"] = {
            "is_replica": read_result[0],
            "database": read_result[1],
            "server_addr": str(read_result[2])
        }
        
        return status
    finally:
        write_db.close()
        read_db.close()
