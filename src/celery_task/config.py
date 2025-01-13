from celery import Celery
import os
from src.libs.audio_time_stamp import get_time_stamp
from src.libs.transcribe import segment_and_transcribe
from src.libs.write_audio_inference_to_db import write_audio_inference_to_db
from src.libs.transcribe import update_translation_status

#celery -A src.celery.config worker --loglevel=info
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")


celery_app = Celery("transcription_tasks", broker=redis_url, backend=redis_url)
os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')
celery_app.conf.update(
    task_default_queue='default',
    # task_serializer="json",
    # result_serializer="json",
    # accept_content=["json"],
    # timezone="UTC",
    enable_utc=True,
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_hijack_root_logger=False,
)

# @celery_app.task(bind=True)
# async def speech_to_text_task(self, content: str, email: str, model: str, project_id: str):

#     try:
#         print('here in function')
#         # getting the time stamp of the audio file, will return the start and end time where ever it detects speech in the audio
#         audio_time_stamp = await get_time_stamp(content)
#         total_audio_segments = len(audio_time_stamp)
#         print("Time Stamp Generated")
#         update_translation_status(project_id, "AUDIO TIME STAMP GENERATED", 0, "NONE")
#         # print(audio_time_stamp)

#         # segment the audio file base on the start and end time and transcribe the audio
#         audio_inference = await segment_and_transcribe(total_audio_segments, project_id, content, audio_time_stamp)
#         update_translation_status(project_id, "success", "NONE")

#         write_inference_to_db = await write_audio_inference_to_db(email, project_id, audio_inference, model)
        
#         return {"status": "success", "message": "Audio file transcribed successfully"}

#     except Exception as e:
#         print('error part')
#         error_msg = str(e)
#         update_translation_status(project_id, 'FAILED', error=error_msg)
#         self.retry(exc=e, countdown=60, max_retries=3)
#         return {"status": "failure", "error": str(e)}

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