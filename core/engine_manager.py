"""Local-first response engine switching for Lumen.

local  -> local Ollama / Qwen. No cloud client, key, or request is used.
gemini -> optional Gemini text generation. STT, FunctionGemma tools, and Piper
          remain local. This is not Gemini Live audio-to-audio.
"""
from __future__ import annotations

import json
import os
import re
from typing import Iterator

import requests

from config import RESPONDER_MODEL

MODE_LOCAL = "local"
MODE_GEMINI = "gemini"
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"


def _settings():
    from core.settings_store import settings
    return settings


def current_mode() -> str:
    mode = str(_settings().get("engine.mode", MODE_LOCAL)).strip().lower()
    return mode if mode in (MODE_LOCAL, MODE_GEMINI) else MODE_LOCAL


def parse_engine_command(text: str):
    """Parse explicit engine-switch phrases, avoiding casual mentions."""
    value = re.sub(r"[^a-z0-9\s]", " ", str(text or "").lower())
    value = " ".join(value.split())
    if re.search(r"\b(?:switch|change|move|go|use|make)\b.*\b(?:local|offline)\b", value):
        return MODE_LOCAL
    if re.search(r"\b(?:switch|change|move|go|use|make)\b.*\b(?:gemini|cloud|online|remote)\b", value):
        return MODE_GEMINI
    return None


def _ollama_base() -> str:
    value = str(_settings().get("ollama_url", "http://localhost:11434")).rstrip("/")
    return value[:-4] if value.endswith("/api") else value


def _local_model() -> str:
    return str(_settings().get("models.chat", RESPONDER_MODEL) or RESPONDER_MODEL)


class EngineManager:
    """Validate, persist, and stream from the selected conversation engine."""

    def current_mode(self) -> str:
        return current_mode()

    def switch_mode(self, mode: str):
        mode = str(mode or "").strip().lower()
        if mode not in (MODE_LOCAL, MODE_GEMINI):
            return False, "Unknown engine. Choose local or gemini."
        old_mode = current_mode()
        if mode == old_mode:
            if mode == MODE_LOCAL:
                return True, "Lumen is already using its local engine: Qwen 3.5 4B, local routing, local speech recognition, and Piper."
            return True, "Lumen is already using Gemini for text responses. Speech input, tool routing, and Piper remain local."

        if mode == MODE_LOCAL:
            model = _local_model()
            try:
                response = requests.get(_ollama_base() + "/api/tags", timeout=4)
                response.raise_for_status()
                available = [item.get("name", "") for item in response.json().get("models", [])]
                if model not in available:
                    return False, (
                        "Local switch not applied: Ollama does not list " + model +
                        ". Run 'ollama pull " + model + "' and try again. Current mode remains " + old_mode + "."
                    )
            except Exception as exc:
                return False, (
                    "Local switch not applied: Ollama is not reachable at " + _ollama_base() +
                    ". Start Ollama and check that " + model + " is installed. Details: " + str(exc)
                )
            _settings().set("engine.mode", MODE_LOCAL)
            return True, (
                "Switched to the fully local engine. New responses use Qwen 3.5 4B through Ollama; "
                "speech recognition, FunctionGemma routing, actions, and Piper output remain on this PC. "
                "Conversation text is not sent to Gemini."
            )

        if not os.environ.get("GEMINI_API_KEY", "").strip():
            return False, (
                "Gemini mode was not enabled because GEMINI_API_KEY is not set. "
                "Lumen remains in local mode. You can keep using Qwen without an API key."
            )
        try:
            from google import genai
            if genai is None:
                raise ImportError("google-genai could not be imported")
        except Exception as exc:
            return False, (
                "Gemini mode was not enabled because the google-genai package is unavailable. "
                "Run 'pip install google-genai' and try again. Details: " + str(exc)
            )
        _settings().set("engine.mode", MODE_GEMINI)
        return True, (
            "Switched to Gemini cloud text responses. Microphone capture, FunctionGemma routing, "
            "local actions, and Piper speech output remain on this PC. Say 'switch to local' to return."
        )

    def handle_switch_command(self, text: str):
        mode = parse_engine_command(text)
        if mode is None:
            return None
        _, message = self.switch_mode(mode)
        return message

    def stream_chat(self, messages: list, thinking: bool = False) -> Iterator[dict]:
        """Yield text chunks from the configured engine; never silently fall back."""
        if current_mode() == MODE_LOCAL:
            yield from self._stream_ollama(messages, thinking)
        else:
            yield from self._stream_gemini(messages)

    def _stream_ollama(self, messages: list, thinking: bool):
        payload = {
            "model": _local_model(),
            "messages": messages,
            "stream": True,
            "think": bool(thinking),
            "keep_alive": "5m",
        }
        with requests.post(
            _ollama_base() + "/api/chat",
            json=payload,
            stream=True,
            timeout=(10, 300),
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                item = json.loads(line.decode("utf-8"))
                message = item.get("message") or {}
                if message.get("thinking"):
                    yield {"thinking": message["thinking"]}
                if message.get("content"):
                    yield {"content": message["content"]}

    def _stream_gemini(self, messages: list):
        from google import genai
        from google.genai import types

        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("Gemini mode is selected but GEMINI_API_KEY is not set.")
        client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(timeout=120_000),
        )
        system_parts = []
        contents = []
        for message in messages:
            role = str(message.get("role", "user")).lower()
            content = str(message.get("content", ""))
            if not content:
                continue
            if role == "system":
                system_parts.append(content)
            elif role in ("assistant", "model"):
                contents.append({"role": "model", "parts": [{"text": content}]})
            else:
                contents.append({"role": "user", "parts": [{"text": content}]})
        if not contents:
            contents = [{"role": "user", "parts": [{"text": "Hello"}]}]
        config = types.GenerateContentConfig(
            system_instruction="\n\n".join(system_parts) if system_parts else None,
            temperature=0.7,
        )
        model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
        for chunk in client.models.generate_content_stream(model=model, contents=contents, config=config):
            text = getattr(chunk, "text", None)
            if text:
                yield {"content": text}


engine_manager = EngineManager()
