from src.celery_task.config import celery_app
from fastapi import UploadFile, Depends
from sqlalchemy.orm import Session
from src.database.models import get_db
from src.libs.audio_time_stamp import get_time_stamp
from src.libs.transcribe import segment_and_transcribe
from src.libs.write_audio_inference_to_db import write_audio_inference_to_db
from src.libs.transcribe import update_translation_status
import asyncio

# @celery_app.task(bind=True)
# def speech_to_text_task(self, content: str, email: str, model: str, project_id: str):
#     try:
#         print('here')
        
#         # Running async functions in a synchronous context with asyncio
#         audio_time_stamp = asyncio.run(get_time_stamp(content))
#         total_audio_segments = len(audio_time_stamp)
#         print("Time Stamp Generated")
#         update_translation_status(project_id, "AUDIO TIME STAMP GENERATED", 0, "NONE")

#         audio_inference = asyncio.run(segment_and_transcribe(total_audio_segments, project_id, content, audio_time_stamp))
#         update_translation_status(project_id, "success", "NONE")

#         write_inference_to_db = asyncio.run(write_audio_inference_to_db(email, project_id, audio_inference, model))

#         return {"status": "success", "message": "Audio file transcribed successfully"}

#     except Exception as e:
#         print('error part')
#         error_msg = str(e)
#         update_translation_status(project_id, 'FAILED', error=error_msg)
#         self.retry(exc=e, countdown=60, max_retries=3)
#         return {"status": "failure", "error": str(e)}

@celery_app.task(bind=True)
def speech_to_text_task(self, content: str, email: str, model: str, project_id: str):
    try:
        print('here in translation')

        # Run async function using asyncio.run
        audio_time_stamp = asyncio.run(get_time_stamp(content))  # Running async code inside sync task
        total_audio_segments = len(audio_time_stamp)
        print("Time Stamp Generated")

        # Update translation status
        update_translation_status(project_id, "AUDIO TIME STAMP GENERATED", 0, "NONE")

        # Segment and transcribe the audio file
        audio_inference = asyncio.run(segment_and_transcribe(total_audio_segments, project_id, content, audio_time_stamp))

        # Update translation status
        update_translation_status(project_id, "success", "NONE")

        # Write inference to database
        asyncio.run(write_audio_inference_to_db(email, project_id, audio_inference, model))
        
        return {"status": "success", "message": "Audio file transcribed successfully"}

    except Exception as e:
        print('error part')
        error_msg = str(e)
        update_translation_status(project_id, 'FAILED', error=error_msg)

        # Retry the task
        self.retry(exc=e, countdown=60, max_retries=3)

        return {"status": "failure", "error": str(e)}