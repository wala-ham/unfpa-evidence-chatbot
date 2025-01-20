# speech_to_text.py
import os
import pyaudio
from google.cloud import speech
from google.cloud.speech import RecognitionConfig, StreamingRecognitionConfig, StreamingRecognizeRequest

# Set up Google Cloud credentials (set the environment variable for your credentials)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r"C:\Users\WalaHammemi\OneDrive - Naxxum\Bureau\Optimisation\Agents\service-account-key.json"

# Initialize Speech-to-Text client
client = speech.SpeechClient()

# Set up microphone for audio input
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

# Function to record audio and return transcription
def record_audio():
    languages = ["en-US", "fr-FR", "es-ES"]
    config = RecognitionConfig(
        encoding=RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=languages[0],  # Default language
        alternative_language_codes=languages[1:]  # List of alternative languages
    )
    streaming_config = StreamingRecognitionConfig(config=config)

    # Generate audio from the microphone stream
    def generate_audio():
        while True:
            data = stream.read(CHUNK)
            yield StreamingRecognizeRequest(audio_content=data)

    requests = generate_audio()
    responses = client.streaming_recognize(streaming_config, requests)

    # Process the responses
    for response in responses:
        for result in response.results:
            if result.is_final:
                transcript = result.alternatives[0].transcript
                return transcript
    return None
