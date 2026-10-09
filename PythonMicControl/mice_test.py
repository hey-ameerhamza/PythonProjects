import sounddevice as sd
import numpy as np

def audio_callback(indata, frames, time, status):
    volume_rms =  np.sqrt(np.mean(indata**2))

    print(f"Volume: {volume_rms:.4f}", end="\r")

with sd.InputStream(callback=audio_callback, channels=1, samplerate=44100):
    print("Listening... speak into your microphone. Press Ctrl + C to stop.")

    while True:
        pass