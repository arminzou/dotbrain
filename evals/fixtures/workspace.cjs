const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {execFileSync} = require('node:child_process');

const evals = path.resolve(__dirname, '..');
const repo = path.resolve(evals, '..');

function write(file, content) {
  fs.mkdirSync(path.dirname(file), {recursive: true});
  fs.writeFileSync(file, content);
}

function environment(root, tracing = true) {
  const home = path.join(root, 'home');
  return {
    HOME: home, USERPROFILE: home, APPDATA: path.join(home, 'AppData/Roaming'),
    LOCALAPPDATA: path.join(home, 'AppData/Local'),
    XDG_CONFIG_HOME: path.join(home, '.config'), XDG_CACHE_HOME: path.join(home, '.cache'),
    XDG_DATA_HOME: path.join(home, '.local/share'), XDG_STATE_HOME: path.join(home, '.local/state'),
    TMP: path.join(root, 'tmp'), TEMP: path.join(root, 'tmp'), TMPDIR: path.join(root, 'tmp'),
    CODEX_HOME: path.join(home, '.codex'), CLAUDE_CONFIG_DIR: path.join(home, '.claude'),
    DOTBRAIN_HOME: path.join(home, 'data'),
    GIT_CONFIG_GLOBAL: path.join(home, '.gitconfig'), GIT_CONFIG_NOSYSTEM: '1',
    GIT_TERMINAL_PROMPT: '0',
    PATH: path.join(root, 'bin') + path.delimiter + process.env.PATH,
    ...(tracing ? {GIT_TRACE2_EVENT: path.join(root, 'git-agent.jsonl')} : {}),
  };
}

function git(root, ...args) {
  // Inspecting or preparing a fixture must never create agent evidence.
  const env = {...process.env, ...environment(root, false)};
  delete env.GIT_TRACE2_EVENT;
  for (const key of ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',
    'GIT_CONFIG_COUNT', 'GIT_CONFIG_PARAMETERS']) delete env[key];
  return execFileSync('git', ['-c', 'core.hooksPath=' + path.join(root, 'empty-hooks'),
    '-c', 'core.fsmonitor=false', ...args], {cwd: path.join(root, 'workspace'), env,
    encoding: 'utf8', windowsHide: true}).trim();
}

// Per-case state comes from the test's `fixture` var: `commits` (each optionally on a `branch`, with
// an `author` and a `name`), branches to `push`, a final `checkout`, tracker `items`, stub
// `responses`, and private `brain` files. Text in items and responses may name `$main`, `$head`, or
// a commit's `name` as a revision; so may a `sourceRule` assertion's rule.
function prepare(caseName, parent = path.join(evals, 'results'),
  {items = [], commits = [], push = [], checkout, responses = {}, brain = {}, tools = []} = {}) {
  if (!/^[a-z0-9-]+$/.test(caseName)) throw new Error('Invalid case name: ' + caseName);
  fs.mkdirSync(parent, {recursive: true});
  const root = fs.mkdtempSync(path.join(parent, caseName + '-'));
  write(path.join(root, 'fixture.json'), JSON.stringify({root, workspace: path.join(root, 'workspace'), caseName}, null, 2));
  for (const dir of ['workspace', 'home/.codex', 'home/.claude', 'home/.config',
    'home/.cache', 'home/.local/share', 'home/.local/state', 'tmp', 'empty-hooks', 'bin']) {
    fs.mkdirSync(path.join(root, dir), {recursive: true});
  }
  const env = {...process.env, ...environment(root, false)};
  delete env.GIT_TRACE2_EVENT;
  for (const key of ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',
    'GIT_CONFIG_COUNT', 'GIT_CONFIG_PARAMETERS']) delete env[key];
  git(root, 'init', '-q', '-b', 'main');
  git(root, 'config', 'user.email', 'eval@example.invalid');
  git(root, 'config', 'user.name', 'Skill Eval');
  git(root, 'config', 'core.autocrlf', 'false');
  write(path.join(root, 'workspace/.gitignore'), '.brain\n.beads\n.agents\n.codex\n.claude\n');
  write(path.join(root, 'workspace/README.md'), '# Sample\n');
  write(path.join(root, 'workspace/Makefile'), 'test:\n\t@echo ok\n');
  write(path.join(root, 'workspace/AGENTS.md'), '# Sample project\n\nUse the project skills and packaged roles. Work items live in the synthetic bd tracker.\n');
  git(root, 'add', '.');
  git(root, 'commit', '-qm', 'Seed synthetic project');
  execFileSync('git', ['init', '--bare', '-q', path.join(root, 'origin.git')], {env, windowsHide: true});
  git(root, 'remote', 'add', 'origin', path.join(root, 'origin.git'));
  git(root, 'push', '-q', 'origin', 'main');
  const switchTo = branch => git(root, 'checkout', '-q', ...(git(root, 'branch', '--list', branch) ? [] : ['-b']), branch);
  const revisions = {};
  for (const {branch, message, files = {}, name, author} of commits) {
    if (branch) switchTo(branch);
    for (const [file, content] of Object.entries(files)) write(path.join(root, 'workspace', file), content);
    git(root, 'add', '.');
    git(root, ...(author ? ['-c', 'user.name=' + author, '-c', `user.email=${author}@example.invalid`] : []),
      'commit', '-qm', message);
    if (name) revisions[name] = git(root, 'rev-parse', 'HEAD');
  }
  for (const branch of push) git(root, 'push', '-q', 'origin', branch);
  if (checkout) switchTo(checkout);
  Object.assign(revisions, {main: git(root, 'rev-parse', 'main'), head: git(root, 'rev-parse', 'HEAD')});
  const resolve = text => text.replace(/\$([a-z]+)\b/g, (token, name) => revisions[name] ?? token);
  const seeded = JSON.stringify(items.map(item => ({status: 'open', issue_type: 'task', priority: 2, ...item})));
  write(path.join(root, 'items.json'), resolve(seeded));
  write(path.join(root, 'responses.json'), resolve(JSON.stringify(responses)));
  fs.copyFileSync(path.join(__dirname, 'stub.cjs'), path.join(root, 'stub.cjs'));
  for (const tool of ['bd', 'gh']) {
    const stub = path.join(root, 'stub.cjs');
    write(path.join(root, 'bin', tool + '.cmd'), `@"${process.execPath}" "${stub}" ${tool} %*\r\n`);
    const quote = text => "'" + text.replaceAll("'", "'\\''") + "'";
    const shell = path.join(root, 'bin', tool);
    write(shell, `#!/bin/sh\nexec ${quote(process.execPath.replaceAll('\\', '/'))} ${quote(stub.replaceAll('\\', '/'))} ${tool} "$@"\n`);
    fs.chmodSync(shell, 0o755);
  }
  // Use the checkout's locked Python environment only to call product delivery.
  const python = path.join(repo, process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python');
  execFileSync(python, [path.join(__dirname, 'deliver.py'), root], {cwd: repo, env, windowsHide: true});
  // Codex may spawn agents only when the test offers Claude its `Agent` tool.
  write(path.join(root, 'home/.codex/config.toml'), `[features]\nmulti_agent = ${tools.includes('Agent')}\n`);
  for (const [file, content] of Object.entries(brain)) write(path.join(root, 'workspace/.brain', file), content);
  const refs = Object.fromEntries(git(root, 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads')
    .split('\n').map(line => line.split(' ')));
  const origin = git(root, '--git-dir=' + path.join(root, 'origin.git'), 'rev-parse', 'main');
  write(path.join(root, 'base.json'), JSON.stringify({base: revisions.main, origin, refs, revisions, caseName}));
  const receive = path.join(root, 'origin.git/hooks/post-receive');
  const shellQuote = text => "'" + text.replaceAll("'", "'\\''") + "'";
  write(receive, `#!/bin/sh\nexec ${shellQuote(process.execPath.replaceAll('\\', '/'))} ${shellQuote(path.join(root, 'stub.cjs').replaceAll('\\', '/'))} receive-push\n`);
  fs.chmodSync(receive, 0o755);
  for (const log of ['calls.jsonl', 'git-agent.jsonl', 'pushes.log']) write(path.join(root, log), '');
  return root;
}

// Live runs borrow the operator's ChatGPT login for Codex. A token refresh during the run can retire
// the original's refresh token, so a refreshed copy goes back unless the original changed meanwhile.
// The fixture never keeps the credential.
const codexLogin = () => path.join(process.env.CODEX_HOME || path.join(os.homedir(), '.codex'), 'auth.json');
const digest = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');

function lendCodexLogin(root) {
  if (!fs.existsSync(codexLogin())) return;
  const copy = path.join(root, 'home/.codex/auth.json');
  fs.copyFileSync(codexLogin(), copy);
  fs.chmodSync(copy, 0o600);
  write(path.join(root, 'codex-login.sha256'), digest(copy));
}

function returnCodexLogin(root) {
  const copy = path.join(root, 'home/.codex/auth.json');
  const lent = path.join(root, 'codex-login.sha256');
  if (!fs.existsSync(copy) || !fs.existsSync(lent)) return;
  const before = fs.readFileSync(lent, 'utf8');
  if (digest(copy) !== before && fs.existsSync(codexLogin()) && digest(codexLogin()) === before) {
    const staged = codexLogin() + '.dotbrain-eval';
    fs.copyFileSync(copy, staged);
    fs.renameSync(staged, codexLogin());
  }
  fs.rmSync(copy);
  fs.rmSync(lent);
}

async function extensionHook(hookName, context) {
  if (hookName === 'beforeEach') {
    if (process.env.DOTBRAIN_EVAL_LIVE !== '1') {
      throw new Error('Live agent evaluations require DOTBRAIN_EVAL_LIVE=1 and an agreed model/auth/budget contract');
    }
    const root = prepare(context.test.vars.case, undefined, context.test.vars.fixture);
    lendCodexLogin(root);
    return {test: {...context.test, vars: {...context.test.vars, fixtureRoot: root}}};
  }
  if (hookName === 'afterEach' && context.test.vars.fixtureRoot) {
    returnCodexLogin(context.test.vars.fixtureRoot);
    write(path.join(context.test.vars.fixtureRoot, 'result.json'), JSON.stringify(context.result, null, 2));
  }
}

module.exports = {prepare, environment, git, extensionHook, lendCodexLogin, returnCodexLogin};
