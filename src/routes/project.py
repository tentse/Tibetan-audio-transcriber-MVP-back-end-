from fastapi import APIRouter, Depends, HTTPException, UploadFile
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

router = APIRouter()

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


@router.get('/{email}')
async def get_projects(email: str, db: Session = Depends(get_db)):
    #get all the projects of the user
    projects = db.query(Project).filter(Project.email == email).all()
    if (projects == None):
        return {"message": "User doesn't have any projects currently"}
    return projects


@router.post('/create/{email}/{model}')
async def create_project(email: str, file: UploadFile, model: str, db: Session = Depends(get_db)):
    contents = await file.read()
    await file.seek(0)
    # if (len(contents) > 3600000):
    #     return {"message": "Audio file is too long"}
    # check if file uploaded is audio file (mp3, wav, flac)
    if (file.content_type not in ["audio/mp3", "audio/wav", "audio/flac", "audio/mpeg"]):
        return {"message": "Invalid file format"}

    project_id = str(uuid.uuid4())

    task_execution_to_celery = speech_to_text_task.delay(contents, email, model, project_id)

    created_date = date.today()
    # create a new project
    new_project = Project(email=email, date=created_date, project_id=project_id, project_name=file.filename , project_status="Created", audio_link="link", model=model)
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
            return {"message": "success"}
            
        status = json.loads(status_data)
        return status

    except redis.ConnectionError:
        print("Failed to connect to Redis. Is Redis server running?")
        return {"message": "Service temporarily unavailable"}
        
    except Exception as e:
        print(f"Redis error: {str(e)}")
        return {"message": "Error retrieving status"}



@router.get('/download/{email}/{project_id}/{format}')
async def download_project(email: str, project_id: str, format: str, db: Session = Depends(get_db)):
    audio_inference = db.query(audio_segment).filter(audio_segment.email == email, audio_segment.project_id == project_id).all()
    if (audio_inference == None):
        return {"message": "Project not found with respective email"}
    elif (format not in ['txt', 'srt']):
        return {"message": "Invalid format"}

    project_detail = db.query(Project).filter(Project.email == email, Project.project_id == project_id).first()
    project_name = project_detail.project_name.split('.')[0]

    def model_to_dict(instance):
        return {column.name: getattr(instance, column.name) for column in instance.__table__.columns}

    audio_inference_dicts = [model_to_dict(item) for item in audio_inference]
    # print(audio_inference_dicts)

    if (format == 'txt'):
        txt_content = ""
        for item in audio_inference_dicts:
            txt_content += f"Start Time: {item['start_time']}, End Time: {item['end_time']}, Transcription: {item['transcription']}\n"

        txt_stream = io.StringIO(txt_content)

        return StreamingResponse(txt_stream, media_type="text/plain", headers={"Content-Disposition": f"attachment; filename={project_name}.txt"})
    elif (format == 'srt'):
        srt_content = ""
        index = 1
        for subtitle in audio_inference_dicts:
            start_val = float(subtitle['start_time'])  # parse float
            end_val = float(subtitle['end_time'])      # parse float

            start_secs = int(start_val)                # integer part
            end_secs = int(end_val)

            start_millis = int(round((start_val - start_secs) * 1000))
            end_millis = int(round((end_val - end_secs) * 1000))

            format_start_time = f"00:00:{start_secs:02d},{start_millis:03d}"
            format_end_time = f"00:00:{end_secs:02d},{end_millis:03d}"

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