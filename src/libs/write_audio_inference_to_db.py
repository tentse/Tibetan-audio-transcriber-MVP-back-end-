from src.database.models import audio_segment, get_db
from contextlib import contextmanager

@contextmanager
def get_db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

async def write_audio_inference_to_db(email, project_id, file, model):

    with get_db_session() as db:
        segments_to_add = []
        for segment in file:
            if ('error' in segment[2]):
                print("error: error in speech to text details", str(segment))
                continue
            startTime = segment[0]
            endTime = segment[1]
            stt = segment[2]['text']
            new_segment = audio_segment(
                email=email,
                project_id=project_id,
                start_time=startTime,
                end_time=endTime,
                transcription=stt,
                is_transcribed=True
            )
            segments_to_add.append(new_segment)

        db.add_all(segments_to_add)
        db.commit()
        return {"message": "success"}