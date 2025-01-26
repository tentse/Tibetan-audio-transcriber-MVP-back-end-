from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    project_id = Column(String, unique=True, index=True)
    date = Column(String)
    project_name = Column(String)
    project_status = Column(String)
    audio_link = Column(String)
    model = Column(String)

class audio_segment(Base):
    
    __tablename__ = "audio_segments"

    id = Column(Integer, primary_key=True, index=True)
    sequence = Column(Integer)
    email = Column(String, index=True)
    project_id = Column(String, index=True)
    start_time = Column(String)
    end_time = Column(String)
    transcription = Column(String)
    comments = Column(String, default=None)

class model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, unique=True, index=True)


def create_tables():
    Base.metadata.create_all(bind=engine)



