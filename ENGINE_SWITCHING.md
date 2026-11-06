# Lumen engine switching

| Mode | Response LLM | Speech input | Tool router | Speech output |
|---|---|---|---|---|
| local (default) | Ollama / Qwen 3.5 4B | Local RealTimeSTT / Whisper | Local FunctionGemma | Local Piper |
| gemini (opt-in) | Gemini cloud text model | Local RealTimeSTT / Whisper | Local FunctionGemma | Local Piper |

The selected mode applies to new turns without an application restart. The Gemini option is text generation, not Gemini Live audio-to-audio. Lumen transcribes locally, routes actions locally, and uses local Piper output in both modes.

## Voice and chat commands

- switch to local, go offline, use the local engine
- switch to Gemini, go online, use cloud mode

A failed engine validation leaves the active mode unchanged. There is no silent cloud fallback from local mode.

## Local setup

\`\`\`powershell
ollama pull qwen3.5:4b
ollama list
\`\`\`

Before changing from Gemini to local, Lumen checks that Ollama is reachable and the configured chat model is installed. If not, it explains the issue and keeps the current mode.

## Optional Gemini free tier

Gemini mode requires GEMINI_API_KEY and the google-genai package. For a no-charge setup, create the key using a Google AI Studio project that has no billing account and remain within the model's published free tier. Free quotas can change and may be exhausted; a quota/provider error is surfaced rather than trying a paid provider.

\`\`\`powershell
$env:GEMINI_API_KEY = "your-free-tier-key"
\`\`\`

Optional model override: GEMINI_MODEL. Default: gemini-3.6-flash.

## Privacy

In local mode, conversation prompts are sent to the configured Ollama endpoint on your own computer. In Gemini mode, transcripts, conversation history, and tool-result context are sent to the Gemini API. Microphone capture, FunctionGemma routing, tool execution, and Piper speech output remain local in both modes.
