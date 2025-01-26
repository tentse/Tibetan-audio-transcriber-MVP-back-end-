from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from src.database.models import Project, get_db, audio_segment
from sqlalchemy.orm import Session
import uuid
import io
from datetime import date
from src.celery_task.task import speech_to_text_task
import redis
import json
from src.libs.update_status import update_translation_status
from src.libs.s3upload import upload_file_to_s3
import time
from pydantic import BaseModel

router = APIRouter()

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

class ProjectUpdate(BaseModel):
    project_id: str
    sequence: int
    transcription: str
    comments: str

@router.get('/{email}')
async def get_projects(email: str, db: Session = Depends(get_db)):
    #get all the projects of the user
    projects = db.query(Project).filter(Project.email == email).order_by(Project.id.desc()).all()
    if (projects == None):
        return {"message": "User doesn't have any projects currently"}
    return projects



@router.post('/create')
async def create_project(file: UploadFile = File(...), email: str = Form(...), project_name : str = Form(...), model: str = Form(...), db: Session = Depends(get_db)):
    
    contents = await file.read()
    await file.seek(0)
    if (file.content_type not in ["audio/mp3", "audio/wav", "audio/flac", "audio/mpeg"]):
        return {"message": "Invalid file format"}

    project_id = str(uuid.uuid4())

    upload_time = milliseconds_since_epoch = int(time.time() * 1000)
    # print(upload_time)

    # print(file.filename)
    
    upload_file_url = await upload_file_to_s3(file, file.filename.split('.')[-1], f"{upload_time}-{file.filename}")

    task_execution_to_celery = speech_to_text_task.delay(email, model, project_id, upload_file_url)

    created_date = date.today()
    # create a new project
    new_project = Project(email=email, date=created_date, project_name=project_name, project_id=project_id, project_status="CREATED", audio_link=upload_file_url, model=model)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    update_translation_status(project_id, "AUDIO FILE UPLOADED", 0, "NONE")

    return new_project


@router.get('/status/{email}/{project_id}')
async def get_project_status(email: str, project_id: str, db: Session = Depends(get_db)):

    try:
        # check if the project exists in the project table
        project = db.query(Project).filter(Project.email == email, Project.project_id == project_id).first()
        if (project == None):
            return {"message": "Project not found with respective email"}
        
        status_data = redis_client.get(f'translation_status:{project_id}')
        if status_data is None:
            return {"progress": 100, "status": "success", "error": "NONE"}
            
        status = json.loads(status_data)
        return status

    except redis.ConnectionError:
        print("Failed to connect to Redis. Is Redis server running?")
        return {"message": "Service temporarily unavailable"}
        
    except Exception as e:
        print(f"Redis error: {str(e)}")
        return {"message": "Error retrieving status"}
    

@router.get('/audiosegments/{project_id}')
async def get_audio_segments(project_id: str, db: Session = Depends(get_db)):
    project_data = db.query(Project).filter(Project.project_id == project_id).first()
    if (project_data == None):
        return {"message": "Project not found with respective email"}
    
    audio_inference = db.query(audio_segment).filter(audio_segment.project_id == project_id).order_by(audio_segment.sequence).all()
    return audio_inference

@router.post('/audiosegments/update')
async def update_audio_segments(project: ProjectUpdate, db: Session = Depends(get_db)):
    project_id = project.project_id
    transcription = project.transcription
    comments = project.comments
    sequence = project.sequence

    project_data = db.query(Project).filter(Project.project_id == project_id).first()
    if (project_data == None):
        return {"message": "Project not found with respective email"}
    
    update_transcription = db.query(audio_segment).filter(audio_segment.project_id == project_id, audio_segment.sequence == sequence).update({audio_segment.transcription: transcription, audio_segment.comments: comments});
    db.commit()
    return {"message": "Transcription updated successfully"}


@router.get('/download/{email}/{project_id}/{format}')
async def download_project(email: str, project_id: str, format: str, db: Session = Depends(get_db)):
    project_data = db.query(Project).filter(Project.email == email, Project.project_id == project_id).first()
    if (project_data.project_status != "COMPLETED"):
        return {"message": "Project not found with respective email or still in progress"}
    elif (format not in ['txt', 'srt']):
        return {"message": "Invalid format"}

    project_detail = db.query(Project).filter(Project.email == email, Project.project_id == project_id).first()
    project_name = project_detail.project_name

    def model_to_dict(instance):
        return {column.name: getattr(instance, column.name) for column in instance.__table__.columns}
    
    audio_inference = db.query(audio_segment).filter(audio_segment.project_id == project_id).order_by(audio_segment.sequence).all()

    audio_inference_dicts = [model_to_dict(item) for item in audio_inference]
    print(audio_inference_dicts)
    print(format)
    if (format == 'txt'):
        txt_content = ""
        for item in audio_inference_dicts:
            txt_content += f"Start Time: {item['start_time']}, End Time: {item['end_time']}, Transcription: {item['transcription']}\n"

        txt_stream = io.StringIO(txt_content)

        return StreamingResponse(txt_stream, media_type="text/plain", headers={"Content-Disposition": f"attachment; filename={project_name}_text.txt"})
    elif (format == 'srt'):
        srt_content = ""
        index = 1

        def seconds_to_srt_format(seconds):
            """
            Converts seconds to SRT time format (HH:MM:SS,mmm).
            """
            ms = int((seconds % 1) * 1000)  # Extract milliseconds from the decimal part
            s = int(seconds) % 60           # get in seconds
            m = int(seconds // 60) % 60     # get in minutes
            h = int(seconds // 3600)        # get in hours
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"  # Format the time
        

        for subtitle in audio_inference_dicts:
            start_val = float(subtitle['start_time'])  # parse float
            end_val = float(subtitle['end_time'])      # parse float

            format_start_time = seconds_to_srt_format(start_val)
            format_end_time = seconds_to_srt_format(end_val)

            srt_content += f"{index}\n"
            srt_content += f"{format_start_time} --> {format_end_time}\n"
            srt_content += f"{subtitle['transcription']}\n\n"
            index += 1

        srt_stream = io.StringIO(srt_content)
    
        # Return the content as a downloadable .srt file
        return StreamingResponse(
            srt_stream,
            media_type="application/x-subrip-text-subtitle",  # MIME type for SRT files
            headers={"Content-Disposition": f"attachment; filename={project_name}.srt"}
        )
    else:
        return {"message": "Invalid format"}