from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from src.database.models import Project, get_db, audio_segment
from sqlalchemy.orm import Session
import uuid
import io
from datetime import date
from src.libs.audio_time_stamp import get_time_stamp
from src.libs.transcribe import segment_and_transcribe
from src.libs.write_audio_inference_to_db import write_audio_inference_to_db

router = APIRouter()

@router.get('/projects/{email}')
async def get_projects(email: str, db: Session = Depends(get_db)):
    #get all the projects of the user
    projects = db.query(Project).filter(Project.email == email).all()
    if (projects == None):
        return {"message": "User doesn't have any projects currently"}
    return projects

@router.post('/projects/create/{email}/{model}')
async def create_project(email: str, file: UploadFile, model: str, db: Session = Depends(get_db)):
    # check audio file length is <= 1hr
    contents = await file.read()
    await file.seek(0)
    if (len(contents) > 3600000):
        return {"message": "Audio file is too long"}
    # check if file uploaded is audio file (mp3, wav, flac)
    if (file.content_type not in ["audio/mp3", "audio/wav", "audio/flac", "audio/mpeg"]):
        return {"message": "Invalid file format"}

    # getting the time stamp of the audio file, will return the start and end time where ever it detects speech in the audio
    audio_time_stamp = await get_time_stamp(file)
    
    # segment the audio file base on the start and end time and transcribe the audio
    audio_inference = await segment_and_transcribe(contents, audio_time_stamp)

    project_id = str(uuid.uuid4())

    write_inference_to_db = await write_audio_inference_to_db(email, project_id, audio_inference, model, db)

    created_date = date.today()
    # create a new project
    new_project = Project(email=email, date=created_date, project_id=project_id, project_name=file.filename , project_status="Created", audio_link="link", model=model)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project

@router.get('/projects/status/{email}/{project_id}')
async def get_project_status(email: str, project_id: str, db: Session = Depends(get_db)):
    # get the status of the project
    project = db.query(Project).filter(Project.email == email, Project.project_id == project_id).first()
    if (project == None):
        return {"message": "Project not found"}
    return project

@router.get('/projects/download/{email}/{project_id}/{format}')
async def download_project(email: str, project_id: str, format: str, db: Session = Depends(get_db)):
    audio_inference = db.query(audio_segment).filter(audio_segment.email == email, audio_segment.project_id == project_id).all()
    if (audio_inference == None):
        return {"message": "Project not found with respective email"}

    def model_to_dict(instance):
        return {column.name: getattr(instance, column.name) for column in instance.__table__.columns}

    audio_inference_dicts = [model_to_dict(item) for item in audio_inference]
    # print(audio_inference_dicts)

    if (format == 'txt'):
        txt_content = ""
        for item in audio_inference_dicts:
            txt_content += f"Start Time: {item['start_time']}, End Time: {item['end_time']}, Transcription: {item['transcription']}\n"

        txt_stream = io.StringIO(txt_content)

        return StreamingResponse(txt_stream, media_type="text/plain", headers={"Content-Disposition": "attachment; filename=audio_inference.txt"})
    elif (format == 'srt'):
        srt_content = ""
        index = 1
        for subtitle in audio_inference_dicts:
            srt_content += f"{index}\n"
            srt_content += f"{subtitle['start_time']} --> {subtitle['end_time']}\n"
            srt_content += f"{subtitle['transcription']}\n\n"
            index += 1
        srt_stream = io.StringIO(srt_content)
    
        # Return the content as a downloadable .srt file
        return StreamingResponse(
            srt_stream,
            media_type="application/x-subrip-text-subtitle",  # MIME type for SRT files
            headers={"Content-Disposition": "attachment; filename=audio_srt.srt"}
        )
    else:
        return {"message": "Invalid format"}