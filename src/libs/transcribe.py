import asyncio
import httpx
from fastapi import HTTPException
from typing import Tuple
import librosa
import soundfile as sf
import io
import os
from dotenv import load_dotenv
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


load_dotenv()

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
            'progress': progress,
            'error': error
        }
        redis_client.set(f'translation_status:{job_id}', json.dumps(status_data))

async def speech_to_text_tibetan(audio:str) -> dict:
    """Convert speech to text using the STT model."""

    AUTH = os.getenv("MODEL_AUTH")
    MODEL_URL = os.getenv("MODEL_URL")

    MODEL_AUTH = AUTH

    api_url = MODEL_URL
    response_time = 0

    headers = {
        "Content-Type": "audio/flac",
        "Authorization": f"Bearer {MODEL_AUTH}",
        "Access-Control-Allow-Origin": "*",
    }


    try:
        start_time = asyncio.get_event_loop().time()  # Record start time
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, headers=headers, content=audio)
            data = response.json()
            end_time = asyncio.get_event_loop().time()  # Record end time
            response_time = end_time - start_time  # Calculate response time
            return {"text":data['text'],"response_time":response_time}

    except httpx.HTTPStatusError as http_error:
        # Handle HTTP errors
        return {"error": "error in speech to text http", "details": str(http_error)}
    except Exception as e:
        # Handle other possible errors

        return {"error": "error in speech to text", "details": str(e)}


# async def transcribe(audio_data): 
#     # print(url)
#     # Read the audio file as binary
#     try:
#         # with open(url, "rb") as audio_file:
#         #     audio_data = audio_file.read()

#         # print(audio_data)

#         # flac_audio, flac_filename = await convert_to_flac(audio_data, "output_segment")

#         transript = await speech_to_text_tibetan(audio_data)
        
#         return transript

#     except Exception as error:
#         return str(error)

async def segment_and_transcribe(total_audio_segments, project_id, audio_data, time_stamp):
    try:
        # print('here')
        audio, sr = librosa.load(io.BytesIO(audio_data), sr=None)
        # print(time_stamp)
        transcribed_audio_list = []
        segment_completed_count = 0
        print('am here')
        for time in time_stamp:
            start_sample = int(time['start'] * sr)
            end_sample = int(time['end'] * sr)

            segmented_audio = audio[start_sample:end_sample]

            audio_bytes_io = io.BytesIO()
            write_segment_audio = sf.write(audio_bytes_io, segmented_audio, sr, format="WAV")  # Save as .wav (or other formats like .flac)
            audio_bytes_io.seek(0)

            read_audio = audio_bytes_io.read()
            # print(time)
            transcribe_text = await speech_to_text_tibetan(read_audio)

            # check if transcribe text contains error
            while 'error' in transcribe_text:
                transcribe_text = await speech_to_text_tibetan(read_audio)
            
            transcribed_audio_list.append([time['start'], time['end'], transcribe_text])

            segment_completed_count += 1

            update_translation_status(project_id, "PROCESSING", float(segment_completed_count / total_audio_segments * 100), "NONE")


        return transcribed_audio_list
    
    except Exception as e:
        return ({"error": "Error segmenting audio"}, e)
        # Segment the audio file
        # segments = await audio_segment(audio_data, time_stamp)
        # print(segments)
        # if segments == None:
        #     return {"error": "Error segmenting audio"}

        # Transcribe each segment
        # transcriptions = []
        # for segment in segments:
        #     transcription = await transcribe(segment)