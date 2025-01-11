from src.database.models import audio_segment

async def write_audio_inference_to_db(email, project_id, file, model, db):

    for segment in file:
        new_segment = audio_segment(email=email, project_id=project_id, start_time=segment[0], end_time=segment[1], transcription=segment[2]['text'], is_transcribed=True)
        db.add(new_segment)
        db.commit()
        db.refresh(new_segment)
    return {"message": "success"}