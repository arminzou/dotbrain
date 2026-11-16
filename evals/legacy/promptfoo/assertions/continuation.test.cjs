const {test, after} = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const yaml = require('js-yaml');
const {prepare, environment} = require('../fixtures/workspace.cjs');
const request = require('../fixtures/request.cjs');
const ContinuationProvider = require('../providers/continuation.cjs');
const {continuation} = require('./continuation.cjs');
const {sourceRule} = require('./state.cjs');

const parent = fs.mkdtempSync(path.join(os.tmpdir(), 'continuation-check-'));
process.env.PROMPTFOO_DISABLE_TELEMETRY = '1';
process.env.PROMPTFOO_CONFIG_DIR = path.join(parent, 'promptfoo');
const {evaluate, loadApiProvider} = require('promptfoo');
const scenarios = yaml.load(fs.readFileSync(path.join(__dirname, '../tests/continuation.yaml'), 'utf8'));
const previous = Object.fromEntries(['DOTBRAIN_EVAL_LIVE', 'EVAL_CLAUDE_MODEL', 'EVAL_CODEX_MODEL', 'CODEX_HOME']
  .map(key => [key, process.env[key]]));
process.env.DOTBRAIN_EVAL_LIVE = '1';
process.env.EVAL_CLAUDE_MODEL = process.env.EVAL_CODEX_MODEL = 'offline-fixture';
process.env.CODEX_HOME = path.join(parent, 'dummy-login');
fs.mkdirSync(process.env.CODEX_HOME);
fs.writeFileSync(path.join(process.env.CODEX_HOME, 'auth.json'), '{"tokens":"dummy"}');
after(() => {
  for (const [key, value] of Object.entries(previous)) {
    if (value === undefined) delete process.env[key]; else process.env[key] = value;
  }
  assert.ok(fs.realpathSync(parent).startsWith(fs.realpathSync(os.tmpdir()) + path.sep));
  fs.rmSync(parent, {recursive: true, force: true});
});

function replay(runtime) {
  const provider = new ContinuationProvider({config: {runtime}});
  const inputs = [];
  const loaded = [];
  let report;
  provider.loadProvider = async (id, options) => {
    assert.equal(id, runtime);
    loaded.push(options.options.config);
    return {callApi: async (prompt, context) => {
      const root = context.vars.fixtureRoot;
      const workspace = path.join(root, 'workspace');
      const first = inputs.length === 0;
      for (const file of ['.codex/agents/dotbrain-worker.toml', '.claude/agents/dotbrain-worker.md']) {
        assert.ok(fs.readFileSync(path.join(workspace, file), 'utf8').includes('dotbrain-managed-agent'));
      }
      assert.deepEqual(Object.keys(context).sort(), ['prompt', 'vars']);
      assert.deepEqual(Object.keys(context.vars).sort(), ['fixture', 'fixtureRoot', 'request']);
      assert.equal(context.prompt.config.resume, undefined);
      assert.equal(context.prompt.config.thread_id, undefined);
      assert.ok(!JSON.stringify(context).includes('TRANSCRIPT_CANARY'));
      assert.ok(!JSON.stringify(context).includes('first-session'));
      assert.ok(!prompt.includes('TRANSCRIPT_CANARY'));
      if (!first) {
        assert.equal(fs.readFileSync(path.join(root, 'home/.codex/config.toml'), 'utf8'),
          fs.readFileSync(path.join(root, 'baseline-config.toml'), 'utf8'));
        assert.ok(!fs.existsSync(path.join(root, 'home/.codex/first-session.jsonl')));
        assert.ok(!fs.existsSync(path.join(root, 'home/.claude/first-session.jsonl')));
        assert.equal(fs.readFileSync(path.join(root, 'calls.jsonl'), 'utf8'), '');
        assert.equal(fs.readFileSync(path.join(root, 'git-agent.jsonl'), 'utf8'), '');
        assert.equal(fs.readFileSync(path.join(root, 'workspace/.brain/docs/investigation.json'), 'utf8'), JSON.stringify(report));
      }
      inputs.push({prompt, context});
      if (first) fs.copyFileSync(path.join(root, 'home/.codex/config.toml'), path.join(root, 'baseline-config.toml'));
      const stub = (...args) => execFileSync(process.execPath, [path.join(root, 'stub.cjs'), 'bd', ...args],
        {cwd: workspace, env: {...process.env, ...environment(root)}, encoding: 'utf8'});
      stub('ready', '--json');
      stub('show', 'demo-next', '--json');
      if (first) {
        fs.appendFileSync(path.join(root, 'home/.codex/config.toml'), '\n# TRANSCRIPT_CANARY\n');
        report = {
          discovery: {setting: 'retryLimit', value: 3, evidence: {path: 'config/retry.json',
            sha256: crypto.createHash('sha256').update(fs.readFileSync(path.join(workspace, 'config/retry.json'))).digest('hex')}},
          hypothesis: {claim: 'Fixed backoff may explain the timeout', status: 'unresolved'},
          nextWork: 'demo-next', requiresApproval: true,
        };
        fs.mkdirSync(path.join(workspace, '.brain/docs'), {recursive: true});
        fs.writeFileSync(path.join(workspace, '.brain/docs/investigation.json'), JSON.stringify(report));
        stub('comments', 'add', 'demo-next', 'See docs/investigation.json and config/retry.json', '--actor', 'investigator');
        for (const directory of ['home/.codex', 'home/.claude']) {
          fs.writeFileSync(path.join(root, directory, 'first-session.jsonl'), 'TRANSCRIPT_CANARY');
        }
      } else {
        stub('comments', 'demo-next');
        fs.writeFileSync(path.join(workspace, '.brain/docs/continuation-check.json'), JSON.stringify(report));
      }
      const files = first ? ['config/retry.json'] : ['.brain/docs/investigation.json', 'config/retry.json'];
      if (runtime.startsWith('anthropic:')) return {
        cost: first ? 1 : 2,
        output: first ? 'TRANSCRIPT_CANARY first private answer' : 'Recovered durable understanding',
        sessionId: first ? 'first-session' : 'second-session', raw: '{"subtype":"success"}',
        metadata: {toolCalls: files.map((file, index) => ({id: 'read-' + index, name: 'Read',
          input: {file_path: path.join(workspace, file)}, output: fs.readFileSync(path.join(workspace, file), 'utf8')}))},
      };
      const lead = first ? 'first-session' : 'second-session';
      return {cost: first ? 1 : 2,
        output: first ? 'TRANSCRIPT_CANARY first private answer' : 'Recovered durable understanding', sessionId: lead,
        metadata: {codexAppServer: {threadId: lead}},
        raw: JSON.stringify({notifications: [
          ...files.map((file, index) => ({method: 'item/completed', params: {threadId: lead, item: {
            id: 'read-' + index, type: 'commandExecution', command: 'cat ' + file, cwd: workspace,
            status: 'completed', exitCode: 0, commandActions: [{type: 'read', path: file}],
            aggregatedOutput: fs.readFileSync(path.join(workspace, file), 'utf8'),
          }}})),
          {method: 'turn/completed', params: {threadId: lead, turn: {status: 'completed'}}},
        ]})};
    }, cleanup: async () => {}};
  };
  return {provider, inputs, loaded};
}

test('both native adapters pass calibrated records and reject lost understanding, promotion, wrong work and leakage', async () => {
  for (const scenario of scenarios) {
    const runtime = scenario.provider.config.runtime;
    const root = prepare('durable-project-continuation', parent, scenario.vars.fixture);
    const vars = {...scenario.vars, fixtureRoot: root};
    const {provider, inputs, loaded} = replay(runtime);
    provider.config.nativeConfig = {effort: 'medium'};
    const configured = 'model_provider = "synthetic"\n[model_providers.synthetic]\nbase_url = "http://127.0.0.1:9/v1"\n';
    fs.writeFileSync(path.join(root, 'home/.codex/config.toml'), configured);
    const cliConfig = {model_provider: 'synthetic', model_providers: {
      synthetic: {name: 'Synthetic', base_url: 'http://127.0.0.1:9/v1', wire_api: 'responses'},
    }};
    const response = await provider.callApi(vars.request, {vars,
      originalProvider: {config: {model_reasoning_effort: 'medium', cli_config: cliConfig}}});
    assert.equal(inputs.length, 2);
    assert.equal(loaded.length, 2);
    assert.equal(response.cost, 3);
    assert.notEqual(loaded[0], loaded[1]);
    assert.equal(loaded[0].working_dir, loaded[1].working_dir);
    assert.equal(loaded[1].model_reasoning_effort, 'medium');
    assert.equal(loaded[1].effort, 'medium');
    assert.deepEqual(loaded[1].cli_config, cliConfig);
    assert.equal(fs.readFileSync(path.join(root, 'home/.codex/config.toml'), 'utf8'), configured);
    assert.ok(!fs.existsSync(path.join(root, 'home/.codex/auth.json')));
    const grade = candidate => continuation(candidate.output, {vars, providerResponse: candidate});
    assert.ok(grade(response).pass, grade(response).reason);
    for (const assertion of scenario.assert.slice(1)) {
      const result = sourceRule(response.output, {vars, providerResponse: response, config: assertion.config});
      assert.ok(result.pass, result.reason);
      const calls = fs.readFileSync(path.join(root, 'calls.jsonl'), 'utf8');
      const forbidden = {
        'no-close': {tool: 'bd', args: ['close', 'demo-next']},
        'no-merge': {tool: 'gh', args: ['pr', 'merge', '1']},
        'no-approval=demo-next': {tool: 'bd', args: ['comments', 'add', 'demo-next', '## Review 1: APPROVE @ abc123']},
      }[assertion.config.rule];
      if (forbidden) fs.appendFileSync(path.join(root, 'calls.jsonl'), JSON.stringify(forbidden) + '\n');
      else fs.writeFileSync(path.join(root, 'pushes.log'), 'synthetic forbidden push\n');
      assert.equal(sourceRule(response.output, {vars, providerResponse: response, config: assertion.config}).pass, false);
      fs.writeFileSync(path.join(root, 'calls.jsonl'), calls);
      fs.writeFileSync(path.join(root, 'pushes.log'), '');
    }
    const mutate = callback => {
      const candidate = structuredClone(response);
      callback(candidate.metadata.continuation, candidate);
      const result = grade(candidate);
      assert.equal(result.pass, false, 'known-wrong record must fail');
      return result;
    };
    mutate(journey => { delete journey.before['workspace/.brain/docs/investigation.json']; });
    mutate(journey => {
      const file = 'workspace/.brain/docs/investigation.json';
      const record = JSON.parse(journey.before[file]);
      record.hypothesis.status = 'accepted';
      journey.before[file] = JSON.stringify(record);
    });
    mutate(journey => {
      const file = 'workspace/.brain/docs/investigation.json';
      const record = JSON.parse(journey.before[file]);
      record.nextWork = 'demo-blocked';
      journey.before[file] = JSON.stringify(record);
    });
    mutate(journey => { journey.secondInput.prompt += journey.first.response.output; });
    mutate(journey => { journey.secondInput.prompt += journey.first.response.sessionId; });
    mutate((journey, candidate) => { candidate.sessionId = journey.first.response.sessionId; });
    mutate(journey => { journey.secondInput.fresh.persist_threads = true; });
    mutate(journey => { journey.secondCalls = ''; });
    mutate(journey => {
      const file = 'workspace/.brain/docs/investigation.json';
      const record = JSON.parse(journey.before[file]);
      record.discovery.evidence.sha256 = 'unverified';
      journey.before[file] = JSON.stringify(record);
    });
    const missing = mutate(journey => { delete journey.first.response; });
    assert.match(missing.reason, /INCONCLUSIVE/);
    assert.match(grade({...response, metadata: {}}).reason, /INCONCLUSIVE/);
    const report = path.join(root, 'workspace/.brain/docs/continuation-check.json');
    const good = fs.readFileSync(report, 'utf8');
    for (const wrong of [
      {...JSON.parse(good), discovery: null},
      {...JSON.parse(good), hypothesis: {claim: 'Fixed backoff may explain the timeout', status: 'accepted'}},
      {...JSON.parse(good), nextWork: 'demo-blocked'},
      {...JSON.parse(good), requiresApproval: false},
    ]) {
      fs.writeFileSync(report, JSON.stringify(wrong));
      assert.equal(grade(response).pass, false);
    }
    fs.writeFileSync(report, good);
    const absentRead = structuredClone(response);
    if (runtime.startsWith('anthropic:')) absentRead.metadata.toolCalls = [];
    else {
      const raw = JSON.parse(absentRead.raw);
      raw.notifications = raw.notifications.filter(event => event.method === 'turn/completed');
      absentRead.raw = JSON.stringify(raw);
    }
    assert.match(grade(absentRead).reason, /INCONCLUSIVE.*read/);
    provider.config.nativeConfig = {resume: 'first-session'};
    await assert.rejects(provider.callApi(vars.request, {vars}), /fresh sessions/);
    assert.equal(inputs.length, 2, 'resume options must be refused before contacting the provider');
  }
});

test('Promptfoo runs each two-session case as one fixture with the real hooks and no model calls', async () => {
  const config = yaml.load(fs.readFileSync(path.join(__dirname, '../promptfooconfig.yaml'), 'utf8'));
  const roots = [];
  const adapters = [];
  try {
    const tests = await Promise.all(scenarios.map(async scenario => {
      const provider = await loadApiProvider(scenario.provider.id, {
        basePath: path.join(__dirname, '../tests'), options: scenario.provider,
      });
      const adapter = replay(scenario.provider.config.runtime);
      adapters.push(adapter);
      provider.loadProvider = adapter.provider.loadProvider;
      const call = provider.callApi.bind(provider);
      provider.callApi = async (prompt, context) => {
        roots.push(context.vars.fixtureRoot);
        return call(prompt, context);
      };
      return {...scenario, provider};
    }));
    const nativeIds = scenarios.map(scenario => scenario.provider.config.runtime);
    const record = await evaluate({...config, tracing: {enabled: false}, writeLatestResults: false,
      tests, providers: nativeIds.map(id => ({id: () => id,
        config: id.startsWith('anthropic:') ? {effort: 'medium'}
          : {model_reasoning_effort: 'medium', cli_config: {model_provider: 'synthetic'}},
        callApi: async () => {
        throw new Error('The two-session case must use its existing-runtime adapter');
      }}))}, {cache: false, maxConcurrency: 1});
    const summary = await record.toEvaluateSummary();
    assert.equal(summary.results.length, 2);
    assert.equal(summary.stats.successes, 2, JSON.stringify(summary.results.map(result => result.error)));
    assert.equal(new Set(roots).size, 2);
    for (const adapter of adapters) {
      assert.equal(adapter.loaded.length, 2);
      for (const native of adapter.loaded) {
        if (native.effort) assert.equal(native.effort, 'medium');
        else {
          assert.equal(native.model_reasoning_effort, 'medium');
          assert.deepEqual(native.cli_config, {model_provider: 'synthetic'});
        }
      }
    }
    for (const result of summary.results) {
      assert.equal(result.gradingResult.componentResults.length, 6);
      assert.ok(result.gradingResult.componentResults.every(part => part.pass));
    }
    for (const root of roots) {
      assert.ok(fs.existsSync(path.join(root, 'result.json')));
      assert.ok(!fs.existsSync(path.join(root, 'home/.codex/auth.json')));
    }
  } finally {
    const results = path.resolve(__dirname, '../results');
    for (const root of roots) {
      assert.ok(fs.realpathSync(root).startsWith(results + path.sep));
      fs.rmSync(root, {recursive: true, force: true});
    }
  }
});
