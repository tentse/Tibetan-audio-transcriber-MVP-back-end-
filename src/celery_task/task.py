from src.celery_task.config import celery_app
from src.libs.audio_time_stamp import get_time_stamp
from src.libs.transcribe import segment_and_transcribe
from src.libs.write_audio_inference_to_db import write_audio_inference_to_db
from src.libs.transcribe import update_translation_status
from src.libs.s3download import download_file_from_s3
import asyncio


@celery_app.task(bind=True)
def speech_to_text_task(self, email: str, model: str, project_id: str, file_url: str):
    try:

        print('downloading and getting audio file content')
        content = asyncio.run(download_file_from_s3(file_url))
        print('got audio file content')

        print(content)

        # Run async function using asyncio.run
        audio_time_stamp = asyncio.run(get_time_stamp(content))  # Running async code inside sync task
        total_audio_segments = len(audio_time_stamp)
        print("Time Stamp Generated for :", project_id, end=" ")

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
        print('error in clery worker, retrying in 60s')
        error_msg = str(e)
        update_translation_status(project_id, 'FAILED', error=error_msg)

        # Retry the task
        self.retry(exc=e, countdown=60, max_retries=3)

        return {"status": "failure", "error": str(e)}