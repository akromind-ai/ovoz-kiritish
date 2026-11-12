#!/bin/bash
# O'zbekcha ovozli kiritish — macOS uchun birinchi o'rnatish. Kengaytma chaqiradi: ornatish.sh "<data papka>"
set -e
DATA="$1"
SRC="$(cd "$(dirname "$0")" && pwd)"
[ -z "$DATA" ] && { echo "Data papka berilmadi"; exit 1; }
export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/Current/bin:$PATH"
mkdir -p "$DATA"
rm -f "$DATA/ornatildi.txt"

echo "[1/4] Python qidirilmoqda..."
PY=""
# Faqat 3.10–3.13: 3.14 da Intel Mac / macOS<14 uchun onnxruntime yo'q, 3.9 (Xcode) da kutubxonalar eski.
# 3.12 birinchi — onnxruntime macOS 11+ va Intel uchun ham bor.
for c in python3.12 python3.11 python3.13 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 13) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Python topilmadi — python.org dan o'rnatilmoqda (Mac paroli so'raladi)..."
  PKG="/tmp/python-3.12.10-macos11.pkg"
  curl -fL -o "$PKG" "https://www.python.org/ftp/python/3.12.10/python-3.12.10-macos11.pkg"
  sudo installer -pkg "$PKG" -target /
  rm -f "$PKG"
  PY="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12"
  [ -x "$PY" ] || { echo "Python o'rnatilmadi. https://www.python.org/downloads/macos/ dan qo'lda o'rnating."; exit 1; }
fi
"$PY" --version

echo "[2/4] Python muhiti yaratilmoqda..."
[ -x "$DATA/.venv/bin/python" ] || "$PY" -m venv "$DATA/.venv"
"$DATA/.venv/bin/python" -m pip install --upgrade pip

echo "[3/4] Kutubxonalar o'rnatilmoqda..."
"$DATA/.venv/bin/python" -m pip install -r "$SRC/requirements.txt"

echo "[4/4] O'zbekcha model yuklanmoqda (~1,5 GB, bir marta)..."
"$DATA/.venv/bin/python" -c "from faster_whisper import WhisperModel; WhisperModel('AlexAnoshka/fast-whisper-uz-rubaistt-v2-medium-ct2', device='cpu', compute_type='int8'); print('Model tayyor')"

echo ok > "$DATA/ornatildi.txt"
echo
echo "TAYYOR. Endi: Tizim sozlamalari → Maxfiylik va xavfsizlik → «Accessibility» va «Input Monitoring»"
echo "ro'yxatida Visual Studio Code ni yoqing (klavisha va matn qo'yish uchun). Mikrofon so'ralsa — ruxsat bering."
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" 2>/dev/null || true
