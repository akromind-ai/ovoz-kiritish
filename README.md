# «Ovozli kiritish» — ўзбекча овозли киритиш

Ўзбекча гапирасиз — матн курсор турган жойга ёзилади (VS Code, Claude чати, Telegram, Word…).
Интернетсиз ва бепул: ўзбекча ўқитилган Whisper модели компютернинг ўзида ишлайди.
Windows ва macOS (Apple Silicon ва Intel), VS Code кенгайтмаси орқали бошқарилади.

| | |
|---|---|
| Жорий версия | **0.3.4** (2026-11-12) — Windows + macOS (Apple Silicon ва Intel), мустақил кенгайтма, ўзи ўрнатилади |
| Тайёр пакет | `02_tayyor_paketlar/ovoz-kiritish-0.3.4.vsix` |
| Клавиша | Windows — **Ctrl+Alt+Space**, Mac — **Control+Shift+Space**; Esc — бекор қилиш |
| Модел | `AlexAnoshka/fast-whisper-uz-rubaistt-v2-medium-ct2` (Apache-2.0), WER 9,9 % жонли нутқ |
| Лицензия | MIT (кенгайтма коди) |
| Marketplace | ҳали чиқарилмаган — қуйида «Нашр қилиш» |

## Папка тузилиши
| Папка | Нима |
|---|---|
| `01_kengaytma/` | **Асосий манба** — шу ерда ривожлантирилади. VS Code кенгайтмаси (`extension.js`, `package.json`) ва ичидаги Python дастури (`python/`) |
| `02_tayyor_paketlar/` | Йиғилган `.vsix` (ўрнатишга тайёр) ва Windows учун ZIP-ўрнатгич; `eski/` — олдинги версиялар |
| `03_shaxsiy_v0.1/` | Биринчи шахсий версия (фақат Windows, дастур алоҳида папкада). Таққослаш учун, ўзгартирилмайди |
| `04_hujjatlar/` | Қўлланмалар, ривожлантириш режаси |
| `05_mac_ornatgich/` | Эски, алоҳида Mac ўрнатгичи (0.3.1 дан бошлаб керак эмас — кенгайтманинг ўзи ўрнатади) |

## Қандай ишлайди
```
VS Code кенгайтмаси (extension.js)
  ├─ биринчи ишга тушиш → «Ўрнатиш» → python/ornatish.cmd (Windows) | python/ornatish.sh (Mac)
  │     → <globalStorage>/.venv, кутубхоналар, модел (~3 ГБ, бир марта)
  ├─ ёқиш → <globalStorage>/.venv/python  python/OVOZ_kiritish.py   (OVOZ_DATA = globalStorage)
  └─ ҳолатни %TEMP%/OVOZ_state.txt ва OVOZ_kiritish.pid дан ўқийди (тугма, пастки панел)

OVOZ_kiritish.py
  клавиша (Windows: keyboard, Mac: pynput) → микрофон (sounddevice, 16 кГц)
  → faster-whisper (GPU/CUDA, бўлмаса CPU int8; VAD ёқиқ) → лотин → кирилл (to_cyrillic)
  → буфер + Ctrl+V / ⌘V → курсорга
```
Фойдаланувчи маълумоти (`OVOZ_config.json`, `OVOZ_log.txt`) — VS Code `globalStorage` папкасида; кенгайтма янгиланганда йўқолмайди.

## Ўрнатиш (фойдаланувчи учун)
1. Python: Windows — 3.11+ (python.org, «Add to PATH»), Mac — 3.10–3.13, тавсия 3.12 (python.org/downloads/macos; Python бўлмаса ўзи 3.12 ни ўрнатади).
2. VS Code → Extensions → «…» → **Install from VSIX** → `02_tayyor_paketlar/ovoz-kiritish-0.3.4.vsix`.
3. «Ўрнатиш» таклифига рози бўлинг, терминал тугашини кутинг.
4. Mac: Тизим созламалари → Махфийлик ва хавфсизлик → **Accessibility** ва **Input Monitoring** да VS Code'ни ёқинг, микрофонга рухсат беринг.

**MacBook:** битта `.vsix` файли етарли. Кенгайтма биринчи очилганда терминалда ўзи ўрнатилади. Python бўлмаса, уни python.org'дан ўзи ўрнатади (Mac пароли сўралади), охирида рухсатлар ойнасини очади.

**Масофадан ишлаш (Mac → Windows сервер, Remote-SSH / Tunnel):** кенгайтма `extensionKind: ui` — у сервер (Windows) да эмас, қаршингиздаги компютер (Mac) да ишлайди. Микрофон, клавиша ва модел Mac'да ишлайди, матн эса ⌘V билан масофавий ойнага (таҳрирловчи, Claude чати) тушади. Кенгайтмани Mac'га ўрнатинг; серверга ҳеч нарса керак эмас. Ўрнатиш Mac'нинг ўз Terminal ойнасида очилади.

## Ривожлантириш
```bash
cd 01_kengaytma
node --check extension.js                     # JS синтаксиси
python -m py_compile python/OVOZ_kiritish.py  # Python синтаксиси
npx --yes @vscode/vsce@3 package --allow-missing-repository   # → ovoz-kiritish-<версия>.vsix
code --install-extension ovoz-kiritish-<версия>.vsix --force  # ўз компютерингизда синаш
```
Версияни `package.json` да оширинг, `CHANGELOG.md` га ёзинг, тайёр `.vsix` ни `02_tayyor_paketlar/` га, эскисини `eski/` га олинг.
Дастурни VS Code'сиз синаш: `OVOZ_DATA=<папка> <venv>/python python/OVOZ_kiritish.py` (битта нусха ҳимояси бор — ишлаб турган нусхани аввал ўчиринг).

## Нашр қилиш (VS Code Marketplace)
1. https://marketplace.visualstudio.com/manage — Microsoft ҳисоби билан кириш.
2. **Create publisher** — ID `akromind` (бошқа бўлса — `package.json` даги `publisher` ни ўзгартириб, қайта йиғинг).
3. **New extension → Visual Studio Code** → `.vsix` ни юклаш. Кейинги версиялар: шу саҳифада **Update**.
Токен билан: `01_kengaytma/CHIQARISH.bat` (Azure DevOps PAT, «Marketplace: Manage»). Шахсий Microsoft ҳисобида терминалдан Entra ID билан кириш ишламайди (синалган, 2026-11-10).

## Тарих
- **0.1.0** (2026-09-11) — шахсий: Windows, дастур `D:\akromind\VS_code_Global` да, кенгайтма фақат тугма. Ҳозир ҳам шу компютерда ишлайди.
- **0.2.0** (2026-11-10) — мустақил кенгайтма: Python дастури ичида, Python муҳити ва модел ўзи ўрнатилади; MIT, иконка, README.
- **0.3.0** (2026-11-10) — macOS қўшилди (pynput, ⌘V, тизим товушлари, `ornatish.sh`, `hotkey_mac`).
- **0.3.4** (2026-11-12) — Mac: ўрнатиш фақат Python 3.10–3.13 ни олади (3.14 да Intel ва macOS ≤13 учун onnxruntime йўқ); Intel Mac текширилди (ғилдираклар бор).
- **0.3.3** (2026-11-11) — «гапириш» → «гAPIриш» хатоси тузатилди (keep_latin фақат бутун сўз); Windows сигнали тузатилди.
- **0.3.2** (2026-11-10) — масофавий ойна: ўрнатиш Mac'нинг ўз Terminal'ида; дастур Mac'да ишлайди.
- **0.3.1** (2026-11-10) — ўрнатиш биринчи очилганда сўрамасдан бошланади; Mac'да Python ўзи ўрнатилади, рухсатлар ойнаси ўзи очилади.
