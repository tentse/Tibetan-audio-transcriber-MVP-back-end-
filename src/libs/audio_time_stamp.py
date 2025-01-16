from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
import io

model = load_silero_vad()


async def test():
    return "Hello Testing"

async def get_time_stamp(audio_content):
    file_byte = audio_content
    audio_file = io.BytesIO(file_byte)
    audio_file = io.BytesIO(file_byte)
    wav = read_audio(audio_file)
    speech_timestamps = get_speech_timestamps(
        wav,
        model,
        return_seconds=True,  # Return speech timestamps in seconds (default is samples)
    )

    print(speech_timestamps)

    modify_time_stamp = []
    tmp = None

    for time in speech_timestamps:
        if (tmp == None):
            tmp = time
            continue
        start =  float(tmp['start'])
        end = float(time['end'])

        tmp_end = float(tmp['end'])
        next_start = float(time['start'])

        if (next_start - tmp_end) > 3.0:
            modify_time_stamp.append(tmp)
            tmp = time
        elif (end - start) > 4.0:
            modify_time_stamp.append(tmp)
            tmp = time
        else:
            tmp = {"start": start, "end": end}

    if (tmp != None):
        modify_time_stamp.append(tmp)

    print(speech_timestamps)
    print(modify_time_stamp)
    
    return modify_time_stamp
