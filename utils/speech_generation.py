import os
import base64
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
from elevenlabs.types import VoiceSettings

load_dotenv()

elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)

def generate_speech_with_word_timings(text: str, audio_file_path: str):
    # 1. Use the timestamps-enabled endpoint
    response = elevenlabs.text_to_speech.convert_with_timestamps(
        text=text,
        voice_id="nPczCjzI2devNBz1zQrb",
        model_id="eleven_flash_v2_5",
        output_format="mp3_44100_128",
        voice_settings=VoiceSettings(
            speed=1.1,           # Increase speed (Range: 0.7 - 1.2)
            stability=0.5,      # Lower for more emotion/engagement
            # similarity_boost=0.8,# Higher for better voice clarity
            # style=0.2,           # Slightly amplify original speaker style
            # use_speaker_boost=True
        )
    )

    # 2. Extract audio and alignments
    audio_bytes = base64.b64decode(response.audio_base_64)
    alignment = response.alignment

    # 3. Save the audio file
    with open(audio_file_path, "wb") as f:
        f.write(audio_bytes)

    # 4. Group character timestamps into word timestamps
    words = []
    current_word = ""
    start_time = None

    characters = alignment.characters
    start_times = alignment.character_start_times_seconds
    end_times = alignment.character_end_times_seconds

    for char, s_time, e_time in zip(characters, start_times, end_times):
        if char == " ":
            if current_word:
                words.append({"word": current_word, "start": start_time, "end": last_end_time})
                current_word = ""
                start_time = None
        else:
            if start_time is None:
                start_time = s_time
            current_word += char
            last_end_time = e_time

    # Add the final word
    if current_word:
        words.append({"word": current_word, "start": start_time, "end": last_end_time})

    return audio_file_path, words

if __name__ == "__main__":
    # Example Usage
    file_path, word_timings = generate_speech_with_word_timings("Hello world, how are you!", "output.mp3")
    print(word_timings)