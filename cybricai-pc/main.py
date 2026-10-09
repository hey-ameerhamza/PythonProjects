import sys
import os
import time
import asyncio
import tempfile
import subprocess
import pyautogui
import speech_recognition as sr
import pygame
from dotenv import load_dotenv

import edge_tts
from google import genai
from google.genai import types

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QPushButton, QLineEdit, QVBoxLayout, 
                             QHBoxLayout, QFrame)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer, QSize
from PyQt5.QtGui import QColor, QPainter, QPen, QFont, QLinearGradient, QBrush, QPixmap
from PyQt5.QtSvg import QSvgRenderer


# 0. INITIALIZE GEMINI CLIENT

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Gemini API Key Not Found! Contact Developer!")

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3.6-flash"

# Modern Neural Voice Setting (Options: "en-US-AriaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural")
NEURAL_VOICE = "en-US-AriaNeural"

# 1. OS TOOLS FOR GEMINI AI

def open_app(app_name: str) -> str:
    """Opens a Windows application like calculator, notepad, etc."""
    apps = {
        "calculator": "calc.exe",
        "notepad": "notepad.exe", 
        "camera": "camera.exe", 
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "explorer": "explorer.exe"
    }
    exe = apps.get(app_name.lower(), app_name)
    subprocess.Popen(exe, shell=True)
    return f"Opened {app_name}"

def type_text(text: str) -> str:
    """Types given text into the currently active Windows app."""
    time.sleep(1)
    pyautogui.write(text, interval=0.03)
    return f"Typed: '{text}' into active window."

def summarize_text(text: str) -> str:
    """Summarizes text using Gemini Flash."""
    res = client.models.generate_content(
        model=MODEL_NAME,
        contents=f"Summarize this concisely: {text}"
    )
    return res.text

# 2. ASYNC NEURAL TEXT-TO-SPEECH THREAD (PYGAME AUDIO)

class SpeakThread(QThread):
    finished_signal = pyqtSignal()

    def __init__(self, text, voice=NEURAL_VOICE):
        super().__init__()
        self.text = text
        self.voice = voice

    def run(self):
        asyncio.run(self._speak())

    async def _speak(self):
        temp_file = None
        try:
            communicate = edge_tts.Communicate(self.text, self.voice)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_file = fp.name
            
            await communicate.save(temp_file)

            # Play audio generated via Pygame
            pygame.mixer.init()
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                time.sleep(0.05)

            pygame.mixer.quit()

        except Exception as e:
            print(f"TTS Error: {e}")
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
            self.finished_signal.emit()


# 3. BACKGROUND GEMINI WORKER THREAD

class WorkerThread(QThread):
    chat_signal = pyqtSignal(str)
    speak_signal = pyqtSignal(str)

    def __init__(self, user_text):
        super().__init__()
        self.user_text = user_text

    def run(self):
        tools = [open_app, type_text, summarize_text]
        sys_inst = "You are Cybric AI, an advanced AI desktop assistant. Keep responses brief and helpful."
        
        try:
            chat = client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(
                    system_instruction=sys_inst,
                    tools=tools,
                    temperature=0.3
                )
            )

            response = chat.send_message(self.user_text)

            if response.text:
                self.chat_signal.emit(response.text)
                self.speak_signal.emit(response.text)

        except Exception as e:
            self.chat_signal.emit(f"Error: {str(e)}")

# 4. VOICE LISTENER THREAD

class VoiceListenerThread(QThread):
    voice_recognized = pyqtSignal(str)
    voice_error = pyqtSignal(str)

    def run(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
                text = recognizer.recognize_google(audio)
                self.voice_recognized.emit(text)
            except sr.WaitTimeoutError:
                self.voice_error.emit("Timeout")
            except Exception:
                self.voice_error.emit("Error")


# 5. CUSTOM ANIMATED INTERACTIVE ORB

class GlowingOrbWidget(QWidget):
    orb_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(380, 280)
        self.setCursor(Qt.PointingHandCursor)
        self.is_listening = False
        self.is_speaking = False
        self.wave_phase = 0
        
        # Timer to animate waves & pulses
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.orb_clicked.emit()

    def animate(self):
        self.wave_phase = (self.wave_phase + 4) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.width() // 2, self.height() // 2
        base_radius = 75

        if self.is_speaking:
            radius = base_radius + int((self.wave_phase % 40) / 2)
        elif self.is_listening:
            radius = base_radius + int((self.wave_phase % 20) / 2)
        else:
            radius = base_radius

        # Draw Soundwave Lines
        for i in range(-14, 15):
            if i == 0:
                continue
            x = cx + (i * 11)
            height = 18 + abs(i) * 2

            if self.is_speaking:
                height += (abs((self.wave_phase + i * 15) % 60) - 30) * 1.5
            elif self.is_listening:
                height += (abs((self.wave_phase + i * 10) % 30) - 15) * 1.2

            grad = QLinearGradient(x, cy - height, x, cy + height)
            grad.setColorAt(0, QColor(0, 240, 255, 180))
            grad.setColorAt(1, QColor(160, 32, 240, 180))
            
            painter.setPen(QPen(QBrush(grad), 3))
            painter.drawLine(x, int(cy - (height // 2)), x, int(cy + (height // 2)))

        # Glowing Orb Gradient
        grad_orb = QLinearGradient(cx - radius, cy - radius, cx + radius, cy + radius)
        if self.is_speaking:
            grad_orb.setColorAt(0.0, QColor(160, 32, 240, 255))
            grad_orb.setColorAt(0.5, QColor(0, 240, 255, 220))
            grad_orb.setColorAt(1.0, QColor(0, 128, 255, 255))
        else:
            grad_orb.setColorAt(0.0, QColor(0, 240, 255, 255))
            grad_orb.setColorAt(0.5, QColor(0, 128, 255, 220))
            grad_orb.setColorAt(1.0, QColor(140, 20, 252, 255))

        painter.setBrush(QBrush(grad_orb))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        # Tech Ring Accent Around Orb
        ring_radius = radius + 15
        ring_pen = QPen(QColor(0, 240, 255, 140 if self.is_listening else 60), 2)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(cx - ring_radius, cy - ring_radius, ring_radius * 2, ring_radius * 2)


# 6. APPLICATION GUI

class CybricAIGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CYBRIC AI")
        self.resize(1100, 700)
        self.setStyleSheet("background-color: #060913;")

        self.is_auto_listening = False
        self.voice_listener_thread = None
        self.speak_thread = None

        self.init_ui()

        # Trigger Welcome Message & Auto-Listen on startup
        QTimer.singleShot(800, self.trigger_welcome_sequence)

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 20, 30, 30)

        # Clean Header
        logo_layout = QVBoxLayout()
        logo_title = QLabel("CYBRIC AI")
        logo_title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        logo_title.setStyleSheet("color: #00F0FF; letter-spacing: 3px;")
        logo_title.setAlignment(Qt.AlignCenter)
        
        logo_sub = QLabel("YOUR AI ASSISTANT")
        logo_sub.setFont(QFont("Segoe UI", 9))
        logo_sub.setStyleSheet("color: #6C7D93; letter-spacing: 3px;")
        logo_sub.setAlignment(Qt.AlignCenter)

        logo_layout.addWidget(logo_title)
        logo_layout.addWidget(logo_sub)
        main_layout.addLayout(logo_layout)

        main_layout.addStretch()

        # Central Interactive Orb
        self.orb_widget = GlowingOrbWidget()
        self.orb_widget.orb_clicked.connect(self.toggle_orb_listening)
        main_layout.addWidget(self.orb_widget, alignment=Qt.AlignCenter)

        # Status Pill Badge
        self.status_pill = QLabel("Initializing...")
        self.status_pill.setStyleSheet("""
            QLabel {
                background-color: rgba(10, 25, 45, 220);
                color: #00F0FF;
                border: 1px solid #00F0FF;
                border-radius: 20px;
                padding: 8px 24px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        main_layout.addWidget(self.status_pill, alignment=Qt.AlignCenter)

        main_layout.addStretch()

        # Bottom Input Bar
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(8, 14, 28, 230);
                border: 1px solid #00F0FF;
                border-radius: 28px;
                padding: 4px;
            }
        """)
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(15, 5, 10, 5)

        # SVG Chat Icon
        chat_icon_label = QLabel()
        chat_svg = QSvgRenderer(
            b'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00F0FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>'
        )
        
        icon_pixmap = QPixmap(20, 20)
        icon_pixmap.fill(Qt.transparent)
        
        painter = QPainter(icon_pixmap)
        chat_svg.render(painter)
        painter.end()
        
        chat_icon_label.setPixmap(icon_pixmap)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a command or tap the orb to speak...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #A0C5E8;
                font-size: 14px;
                padding-left: 10px;
            }
        """)
        self.input_field.returnPressed.connect(self.handle_text_send)
        self.input_field.selectionChanged.connect(self.stop_listening)

        # Prompt Button
        send_btn = QPushButton(" Send Prompt")
        send_btn.setCursor(Qt.PointingHandCursor)
        send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00C8FF, stop:1 #A020F0);
                color: #FFFFFF;
                border: none;
                border-radius: 20px;
                padding: 10px 24px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00F0FF, stop:1 #B432FF);
            }
        """)
        send_btn.clicked.connect(self.handle_text_send)

        bottom_layout.addWidget(chat_icon_label)
        bottom_layout.addWidget(self.input_field)
        bottom_layout.addWidget(send_btn)

        main_layout.addWidget(bottom_frame)

    # CORE FLOW
    def trigger_welcome_sequence(self):
        welcome_msg = "Hey, welcome back! How can I help you today?"
        self.speak(welcome_msg, on_finished=self.start_listening)

    def speak(self, text, on_finished=None):
        self.orb_widget.is_speaking = True
        self.status_pill.setText("CYBRIC AI Speaking...")
        
        self.speak_thread = SpeakThread(text)
        if on_finished:
            self.speak_thread.finished_signal.connect(on_finished)
        self.speak_thread.finished_signal.connect(self.on_speak_finished)
        self.speak_thread.start()

    def on_speak_finished(self):
        self.orb_widget.is_speaking = False

    def toggle_orb_listening(self):
        if self.is_auto_listening:
            self.stop_listening()
        else:
            self.start_listening()

    def start_listening(self):
        if self.orb_widget.is_speaking:
            return
            
        self.is_auto_listening = True
        self.orb_widget.is_listening = True
        self.status_pill.setText("Listening...")

        self.voice_listener_thread = VoiceListenerThread()
        self.voice_listener_thread.voice_recognized.connect(self.on_voice_input)
        self.voice_listener_thread.voice_error.connect(self.on_voice_error)
        self.voice_listener_thread.start()

    def stop_listening(self):
        self.is_auto_listening = False
        self.orb_widget.is_listening = False
        if not self.orb_widget.is_speaking:
            self.status_pill.setText("Tap the orb or type to interact")

    def on_voice_input(self, text):
        self.stop_listening()
        self.status_pill.setText(f"You: {text}")
        self.process_user_prompt(text)

    def on_voice_error(self, err_type):
        if self.is_auto_listening:
            self.start_listening()

    def handle_text_send(self):
        text = self.input_field.text().strip()
        if text:
            self.stop_listening()
            self.input_field.clear()
            self.status_pill.setText(f"Processing: '{text}'")
            self.process_user_prompt(text)

    def process_user_prompt(self, text):
        self.worker_thread = WorkerThread(text)
        self.worker_thread.chat_signal.connect(lambda msg: self.status_pill.setText(f"CYBRIC AI: {msg[:35]}..."))
        self.worker_thread.speak_signal.connect(self.speak)
        self.worker_thread.start()

# 7. EXECUTION

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = CybricAIGUI()
    gui.show()
    sys.exit(app.exec_())