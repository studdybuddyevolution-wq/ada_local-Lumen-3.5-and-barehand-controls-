# Lumen

Lumen is a local-first Windows desktop assistant based on the A.D.A / Pocket AI project. Its default response engine runs on your PC:

- **Chat LLM:** Ollama with Qwen 3.5 4B
- **Intent router:** local FunctionGemma
- **Speech recognition:** local RealTimeSTT / Whisper
- **Speech output:** local Piper TTS
- **Actions:** local tools for timers, calendar, tasks, Kasa devices, web search, and the optional Barehands board

The microphone is closed at startup. Press **Wake** to open it and **Sleep** to stop listening and release the recorder. There is no wake-word detector or ambient wake-word listener.

## Windows setup

1. Install Python 3.10+ and Ollama.
2. Pull the default local model:

   \`\`\`powershell
   ollama pull qwen3.5:4b
   \`\`\`

3. From this repository folder:

   \`\`\`powershell
   python -m venv .venv
   .\\.venv\\Scripts\\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   \`\`\`

4. Optional NVIDIA acceleration: install a CUDA-enabled PyTorch build from the official PyTorch selector.
5. Launch Lumen:

   \`\`\`powershell
   python main.py
   \`\`\`

The first launch may download the local FunctionGemma and Piper voice assets. These are local model downloads, not paid API calls.

## Manual voice controls

Press **Wake** to create/open the local Whisper recorder and start listening. Press **Sleep** to stop recognition and shut down the recorder. Pressing Wake again creates a fresh recorder. The microphone is not opened at app startup; no Porcupine or OpenWakeWord service runs in the background.

## Switching response engines

The default mode is local. These commands work in the chat box and by voice after pressing Wake:

- **“Switch to local”** — Qwen 3.5 4B responds locally through Ollama.
- **“Switch to Gemini”** — optionally use Gemini for text generation.

The Gemini option is not Gemini Live audio-to-audio. In both modes, microphone speech recognition, FunctionGemma action routing, local tool execution, and Piper speech output remain on this PC. Only the natural-language response LLM changes.

Gemini is opt-in. The SDK is listed as a dependency, but Lumen will not select Gemini unless GEMINI_API_KEY is set. For a no-charge configuration, use a Google AI Studio project with no billing account and stay within the free-tier limits. Limits and model availability can change; quota failures are shown to you. Lumen does not silently fall back to a paid model. Do not configure a billing-enabled project if you require a hard no-charge setup.

Set the key only in your current PowerShell session, never in source code or settings files:

\`\`\`powershell
$env:GEMINI_API_KEY = "your-free-tier-key"
\`\`\`

The default model is gemini-3.6-flash; GEMINI_MODEL can override it. Local mode does not create a Gemini client or send conversation text to Google.

See [ENGINE_SWITCHING.md](ENGINE_SWITCHING.md) for more detail.

## Barehands board

Lumen can optionally control the separate [Barehands](https://github.com/jaredrhod/barehands) hand-tracked board. See [BAREHANDS_INTEGRATION.md](BAREHANDS_INTEGRATION.md). The bridge calls only the local 127.0.0.1 Barehands server; it does not call an AI API. The upstream checkout is installed separately and is excluded from this repository.

## Upstream acknowledgement

The original desktop application is A.D.A / Pocket AI by [nazirlouis](https://github.com/nazirlouis/ada_local). Lumen-specific changes are maintained in this fork.
