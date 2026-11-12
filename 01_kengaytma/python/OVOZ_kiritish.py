"""Ўзбекча овозли киритиш (Windows ва macOS).

Гарячая клавиша -> микрофон -> Whisper (GPU) -> матн курсор турган жойга.
Созламалар: OVOZ_config.json
"""
import os, sys, re, json, glob, site, time, threading, ctypes, tempfile, subprocess
IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
if IS_WIN:
    import winsound

HERE = os.path.dirname(os.path.abspath(__file__))
# Foydalanuvchi ma'lumoti (sozlama, log) — VS Code kengaytmasi OVOZ_DATA ni beradi; bo'lmasa dastur papkasi.
DATA = os.environ.get("OVOZ_DATA") or HERE
os.makedirs(DATA, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


class _Tee:
    """Экранга ва OVOZ_log.txt га бир вақтда ёзади."""
    def __init__(self, stream, log):
        self.stream, self.log = stream, log

    def write(self, s):
        self.stream.write(s)
        self.log.write(s); self.log.flush()

    def flush(self):
        self.stream.flush()


_log = open(os.path.join(DATA, "OVOZ_log.txt"), "a", encoding="utf-8")
_log.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
sys.stdout = _Tee(sys.stdout, _log)
sys.stderr = _Tee(sys.stderr, _log)

# pip орқали ўрнатилган CUDA DLL'ларини (cuBLAS, cuDNN) топиш
for sp in site.getsitepackages():
    for b in glob.glob(os.path.join(sp, "nvidia", "*", "bin")):
        os.add_dll_directory(b)
        os.environ["PATH"] = b + os.pathsep + os.environ["PATH"]

import numpy as np
import sounddevice as sd
import pyperclip
if IS_WIN:
    import keyboard
else:
    from pynput import keyboard as pk

_cfg = os.path.join(DATA, "OVOZ_config.json")
if not os.path.exists(_cfg):
    import shutil
    shutil.copy(os.path.join(HERE, "OVOZ_config.default.json"), _cfg)
with open(_cfg, encoding="utf-8") as f:
    CFG = json.load(f)
HOTKEY = CFG.get("hotkey_mac", "ctrl+shift+space") if IS_MAC else CFG["hotkey"]


def beep(freq, ms):
    if IS_WIN:
        winsound.Beep(freq, ms)
    elif IS_MAC:
        snd = {880: "Tink", 600: "Pop", 300: "Bottle", 220: "Basso"}.get(freq, "Tink")
        subprocess.Popen(["afplay", f"/System/Library/Sounds/{snd}.aiff"])
    else:
        print("\a", end="", flush=True)

RATE = 16000
MAX_SECONDS = 300


# ---------------------------------------------------------------- транслитерация
LAT2CYR = dict(zip("abdfghijklmnopqrstuvxyz",
                   "абдфгҳижклмнопқрстувхйз"))
VOWELS = set("aeiouў")
APOS = re.compile(r"[ʻʼ‘’`´]")


def _word_to_cyr(w):
    low = w.lower()
    # Ўзбек лотинида йўқ ҳарфлар (w, ch'сиз c) — бу инглизча сўз, тегмаймиз
    if "w" in low or re.search(r"c(?!h)", low):
        return w
    out, i, n = [], 0, len(low)
    while i < n:
        c, nx = low[i], low[i + 1] if i + 1 < n else ""
        nx2 = low[i + 2] if i + 2 < n else ""
        if c in "og" and nx == "'":
            out.append("ў" if c == "o" else "ғ"); i += 2
        elif c == "s" and nx == "'" and nx2 == "h":
            out.append("сҳ"); i += 3
        elif c in "sc" and nx == "h":
            out.append("ш" if c == "s" else "ч"); i += 2
        elif c == "y" and nx and nx in "oaue" and not (nx == "o" and nx2 == "'"):
            out.append({"o": "ё", "a": "я", "u": "ю", "e": "е"}[nx]); i += 2
        elif c == "e":
            out.append("э" if i == 0 or low[i - 1] in VOWELS else "е"); i += 1
        elif c == "'":
            out.append("ъ" if i > 0 else ""); i += 1
        else:
            out.append(LAT2CYR.get(c, c)); i += 1
    res = "".join(out)
    if len(w) > 1 and w.isupper():
        return res.upper()
    if w[0].isupper():
        return res[:1].upper() + res[1:]
    return res


def to_cyrillic(text):
    text = APOS.sub("'", text)
    keep = {}
    for k, word in enumerate(sorted(CFG.get("keep_latin", []), key=len, reverse=True)):
        tag = f"\x00{k}\x00"
        # Фақат бутун сўз: «гапириш» ичидаги «api» ни «API» га алмаштирмаслик учун
        pat = r"(?<![^\W\d_])" + re.escape(word) + r"(?![^\W\d_])"
        text, cnt = re.subn(pat, tag, text, flags=re.IGNORECASE)
        if cnt:
            keep[tag] = word
    text = re.sub(r"[A-Za-z][A-Za-z']*", lambda m: _word_to_cyr(m.group()), text)
    for tag, word in keep.items():
        text = text.replace(tag, word)
    return text


def capitalize_sentences(text):
    return re.sub(r"(^|[.!?]\s+)(\w)", lambda m: m.group(1) + m.group(2).upper(), text)


# ---------------------------------------------------------------- модель
model = None
model_ready = threading.Event()


def load_model():
    global model
    from faster_whisper import WhisperModel
    name = CFG["model"]
    print(f"Модель юкланмоқда: {name} (биринчи марта юклаб олинади, бир неча минут)...", flush=True)
    try:
        model = WhisperModel(name, device="cuda", compute_type="float16")
    except Exception as e:
        print(f"GPU ишламади ({e}), CPU'га ўтилмоқда (секинроқ)...", flush=True)
        model = WhisperModel(name, device="cpu", compute_type="int8")
    model.transcribe(np.zeros(RATE, dtype=np.float32), language=CFG["language"])  # қиздириш
    model_ready.set()
    set_state(state)
    print(f"Тайёр. {HOTKEY} — ёзишни бошлаш/тугатиш, {CFG['cancel_key']} — бекор қилиш.", flush=True)


# ---------------------------------------------------------------- ёзиб олиш
state = "idle"  # idle | recording | busy
lock = threading.Lock()
chunks = []
stream = None

# VS Code тугмаси (ovoz-vscode кенгайтмаси) шу файллардан ҳолатни ўқийди
TMP = tempfile.gettempdir()
PID_FILE = os.path.join(TMP, "OVOZ_kiritish.pid")
STATE_FILE = os.path.join(TMP, "OVOZ_state.txt")


def set_state(s):
    global state
    state = s
    shown = "loading" if s == "idle" and not model_ready.is_set() else ("ready" if s == "idle" else s)
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(shown)
    except OSError:
        pass


def _audio_cb(indata, frames, t, status):
    chunks.append(indata[:, 0].copy())
    if len(chunks) * frames > MAX_SECONDS * RATE:
        threading.Thread(target=toggle, daemon=True).start()


def start_recording():
    global stream
    chunks.clear()
    stream = sd.InputStream(samplerate=RATE, channels=1, dtype="float32", callback=_audio_cb)
    stream.start()
    set_state("recording")
    beep(880, 120)
    print("🎙  Гапиринг...", flush=True)


def stop_stream():
    global stream
    if stream:
        stream.stop(); stream.close(); stream = None


def active_window():
    if not IS_WIN:
        return ""
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    buf = ctypes.create_unicode_buffer(256)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


_last_toggle = 0.0


def toggle():
    global state, _last_toggle
    # Клавишани ушлаб туришда Windows уни такрорлайди — яқин босишларни ташлаймиз
    now = time.monotonic()
    if now - _last_toggle < 0.5:
        return
    _last_toggle = now
    print(f"[{time.strftime('%H:%M:%S')}] клавиша ({state}) — ойна: {active_window()}", flush=True)
    with lock:
        if state == "idle":
            try:
                start_recording()
            except Exception as e:
                beep(220, 300)
                print(f"Микрофон хатоси: {e}", flush=True)
        elif state == "recording":
            stop_stream()
            set_state("busy")
            beep(600, 100)
            audio = np.concatenate(chunks) if chunks else np.zeros(0, np.float32)
            threading.Thread(target=process, args=(audio,), daemon=True).start()


def cancel(_=None):
    global state
    with lock:
        if state == "recording":
            stop_stream()
            set_state("idle")
            beep(300, 150)
            print("✖  Бекор қилинди.", flush=True)


LAST_WAV = os.path.join(TMP, "OVOZ_oxirgi_yozuv.wav")


def save_wav(audio, path):
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())


def transcribe(audio):
    # VAD'сиз ишлатманг: шовқиндан «ассалому алайкум» каби матн ўйлаб топади (синалган)
    segs, _ = model.transcribe(audio, language=CFG["language"], beam_size=CFG.get("beam_size", 5),
                               vad_filter=True, vad_parameters={"threshold": 0.35},
                               condition_on_previous_text=False)
    # Шовқиндан «ўйлаб топилган» сегментларни ташлаймиз
    return " ".join(s.text.strip() for s in segs
                    if not (s.no_speech_prob > 0.6 and s.avg_logprob < -0.7)).strip()


def process(audio):
    global state
    try:
        if len(audio) < RATE * 0.4:
            print("Жуда қисқа ёзув, ўтказиб юборилди.", flush=True)
            return
        if not model_ready.is_set():
            print("Модель ҳали юкланмоқда, кутилмоқда...", flush=True)
            model_ready.wait()
        peak = float(np.abs(audio).max())
        rms = float(np.sqrt(np.mean(audio ** 2)))
        print(f"   ёзув: {len(audio) / RATE:.1f}с, баландлик peak={peak:.3f} rms={rms:.4f}", flush=True)
        save_wav(audio, LAST_WAV)
        if peak < 0.005:
            print("Микрофондан овоз келмаяпти (сукунат). тизимда микрофон танлови ва рухсатини текширинг.", flush=True)
            return
        # Паст микрофонни кучайтирамиз (нутқ аниқлагич паст овозни сукунат деб ташлаб юборади)
        audio = audio * min(0.9 / peak, 30.0)
        t0 = time.time()
        text = transcribe(audio)
        if not text:
            print("Нутқ топилмади.", flush=True)
            return
        if CFG.get("script") == "cyrillic":
            text = to_cyrillic(text)
        text = capitalize_sentences(text)
        print(f"✔  ({time.time() - t0:.1f}с) {text}", flush=True)
        paste(text)
    except Exception as e:
        beep(220, 300)
        print(f"Хато: {e}", flush=True)
    finally:
        set_state("idle")


_held = set()          # macOS: ҳозир босилган модификаторлар (pynput)
_kb = None


def paste(text):
    # Гарячая клавиша модификаторлари қўйиб юборилишини кутамиз, акс ҳолда ctrl+alt+v бўлиб кетади
    for _ in range(100):
        busy = (any(keyboard.is_pressed(k) for k in ("ctrl", "alt", "shift", "windows")) if IS_WIN else bool(_held))
        if not busy:
            break
        time.sleep(0.02)
    try:
        old = pyperclip.paste()
    except Exception:
        old = None
    pyperclip.copy(text)
    time.sleep(0.05)
    if IS_WIN:
        keyboard.send("ctrl+v")
    else:
        mod = pk.Key.cmd if IS_MAC else pk.Key.ctrl
        with _kb.pressed(mod):
            _kb.press("v"); _kb.release("v")
    print(f"   жойлаштирилди — ойна: {active_window()}", flush=True)
    if CFG.get("press_enter"):
        time.sleep(0.1)
        if IS_WIN:
            keyboard.send("enter")
        else:
            _kb.press(pk.Key.enter); _kb.release(pk.Key.enter)
    time.sleep(0.4)
    if old is not None:
        pyperclip.copy(old)


def _pynput_hotkey(h):
    """«ctrl+shift+space» → «<ctrl>+<shift>+<space>» (pynput)."""
    nom = {"ctrl": "<ctrl>", "control": "<ctrl>", "alt": "<alt>", "option": "<alt>", "shift": "<shift>",
           "cmd": "<cmd>", "command": "<cmd>", "space": "<space>", "esc": "<esc>", "enter": "<enter>"}
    q = []
    for k in h.lower().split("+"):
        k = k.strip()
        q.append(nom.get(k, f"<{k}>" if len(k) > 1 else k))
    return "+".join(q)


def single_instance():
    """Иккинчи нусха ишга тушмасин. True — биз ягона нусхамиз."""
    if IS_WIN:
        ctypes.windll.kernel32.CreateMutexW(None, False, "OVOZ_kiritish_single_instance")
        return ctypes.windll.kernel32.GetLastError() != 183
    import fcntl
    global _lockf
    _lockf = open(os.path.join(TMP, "OVOZ_kiritish.lock"), "w")
    try:
        fcntl.flock(_lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------- ишга тушириш
def main():
    global _kb
    if not single_instance():
        print("Дастур аллақачон ишлаяпти.")
        return
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    set_state("idle")
    threading.Thread(target=load_model, daemon=True).start()
    go = lambda: threading.Thread(target=toggle, daemon=True).start()
    if IS_WIN:
        ctypes.windll.kernel32.SetConsoleTitleW("Овозли киритиш")
        keyboard.add_hotkey(HOTKEY, go, suppress=True, trigger_on_release=True)
        keyboard.on_press_key(CFG["cancel_key"], cancel)
        keyboard.wait()
        return
    # macOS: Тизим созламалари → Махфийлик → «Accessibility» ва «Input Monitoring» да VS Code'га рухсат керак
    _kb = pk.Controller()
    MODS = {pk.Key.ctrl, pk.Key.ctrl_l, pk.Key.ctrl_r, pk.Key.alt, pk.Key.alt_l, pk.Key.alt_r,
            pk.Key.shift, pk.Key.shift_l, pk.Key.shift_r, pk.Key.cmd, pk.Key.cmd_l, pk.Key.cmd_r}
    hk = pk.HotKey(pk.HotKey.parse(_pynput_hotkey(HOTKEY)), go)

    def on_press(key):
        if key in MODS:
            _held.add(key)
        if key == pk.Key.esc:
            cancel()
        hk.press(L.canonical(key))

    def on_release(key):
        _held.discard(key)
        hk.release(L.canonical(key))

    L = pk.Listener(on_press=on_press, on_release=on_release)
    L.start()
    L.join()


if __name__ == "__main__":
    main()
