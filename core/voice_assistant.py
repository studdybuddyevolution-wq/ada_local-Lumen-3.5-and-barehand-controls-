"""Lumen voice assistant: manual mic, local actions, selectable response engine."""
import threading
from typing import Optional

from PySide6.QtCore import QObject, Signal

from config import MAX_HISTORY, GRAY, RESET, CYAN, GREEN
from core.stt import STTListener
from core.llm import route_query, should_bypass_router
from core.model_persistence import ensure_qwen_loaded, mark_qwen_used
from core.tts import tts, SentenceBuffer
from core.function_executor import executor as function_executor
from core.engine_manager import engine_manager, MODE_LOCAL

ACTION_FUNCTIONS = {
    "control_light", "set_timer", "set_alarm", "create_calendar_event",
    "add_task", "web_search", "barehands_control",
}


class VoiceAssistant(QObject):
    listening_state_changed = Signal(bool)
    speech_recognized = Signal(str)
    processing_started = Signal()
    processing_finished = Signal()
    error_occurred = Signal(str)
    timer_set = Signal(int, str)
    alarm_added = Signal()
    calendar_updated = Signal()
    task_added = Signal()

    def __init__(self):
        super().__init__()
        self.stt_listener: Optional[STTListener] = None
        self.running = False
        self.messages = [{
            "role": "system",
            "content": "You are Lumen, a helpful desktop assistant. Respond in short, complete, conversational sentences.",
        }]
        self.current_session_id = None

    def initialize(self) -> bool:
        """Prepare local audio without activating the microphone."""
        try:
            if self.stt_listener is None:
                self.stt_listener = STTListener(
                    speech_callback=self._on_speech,
                    error_callback=self._on_stt_error,
                )
            if not self.stt_listener.initialized and not self.stt_listener.initialize():
                return False
            if not tts.piper_exe:
                tts.initialize()
            tts.toggle(True)
            return True
        except Exception as exc:
            message = f"Voice initialization failed: {exc}"
            print(f"{GRAY}[VoiceAssistant] {message}{RESET}")
            self.error_occurred.emit(message)
            return False

    def start(self) -> bool:
        """Wake Lumen: explicitly open microphone capture."""
        if self.running:
            return True
        if self.stt_listener is None:
            if not self.initialize():
                return False
        if not self.stt_listener.start():
            self.running = False
            self.listening_state_changed.emit(False)
            return False
        self.running = True
        self.listening_state_changed.emit(True)
        print(f"{GREEN}[VoiceAssistant] Microphone awake. Manual listening enabled.{RESET}")
        return True

    def stop(self):
        """Sleep Lumen and close the microphone."""
        self.running = False
        if self.stt_listener:
            self.stt_listener.stop()
        self.listening_state_changed.emit(False)
        print(f"{GRAY}[VoiceAssistant] Sleeping. Microphone closed.{RESET}")

    def _on_stt_error(self, message: str):
        self.running = False
        self.listening_state_changed.emit(False)
        self.error_occurred.emit(message)

    def _on_speech(self, text: str):
        text = str(text or "").strip()
        if not text:
            return
        self.speech_recognized.emit(text)
        self.processing_started.emit()
        threading.Thread(target=self._process_query, args=(text,), name="LumenVoiceTurn", daemon=True).start()

    def _process_query(self, user_text: str):
        try:
            switch_reply = engine_manager.handle_switch_command(user_text)
            if switch_reply is not None:
                self.messages.append({"role": "user", "content": user_text})
                self.messages.append({"role": "assistant", "content": switch_reply})
                tts.queue_sentence(switch_reply)
                self.processing_finished.emit()
                return

            if should_bypass_router(user_text):
                func_name, params = "nonthinking", {"prompt": user_text}
            else:
                func_name, params = route_query(user_text)
            print(f"{GRAY}[VoiceAssistant] Routed to: {func_name}{RESET}")

            if func_name in ACTION_FUNCTIONS:
                result = function_executor.execute(func_name, params)
                self._generate_response_with_context(func_name, result, user_text, enable_thinking=(func_name == "web_search"))
                if func_name == "set_timer" and result.get("success"):
                    data = result.get("data", {})
                    self.timer_set.emit(data.get("seconds", 0), data.get("label", "Timer"))
                elif func_name == "set_alarm" and result.get("success"):
                    self.alarm_added.emit()
                elif func_name == "create_calendar_event" and result.get("success"):
                    self.calendar_updated.emit()
                elif func_name == "add_task" and result.get("success"):
                    self.task_added.emit()
            elif func_name == "get_system_info":
                result = function_executor.execute(func_name, params)
                self._generate_response_with_context(func_name, result, user_text, enable_thinking=True)
            elif func_name in ("thinking", "nonthinking"):
                self._stream_qwen_response(user_text, func_name == "thinking")
            else:
                self._stream_qwen_response(user_text, False)
        except Exception as exc:
            message = f"Error processing voice request: {exc}"
            print(f"{GRAY}[VoiceAssistant] {message}{RESET}")
            self.error_occurred.emit(message)
            self.processing_finished.emit()

    def _generate_response_with_context(self, func_name: str, result: dict, user_text: str, enable_thinking: bool = False):
        success = result.get("success", False)
        message = result.get("message", "")
        if func_name == "get_system_info" and success:
            data = result.get("data", {})
            parts = []
            if data.get("timers"): parts.append(f"Active timers: {data['timers']}")
            if data.get("alarms"): parts.append(f"Alarms: {data['alarms']}")
            if data.get("calendar_today"): parts.append(f"Today's events: {data['calendar_today']}")
            if data.get("tasks"):
                pending = [item for item in data["tasks"] if not item.get("completed")]
                parts.append(f"Pending tasks: {len(pending)} items")
            if data.get("smart_devices"):
                on_devices = [item["name"] for item in data["smart_devices"] if item.get("is_on")]
                parts.append(f"Devices on: {on_devices if on_devices else 'none'}")
            if data.get("weather"):
                weather = data["weather"]
                parts.append(f"Weather: {weather.get('temp')}°, {weather.get('condition')}")
            if data.get("news"):
                parts.append("Top news: " + ", ".join(item.get("title", "")[:50] for item in data["news"][:3]))
            context_msg = "\n".join(parts) if parts else "No system information available."
        else:
            context_msg = f"Function {func_name} executed. Success: {success}. Result: {message}"
        self._append_context_and_stream(context_msg, user_text, enable_thinking)

    def _stream_qwen_response(self, user_text: str, enable_thinking: bool):
        self._append_context_and_stream("", user_text, enable_thinking)

    def _append_context_and_stream(self, context_msg: str, user_text: str, enable_thinking: bool):
        if len(self.messages) > MAX_HISTORY:
            self.messages = [self.messages[0]] + self.messages[-(MAX_HISTORY - 1):]
        prompt = (context_msg + "\n\n" if context_msg else "") + user_text
        self.messages.append({"role": "user", "content": prompt})
        self._stream_engine_response(enable_thinking)

    def _stream_engine_response(self, enable_thinking: bool):
        try:
            if engine_manager.current_mode() == MODE_LOCAL:
                if not ensure_qwen_loaded():
                    raise RuntimeError("Could not load local Qwen. Check Ollama and run ollama pull qwen3.5:4b.")
                mark_qwen_used()
            sentence_buffer = SentenceBuffer()
            full_response = ""
            for item in engine_manager.stream_chat(self.messages, thinking=enable_thinking):
                content = item.get("content")
                if content:
                    full_response += content
                    for sentence in sentence_buffer.add(content):
                        tts.queue_sentence(sentence)
            remainder = sentence_buffer.flush()
            if remainder:
                tts.queue_sentence(remainder)
            self.messages.append({"role": "assistant", "content": full_response})
            if engine_manager.current_mode() == MODE_LOCAL:
                mark_qwen_used()
            print(f"{GREEN}[VoiceAssistant] Response generated using {engine_manager.current_mode()}.{RESET}")
        except Exception as exc:
            message = f"Response engine failed: {exc}"
            print(f"{GRAY}[VoiceAssistant] {message}{RESET}")
            self.error_occurred.emit(message)
        finally:
            self.processing_finished.emit()


voice_assistant = VoiceAssistant()
