@echo off
echo ============================================
echo  WhisperWriter GPU Setup (Windows + CUDA)
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.10 or 3.11 from python.org
    echo         Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create venv
    pause
    exit /b 1
)

echo [2/4] Upgrading pip...
venv\Scripts\python.exe -m pip install --upgrade pip

echo [3/4] Installing PyTorch with CUDA 12.1...
venv\Scripts\pip.exe install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
if errorlevel 1 (
    echo [WARNING] CUDA install failed. Trying CPU-only PyTorch...
    venv\Scripts\pip.exe install torch torchvision torchaudio
)

echo [4/4] Installing dependencies...
venv\Scripts\pip.exe install -r requirements.txt

echo.
echo ============================================
echo  Verifying installation...
echo ============================================
venv\Scripts\python.exe -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0)}' if torch.cuda.is_available() else 'No GPU - will use CPU (slower)')"
venv\Scripts\python.exe -c "from faster_whisper import WhisperModel; print('faster-whisper: OK')"

echo.
echo ============================================
echo  Setup complete!
echo ============================================
echo.
echo To run: double-click WhisperWriter.bat
echo To create desktop shortcut: right-click create-shortcut.ps1 ^> Run with PowerShell
echo.
pause
