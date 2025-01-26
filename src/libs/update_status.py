import redis
import json


redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def update_translation_status(job_id: str, status: str, progress: float = 0, error: str = None):
    """Update translation status in Redis
    
    Args:
        job_id (str): Unique identifier for the translation job
        status (str): Current status of the translation
        progress (float, optional): Progress percentage. Defaults to 0.
        error (str, optional): Error message if any. Defaults to None.
    """
    if status == "success":
        redis_client.delete(f'translation_status:{job_id}')
        
    else:
        status_data = {
            'status': status,
            'progress': int(progress),
            'error': error
        }
        redis_client.set(f'translation_status:{job_id}', json.dumps(status_data))