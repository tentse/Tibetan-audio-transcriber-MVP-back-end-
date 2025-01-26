from src.database.models import audio_segment, get_db, Project
from contextlib import contextmanager
from src.libs.update_status import update_translation_status

@contextmanager
def get_db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

async def write_audio_inference_to_db(email, project_id, audio_interence, model):

    audio_interence.sort(key=lambda segment: (segment[0], segment[1]))
    with get_db_session() as db:
        sequence = 0
        segments_to_add = []
        for segment in audio_interence:
            startTime = segment[0]
            endTime = segment[1]
            stt = segment[2]['text']
            if (stt != "" and stt[0] == "་"):
                stt = stt[1:]
            new_segment = audio_segment(
                email=email,
                sequence=sequence,
                project_id=project_id,
                start_time=startTime,
                end_time=endTime,
                transcription=stt,
            )
            segments_to_add.append(new_segment)
            sequence += 1

        db.add_all(segments_to_add)
        db.commit()

        update_translation_status(project_id, "success", 100, "NONE")

        # update the status field in the project table
        project = db.query(Project).filter(Project.project_id == project_id).first()
        project.project_status = "COMPLETED"
        db.commit()


        return {"progress":"100", "status": "success", "error": "NONE"}