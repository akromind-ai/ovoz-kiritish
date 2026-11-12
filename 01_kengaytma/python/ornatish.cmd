@echo off
rem Ozbekcha ovozli kiritish - birinchi ornatish. Kengaytma chaqiradi: ornatish.cmd "<data papka>"
rem Faqat lotin harflari (cmd kirillni buzadi).
setlocal
set "DATA=%~1"
set "SRC=%~dp0"
if "%DATA%"=="" (echo Data papka berilmadi & exit /b 1)
if not exist "%DATA%" mkdir "%DATA%"
del "%DATA%\ornatildi.txt" >nul 2>&1

echo [1/5] Python qidirilmoqda...
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY ( where python >nul 2>&1 && set "PY=python" )
if not defined PY (
  echo.
  echo Python topilmadi. https://www.python.org/downloads/ dan Python 3.11+ ornating,
  echo "Add python.exe to PATH" ni belgilang, VS Code ni qayta oching va "Ovoz: Ornatish" ni bosing.
  exit /b 1
)
%PY% --version

echo [2/5] Python muhiti yaratilmoqda...
if not exist "%DATA%\.venv\Scripts\python.exe" %PY% -m venv "%DATA%\.venv" || (echo .venv yaratilmadi & exit /b 1)
"%DATA%\.venv\Scripts\python.exe" -m pip install --upgrade pip

echo [3/5] Kutubxonalar ornatilmoqda...
"%DATA%\.venv\Scripts\python.exe" -m pip install -r "%SRC%requirements.txt" || (echo Kutubxonalar ornatilmadi & exit /b 1)

echo [4/5] Videokarta tekshirilmoqda...
where nvidia-smi >nul 2>&1 && (
  echo NVIDIA topildi - GPU kutubxonalari ornatilmoqda...
  "%DATA%\.venv\Scripts\python.exe" -m pip install -r "%SRC%requirements-gpu.txt"
) || echo NVIDIA yoq - CPU da ishlaydi (sekinroq).

echo [5/5] Ozbekcha model yuklanmoqda (~1,5 GB, bir marta)...
"%DATA%\.venv\Scripts\python.exe" -c "from faster_whisper import WhisperModel; WhisperModel('AlexAnoshka/fast-whisper-uz-rubaistt-v2-medium-ct2', device='cpu', compute_type='int8'); print('Model tayyor')" || (echo Model yuklanmadi & exit /b 1)

echo ok> "%DATA%\ornatildi.txt"
echo.
echo TAYYOR. Terminalni yopishingiz mumkin - ovozli kiritish ozi yoqiladi.
