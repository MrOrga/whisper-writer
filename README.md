# <img src="./assets/ww-logo.png" alt="WhisperWriter icon" width="25" height="25"> WhisperWriter (GPU-Fixed Fork)

Fork of [savbell/whisper-writer](https://github.com/savbell/whisper-writer) with **critical fixes for Windows + NVIDIA GPU**.

WhisperWriter is a speech-to-text app that uses [OpenAI's Whisper model](https://openai.com/research/whisper) via [faster-whisper](https://github.com/SYSTRAN/faster-whisper/) to auto-transcribe your voice to any active window in real-time.

Press a hotkey (`Ctrl+Shift+Space`), talk, and the text appears where your cursor is.

## What This Fork Fixes

The original repo crashes on Windows with NVIDIA GPUs due to two issues:

| Bug | Symptom | Fix |
|-----|---------|-----|
| CUDA DLLs not found | `Could not load library cublas64_12.dll` | Auto-adds nvidia cublas bin to PATH + `os.add_dll_directory()` at startup |
| Qt + CUDA segfault | App crashes silently on launch | Pre-loads CUDA model BEFORE PyQt5 initializes (Qt OpenGL conflicts with CUDA init) |

Both fixes are in `src/main.py` (clearly marked with `# PATCH:` comments).

## Quick Setup (Windows)

### Prerequisites

- **Python 3.10 or 3.11** from [python.org](https://www.python.org/downloads/) (check "Add Python to PATH")
- **NVIDIA GPU** with updated drivers (optional, CPU works too but slower)
- **Git** from [git-scm.com](https://git-scm.com/downloads)

### Install

```bash
git clone https://github.com/MrOrga/whisper-writer.git
cd whisper-writer
setup.bat
```

That's it. The setup script:
1. Creates a Python virtual environment
2. Installs PyTorch with CUDA 12.1 (falls back to CPU if no GPU)
3. Installs all dependencies
4. Verifies everything works

### Run

**Option A:** Double-click `WhisperWriter.bat`

**Option B:** Create a desktop shortcut (runs silently, no terminal window):
```powershell
# Right-click create-shortcut.ps1 > Run with PowerShell
```

### First Launch

1. A Settings window opens on first run
2. Configure your preferences (defaults work fine)
3. Click Save, then Start
4. Press `Ctrl+Shift+Space` to start recording
5. Talk, pause, and the text appears in your active window

## Recording Modes

- **continuous** (default): Records until you pause. Transcribes, then starts recording again. Press hotkey to stop.
- **voice_activity_detection**: Records until you pause. Stops. Press hotkey to record again.
- **press_to_toggle**: Press hotkey to start, press again to stop.
- **hold_to_record**: Hold hotkey to record, release to stop.

## Configuration

Settings are stored in `src/config.yaml` (auto-created on first run). You can also edit via the Settings window.

Key options:
- **Model**: `tiny`, `base`, `small`, `medium`, `large-v3` (bigger = more accurate but slower)
- **Language**: auto-detect or set ISO code (e.g., `it` for Italian, `en` for English)
- **Device**: `auto` (recommended), `cuda`, or `cpu`
- **API mode**: Can use OpenAI API instead of local model (needs API key in `.env`)

## Troubleshooting

### "Python not found"
Make sure Python is in your PATH. Open a new terminal and run `python --version`.

### App crashes silently
This fork should fix the crash. If it still happens, run from terminal to see the error:
```bash
venv\Scripts\python.exe src\main.py
```

### Slow transcription
- Make sure you're using GPU (check terminal output for `CUDA available: True`)
- Use a smaller model (`base` or `small` instead of `medium`)
- Close other GPU-heavy apps

### No microphone input
Run `python -m sounddevice` inside the venv to list audio devices. Set the correct `sound_device` index in Settings.

## Credits

Original project by [savbell](https://github.com/savbell/whisper-writer). GPU fixes by [MrOrga](https://github.com/MrOrga).
