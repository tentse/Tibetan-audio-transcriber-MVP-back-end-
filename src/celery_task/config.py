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
# celery_app.conf.update(
#     task_default_queue='default',
#     # task_serializer="json",
#     # result_serializer="json",
#     # accept_content=["json"],
#     # timezone="UTC",
#     enable_utc=True,
#     worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
#     worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
#     worker_hijack_root_logger=False,
# )