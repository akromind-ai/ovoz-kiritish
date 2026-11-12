// Ўзбекча овозли киритиш — VS Code кенгайтмаси (Marketplace нусхаси, мустақил; Windows ва macOS).
// Python дастури кенгайтма ичида (python/). Биринчи ишга тушганда Python муҳити, кутубхоналар ва модел
// фойдаланувчининг ўз папкасига (globalStorage) ўрнатилади; созлама ва лог ҳам ўша ерда.
const vscode = require('vscode');
const fs = require('fs');
const os = require('os');
const path = require('path');
const cp = require('child_process');

const PID_FILE = path.join(os.tmpdir(), 'OVOZ_kiritish.pid');
const STATE_FILE = path.join(os.tmpdir(), 'OVOZ_state.txt');

const LOOK = {
  off:       { text: '$(mic) Овоз ўчиқ', tip: 'Овозли киритиш ўчиқ — ёқиш учун босинг' },
  loading:   { text: '$(sync~spin) Овоз юкланмоқда', tip: 'Модель юкланмоқда' },
  ready:     { text: '$(mic-filled) Овоз', tip: (process.platform === 'darwin' ? 'Тайёр: Control+Shift+Space' : 'Тайёр: Ctrl+Alt+Space') + ' — гапириш. Ўчириш учун босинг' },
  recording: { text: '$(record) Ёзилмоқда', tip: 'Гапиринг, тугатиш учун ' + (process.platform === 'darwin' ? 'Control+Shift+Space' : 'Ctrl+Alt+Space'), warn: true },
  busy:      { text: '$(sync~spin) Танилмоқда', tip: 'Нутқ матнга айлантирилмоқда' },
  setup:     { text: '$(cloud-download) Овоз ўрнатилмоқда', tip: 'Python муҳити ва модел ўрнатилмоқда (терминалга қаранг)' },
};

let ctx, dataDir, srcDir, setupTerminal = null;

const IS_WIN = process.platform === 'win32';
const venvPy = () => IS_WIN ? path.join(dataDir, '.venv', 'Scripts', 'python.exe') : path.join(dataDir, '.venv', 'bin', 'python');
const installed = () => fs.existsSync(venvPy()) && fs.existsSync(path.join(dataDir, 'ornatildi.txt'));

function runningPid() {
  let pid;
  try { pid = parseInt(fs.readFileSync(PID_FILE, 'utf8'), 10); } catch { return null; }
  if (!pid) return null;
  try { process.kill(pid, 0); return pid; } catch (e) { return e.code === 'EPERM' ? pid : null; }
}

function readState() {
  if (setupTerminal) return 'setup';
  if (!runningPid()) return 'off';
  try { return fs.readFileSync(STATE_FILE, 'utf8').trim() || 'loading'; } catch { return 'loading'; }
}

// Ўрнатиш ойнаси шу компютерда очилади. Масофавий ойнада (Remote-SSH, Tunnel) VS Code терминали
// серверда очилади — шунинг учун Mac'да ва масофавий ойнада тизимнинг ўз терминали ишлатилади.
function setup() {
  if (setupTerminal) { if (setupTerminal.show) setupTerminal.show(); return; }
  fs.mkdirSync(dataDir, { recursive: true });
  if (IS_WIN && !vscode.env.remoteName) {
    setupTerminal = vscode.window.createTerminal({
      name: 'Овозли киритиш — ўрнатиш',
      shellPath: 'cmd.exe',
      shellArgs: ['/d', '/k', `"${path.join(srcDir, 'ornatish.cmd')}" "${dataDir}"`],
    });
    setupTerminal.show();
    ctx.subscriptions.push(vscode.window.onDidCloseTerminal(t => {
      if (t === setupTerminal) setupTerminal = null;
    }));
  } else if (IS_WIN) {
    cp.spawn(`start "Ovoz" cmd /d /k ""${path.join(srcDir, 'ornatish.cmd')}" "${dataDir}""`,
      { shell: true, detached: true, stdio: 'ignore' }).unref();
    setupTerminal = { local: true };
  } else {
    const q = s => "'" + s.split("'").join("'\\''") + "'";
    const aq = s => s.split('\\').join('\\\\').split('"').join('\\"');   // AppleScript сатри
    const cmd = `bash ${q(path.join(srcDir, 'ornatish.sh'))} ${q(dataDir)}`;
    cp.execFile('osascript', ['-e', 'tell application "Terminal"', '-e', 'activate',
      '-e', `do script "${aq(cmd)}"`, '-e', 'end tell']);
    setupTerminal = { local: true };
    vscode.window.showInformationMessage('Овозли киритиш ўрнатилмоқда — Terminal ойнасига қаранг (Python йўқ бўлса Mac пароли сўралади).');
  }
  const t0 = Date.now();
  const timer = setInterval(() => {
    if (installed()) {
      clearInterval(timer);
      setupTerminal = null;
      vscode.window.showInformationMessage(IS_WIN ? 'Овозли киритиш тайёр: Ctrl+Alt+Space — гапиринг.'
        : "Овозли киритиш тайёр: Control+Shift+Space — гапиринг. Тизим созламаларида VS Code'га Accessibility ва Input Monitoring рухсатини беринг.");
      start();
    } else if (!setupTerminal || Date.now() - t0 > 60 * 60 * 1000) {
      clearInterval(timer);
      setupTerminal = null;
    }
  }, 2000);
  ctx.subscriptions.push({ dispose: () => clearInterval(timer) });
}

async function start() {
  if (runningPid() || setupTerminal) return;
  if (!installed()) {
    const ha = 'Ўрнатиш';
    const j = await vscode.window.showInformationMessage(
      'Овозли киритиш биринчи марта ўрнатилади: Python муҳити ва ўзбекча модел (≈ 3 ГБ, интернет керак).', ha, 'Кейинроқ');
    if (j === ha) setup();
    return;
  }
  try { fs.writeFileSync(STATE_FILE, 'loading'); } catch {}
  const child = cp.spawn(venvPy(), [path.join(srcDir, 'OVOZ_kiritish.py')], {
    cwd: srcDir, detached: true, stdio: 'ignore', windowsHide: true,
    env: Object.assign({}, process.env, { OVOZ_DATA: dataDir }),
  });
  child.unref();
}

function stop() {
  const pid = runningPid();
  if (!pid) return;
  if (IS_WIN) {
    cp.execFile('taskkill', ['/PID', String(pid), '/T', '/F'], () => {
      try { fs.unlinkSync(PID_FILE); } catch {}
    });
  } else {
    try { process.kill(pid, 'SIGTERM'); } catch {}
    try { fs.unlinkSync(PID_FILE); } catch {}
  }
}

function openData(name) {
  const f = path.join(dataDir, name);
  if (!fs.existsSync(f)) {
    if (name === 'OVOZ_config.json') fs.copyFileSync(path.join(srcDir, 'OVOZ_config.default.json'), f);
    else { vscode.window.showInformationMessage('Лог ҳали йўқ.'); return; }
  }
  vscode.window.showTextDocument(vscode.Uri.file(f));
}

function activate(context) {
  ctx = context;
  srcDir = path.join(context.extensionPath, 'python');
  dataDir = context.globalStorageUri.fsPath;

  if (!IS_WIN && process.platform !== 'darwin') {
    vscode.window.showWarningMessage("Овозли киритиш Windows ва macOS'да ишлайди.");
    return;
  }

  const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 1000);
  item.command = 'ovoz.toggle';
  item.show();
  let last = null;

  const refresh = () => {
    const s = readState();
    if (s === last) return;
    last = s;
    const look = LOOK[s] || LOOK.loading;
    item.text = look.text;
    item.tooltip = look.tip;
    item.backgroundColor = look.warn ? new vscode.ThemeColor('statusBarItem.errorBackground') : undefined;
    vscode.commands.executeCommand('setContext', 'ovoz.running', s !== 'off');
  };

  context.subscriptions.push(
    item,
    vscode.commands.registerCommand('ovoz.start', () => { start(); setTimeout(refresh, 300); }),
    vscode.commands.registerCommand('ovoz.stop', () => { stop(); setTimeout(refresh, 500); }),
    vscode.commands.registerCommand('ovoz.toggle', () => { runningPid() ? stop() : start(); setTimeout(refresh, 500); }),
    vscode.commands.registerCommand('ovoz.setup', () => {
      try { fs.unlinkSync(path.join(dataDir, 'ornatildi.txt')); } catch {}
      setup();
    }),
    vscode.commands.registerCommand('ovoz.openConfig', () => openData('OVOZ_config.json')),
    vscode.commands.registerCommand('ovoz.showLog', () => openData('OVOZ_log.txt')),
  );

  const timer = setInterval(refresh, 500);
  context.subscriptions.push({ dispose: () => clearInterval(timer) });
  refresh();

  if (installed()) {
    if (vscode.workspace.getConfiguration('ovoz').get('autoStart')) start();
  } else if (!context.globalState.get('ovoz.taklifQilindi')) {
    context.globalState.update('ovoz.taklifQilindi', true);
    setup();   // биринчи марта — ўрнатиш саволсиз, ўзи бошланади
  }
}

// VS Code ёпилганда дастур ўчирилмайди: бошқа ойналар ҳам ундан фойдаланади.
function deactivate() {}

module.exports = { activate, deactivate };
