import sounddevice as sd
import numpy as np
import winsound
import time

target_voice = 0.04
cooldown_sec = 1.0

last_beep = 0

def audio_callback(indata, frames, time_info,status):
    global last_beep
    volume_rms = np.sqrt(np.mean(indata**2))
    print(f"Volume: {volume_rms:.4f}", end="\r")

    if volume_rms > target_voice:
        now = time.time()
        if now - last_beep > cooldown_sec:
            winsound.Beep(1000,200)
            last_beep = now

with sd.InputStream(callback=audio_callback, channels=1, samplerate=44100):
    print(f"Listening... beep triggers above volume {target_voice}. Press Ctrl+C to stop.")
    while True:
        pass            