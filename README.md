# CHIKU PRO - AI Desktop Companion 🤖

CHIKU PRO is an intelligent, voice-controlled Windows desktop assistant designed to handle productivity tasks, security, system automation, and more. It runs entirely locally by default, integrating smoothly with Ollama, but also supports cloud APIs (OpenAI/Gemini).

## ✨ Features
* **Multi-Factor Authentication:** Secure the assistant using Face Lock (LBPH), PIN, Password, or a combination.
* **Smart Voice Interactions:** Supports microphone input with fallback to keyboard typing. Handles text-to-speech output perfectly.
* **LLM Command Parsing:** Understands natural language statements ("Open Spotify and lower volume to 20") using Mistral (via Ollama), Gemini, or ChatGPT.
* **Desktop Automation:** Open/close apps, search the web, type text automatically, and execute shell commands.
* **System Monitoring:** Check RAM, CPU, Battery, take screenshots, and manage system volume.
* **Risk Analysis:** Built-in safeguards to warn before executing potentially dangerous shell commands.

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/chiku_pro.git
   cd chiku_pro
   ```

2. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```
   *Note: If `PyAudio` fails to install on Windows, run `pip install pipwin` followed by `pipwin install pyaudio`.*

3. **Run the assistant:**
   ```bash
   python main.py
   ```
   *(Or double-click CHIKU_Launcher.bat to run alongside Ollama).*

## 🧠 Using Offline AI (Ollama)
By default, CHIKU PRO connects to a local **Ollama** server on port `11434` running the `mistral` model. No API keys are needed!

If you wish to use OpenAI or Gemini instead, just set `OPENAI_API_KEY` or `GEMINI_API_KEY` in your environment variables, and CHIKU will prioritize the cloud LLM.

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📜 License
MIT License
