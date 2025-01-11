from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
import io

model = load_silero_vad()


async def test():
    return "Hello Testing"

async def get_time_stamp(audio_file):
    file_byte = await audio_file.read()
    audio_file = io.BytesIO(file_byte)
    audio_file = io.BytesIO(file_byte)
    wav = read_audio(audio_file)
    speech_timestamps = get_speech_timestamps(
        wav,
        model,
        return_seconds=True,  # Return speech timestamps in seconds (default is samples)
    )
    return speech_timestamps
