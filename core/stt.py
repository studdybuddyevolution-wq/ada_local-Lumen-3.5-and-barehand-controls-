"""Manual speech-to-text listener; no wake-word detector is used."""
from __future__ import annotations

import threading
from typing import Callable, Optional

from config import REALTIMESTT_MODEL, GRAY, RESET, CYAN, YELLOW, GREEN


class STTListener:
    """Local Whisper recorder that only runs while the user has pressed Wake."""

    def __init__(self, speech_callback: Callable[[str], None], error_callback: Optional[Callable[[str], None]] = None):
        self.speech_callback = speech_callback
        self.error_callback = error_callback
        self.running = False
        self.listening_thread = None
        self.recorder = None
        self.initialized = False

    def initialize(self) -> bool:
        if self.initialized and self.recorder is not None:
            return True
        try:
            from RealtimeSTT import AudioToTextRecorder
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"{CYAN}[STT] Creating local Whisper recorder on {device}...{RESET}")
            # No wake_words or wakeword_backend arguments: microphone use is explicit.
            self.recorder = AudioToTextRecorder(
                model=REALTIMESTT_MODEL,
                language="en",
                device=device,
                spinner=False,
            )
            self.initialized = True
            print(f"{GREEN}[STT] Recorder ready. Press Wake to start listening.{RESET}")
            return True
        except ImportError as exc:
            message = "RealTimeSTT is not installed. Run: pip install -r requirements.txt"
            print(f"{GRAY}[STT] {message} ({exc}){RESET}")
            if self.error_callback:
                self.error_callback(message)
            self.recorder = None
            self.initialized = False
            return False
        except Exception as exc:
            message = f"Could not open the microphone/Whisper recorder: {exc}"
            print(f"{GRAY}[STT] {message}{RESET}")
            if self.error_callback:
                self.error_callback(message)
            self.recorder = None
            self.initialized = False
            return False

    def start(self) -> bool:
        if self.running:
            return True
        # stop() closes the previous recorder; create a fresh one on re-wake.
        if not self.initialized or self.recorder is None:
            if not self.initialize():
                return False
        self.running = True
        self.listening_thread = threading.Thread(target=self._run_listener, name="LumenManualSTT", daemon=True)
        self.listening_thread.start()
        print(f"{CYAN}[STT] Manual microphone listening started.{RESET}")
        return True

    def _run_listener(self):
        try:
            while self.running and self.recorder is not None:
                text = self.recorder.text()
                if not self.running:
                    break
                if text and text.strip():
                    self.speech_callback(text.strip())
        except Exception as exc:
            if self.running:
                message = f"Speech recognition stopped: {exc}"
                print(f"{GRAY}[STT] {message}{RESET}")
                if self.error_callback:
                    self.error_callback(message)
            self.running = False

    def stop(self):
        self.running = False
        recorder, self.recorder = self.recorder, None
        if recorder is not None:
            try:
                recorder.shutdown()
            except Exception as exc:
                print(f"{YELLOW}[STT] Recorder shutdown warning: {exc}{RESET}")
        thread = self.listening_thread
        self.listening_thread = None
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=5.0)
        self.initialized = False
        print(f"{CYAN}[STT] Microphone closed; recorder released.{RESET}")
