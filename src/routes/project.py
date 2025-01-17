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
from src.libs.s3upload import upload_file_to_s3
import time
from src.libs.s3download import download_file_from_s3

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

    upload_time = milliseconds_since_epoch = int(time.time() * 1000)
    print(upload_time)

    print(file.filename)
    
    upload_file_url = await upload_file_to_s3(file, file.filename.split('.')[-1], f"{upload_time}-{file.filename}")

    print('before downloading')
    file_obj = await download_file_from_s3(upload_file_url)
    print('after downloading')

    # task_execution_to_celery = speech_to_text_task.delay(contents, email, model, project_id, upload_file_url)

    created_date = date.today()
    # create a new project
    new_project = Project(email=email, date=created_date, project_id=project_id, project_name=file.filename , project_status="CREATED", audio_link=upload_file_url, model=model)
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
    project_data = db.query(Project).filter(Project.email == email, Project.project_id == project_id).first()
    if (project_data.project_status != "COMPLETED"):
        return {"message": "Project not found with respective email or still in progress"}
    elif (format not in ['txt', 'srt']):
        return {"message": "Invalid format"}

    project_detail = db.query(Project).filter(Project.email == email, Project.project_id == project_id).first()
    project_name = project_detail.project_name.split('.')[0]

    def model_to_dict(instance):
        return {column.name: getattr(instance, column.name) for column in instance.__table__.columns}
    
    audio_inference = db.query(audio_segment).filter(audio_segment.project_id == project_id).all()

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

        def seconds_to_srt_format(seconds):
            """
            Converts seconds to SRT time format (HH:MM:SS,mmm).
            """
            ms = int((seconds % 1) * 1000)  # Extract milliseconds from the decimal part
            s = int(seconds) % 60
            m = int(seconds // 60) % 60
            h = int(seconds // 3600)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        

        for subtitle in audio_inference_dicts:
            start_val = float(subtitle['start_time'])  # parse float
            end_val = float(subtitle['end_time'])      # parse float

            # start_secs = int(start_val)                # integer part
            # end_secs = int(end_val)

            # start_millis = int(round((start_val - start_secs) * 1000))

            # end_millis = int(round((end_val - end_secs) * 1000))

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