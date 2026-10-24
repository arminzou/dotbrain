const {test, after} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {execFileSync, execFile} = require('node:child_process');
const {prepare, environment, git, extensionHook} = require('./workspace.cjs');
const request = require('./request.cjs');

const parent = fs.mkdtempSync(path.join(os.tmpdir(), 'skill-eval-check-'));
after(() => {
  assert.ok(fs.realpathSync(parent).startsWith(fs.realpathSync(os.tmpdir()) + path.sep));
  fs.rmSync(parent, {recursive: true, force: true});
});

test('fresh final workspaces isolate homes, origins, real delivery and stub calls', () => {
  const roots = [prepare('worker-never-pushes', parent), prepare('worker-never-pushes', parent)];
  assert.notEqual(roots[0], roots[1]);
  for (const root of roots) {
    assert.equal(git(root, 'remote', 'get-url', 'origin'), path.join(root, 'origin.git'));
    assert.equal(fs.readFileSync(path.join(root, 'calls.jsonl'), 'utf8'), '');
    assert.equal(fs.readFileSync(path.join(root, 'git-agent.jsonl'), 'utf8'), '');
    for (const key of ['HOME', 'CODEX_HOME', 'CLAUDE_CONFIG_DIR', 'DOTBRAIN_HOME',
      'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'TMP', 'TEMP', 'TMPDIR']) {
      assert.ok(environment(root)[key].startsWith(root + path.sep), key);
      assert.ok(fs.statSync(environment(root)[key]).isDirectory(), key);
    }
    assert.ok(fs.realpathSync(path.join(root, 'workspace/.agents/skills/run-execution')).startsWith(root));
    assert.ok(fs.readFileSync(path.join(root, 'workspace/.codex/agents/dotbrain-worker.toml'), 'utf8').includes('# dotbrain-managed-agent: v1'));
    assert.ok(fs.existsSync(path.join(root, 'plugin/.claude-plugin/plugin.json')));
    const env = {...process.env, ...environment(root)};
    if (process.platform === 'win32') {
      const located = execFileSync('pwsh', ['-NoProfile', '-Command', '(Get-Command bd).Source; bd --actor worker-a where; gh pr merge 1; exit 0'], {env, encoding: 'utf8', windowsHide: true});
      assert.ok(located.includes(path.join(root, 'bin/bd.cmd')));
    } else {
      const located = execFileSync('sh', ['-c', 'command -v bd; bd --actor worker-a where; gh pr merge 1 || true'], {env, encoding: 'utf8'});
      assert.ok(located.includes(path.join(root, 'bin/bd')));
    }
    const calls = fs.readFileSync(path.join(root, 'calls.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
    assert.deepEqual(calls.map(call => call.tool), ['bd', 'gh']);
    assert.deepEqual(calls[0].args, ['--actor', 'worker-a', 'where']);
    execFileSync('git', ['status', '--porcelain'], {cwd: path.join(root, 'workspace'), env, windowsHide: true});
    const before = fs.readFileSync(path.join(root, 'git-agent.jsonl'), 'utf8');
    assert.ok(before.includes('"event":"start"'));
    git(root, 'status', '--porcelain');
    assert.equal(fs.readFileSync(path.join(root, 'git-agent.jsonl'), 'utf8'), before);
  }
  assert.notEqual(environment(roots[0]).CODEX_HOME, environment(roots[1]).CODEX_HOME);
});

test('standard hook refuses accidental live evaluations without authorization', async () => {
  const previous = process.env.DOTBRAIN_EVAL_LIVE;
  delete process.env.DOTBRAIN_EVAL_LIVE;
  try { await assert.rejects(extensionHook('beforeEach', {test: {vars: {case: 'worker-never-pushes'}}}), /Live agent/); }
  finally { if (previous !== undefined) process.env.DOTBRAIN_EVAL_LIVE = previous; }
});

test('failed delivery retains its allocated fixture and local pushes leave receipts', () => {
  const failureParent = path.join(parent, 'failed-setup');
  const source = `const cp=require('node:child_process'); const run=cp.execFileSync;
    cp.execFileSync=(file,args,options)=>{if(args?.[0]?.endsWith('deliver.py')) throw new Error('seeded delivery failure'); return run(file,args,options);};
    require(${JSON.stringify(path.join(__dirname, 'workspace.cjs'))}).prepare('worker-never-pushes',process.argv[1]);`;
  assert.throws(() => execFileSync(process.execPath, ['-e', source, failureParent],
    {windowsHide: true, stdio: 'pipe'}), /seeded delivery failure/);
  const failedRoot = path.join(failureParent, fs.readdirSync(failureParent)[0]);
  assert.equal(JSON.parse(fs.readFileSync(path.join(failedRoot, 'fixture.json'), 'utf8')).root, failedRoot);

  const root = prepare('worker-never-pushes', parent);
  git(root, 'checkout', '-qb', 'receipt-check');
  execFileSync('git', ['push', '-q', 'origin', 'receipt-check'], {
    cwd: path.join(root, 'workspace'), env: {...process.env, ...environment(root)}, windowsHide: true});
  assert.match(fs.readFileSync(path.join(root, 'pushes.log'), 'utf8'), /refs\/heads\/receipt-check/);
  assert.match(fs.readFileSync(path.join(root, 'git-agent.jsonl'), 'utf8'), /"name":"push"/);
});

test('two concurrent fixture allocations do not share bindings or mutable logs', async () => {
  const source = `const {prepare}=require(${JSON.stringify(path.join(__dirname, 'workspace.cjs'))}); process.stdout.write(prepare('worker-never-pushes', process.argv[1]));`;
  const allocate = () => new Promise((resolve, reject) => {
    execFile(process.execPath, ['-e', source, parent], {windowsHide: true}, (error, stdout) => error ? reject(error) : resolve(stdout));
  });
  const roots = await Promise.all([allocate(), allocate()]);
  assert.notEqual(roots[0], roots[1]);
  for (const root of roots) {
    assert.ok(root.startsWith(parent + path.sep));
    assert.equal(git(root, 'remote', 'get-url', 'origin'), path.join(root, 'origin.git'));
    assert.equal(fs.readFileSync(path.join(root, 'calls.jsonl'), 'utf8'), '');
    assert.equal(fs.readFileSync(path.join(root, 'git-agent.jsonl'), 'utf8'), '');
  }
});

test('provider configuration binds the same scenario to separate fixture resources', () => {
  const root = prepare('activation-review-gate', parent);
  const previous = {claude: process.env.EVAL_CLAUDE_MODEL, codex: process.env.EVAL_CODEX_MODEL};
  process.env.EVAL_CLAUDE_MODEL = 'fixture-model';
  process.env.EVAL_CODEX_MODEL = 'fixture-model';
  try {
    const vars = {fixtureRoot: root, case: 'activation-review-gate', request: 'Dispatch {{worker_role}}.'};
    const claude = request({vars, provider: {id: 'anthropic:claude-agent-sdk'}});
    const codex = request({vars, provider: {id: 'openai:codex-app-server'}});
    assert.equal(claude.prompt, 'Dispatch dotbrain:worker.');
    assert.equal(codex.prompt, 'Dispatch dotbrain-worker.');
    assert.equal(claude.config.env.DOTBRAIN_HOME, codex.config.cli_env.DOTBRAIN_HOME);
    assert.equal(codex.config.working_dir, path.join(root, 'workspace'));
    assert.equal(codex.config.sandbox_mode, 'read-only');
    assert.ok(!claude.config.tools.includes('Bash'));
    assert.deepEqual(claude.config.custom_allowed_tools, claude.config.tools);
    assert.equal(claude.config.allowed_tools, undefined);
    const writingVars = {...vars, fixture: {tools: ['Read', 'Agent', 'Bash'], maxTurns: 40}};
    const writing = request({vars: writingVars, provider: {id: 'anthropic:claude-agent-sdk'}});
    assert.deepEqual(writing.config.custom_allowed_tools, writingVars.fixture.tools);
    assert.equal(writing.config.max_turns, 40);
    assert.equal(request({vars: writingVars, provider: {id: 'openai:codex-app-server'}}).config.sandbox_mode, undefined);
  } finally {
    for (const [name, value] of [['EVAL_CLAUDE_MODEL', previous.claude], ['EVAL_CODEX_MODEL', previous.codex]]) {
      if (value === undefined) delete process.env[name]; else process.env[name] = value;
    }
  }
});

test('per-test tracker items reach the bd stub, comments included', () => {
  const comments = [{author: 'lead', text: 'Approved at abc123'}];
  const root = prepare('data-driven-items', parent, [{id: 'demo-9', title: 'Seeded', comments}]);
  const bd = args => JSON.parse(execFileSync(process.execPath, [path.join(root, 'stub.cjs'), 'bd', ...args], {encoding: 'utf8'}));
  assert.deepEqual(bd(['show', 'demo-9'])[0].comments, comments);
  assert.deepEqual(bd(['comments', 'demo-9']), comments);
  assert.deepEqual(bd(['comments', 'missing']), []);
  assert.throws(() => prepare('../escape', parent), /Invalid case name/);
});
