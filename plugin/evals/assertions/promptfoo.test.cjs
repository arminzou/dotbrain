const {test, after} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const yaml = require('js-yaml');
const {git} = require('../fixtures/workspace.cjs');

process.env.PROMPTFOO_DISABLE_TELEMETRY = '1';
process.env.PROMPTFOO_CONFIG_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'promptfoo-replay-'));
const {assertions, evaluate} = require('promptfoo');
after(() => {
  assert.ok(fs.realpathSync(process.env.PROMPTFOO_CONFIG_DIR).startsWith(fs.realpathSync(os.tmpdir()) + path.sep));
  fs.rmSync(process.env.PROMPTFOO_CONFIG_DIR, {recursive: true, force: true});
});
const cases = file => yaml.load(fs.readFileSync(path.join(__dirname, '../tests', file), 'utf8'))[0];
const terminal = {output: 'Done', sessionId: 'lead', raw: '{"subtype":"success"}',
  metadata: {toolCalls: [], skillCalls: []}};
const run = (assertion, response = terminal) => assertions.runAssertion({assertion, test: {vars: {}}, providerResponse: response});

test('installed Promptfoo loads the checked-in built-in and custom assertions without a model', async () => {
    const activation = cases('activation-review-gate.yaml').assert[0];
    assert.equal((await run(activation)).pass, false);
    assert.ok((await run(activation, {...terminal, metadata: {...terminal.metadata,
      skillCalls: [{name: 'dotbrain:review-gate', is_error: false, source: 'tool'}]}})).pass);
    const negative = cases('explicit-only-run-retro.yaml').assert;
    for (const assertion of negative) assert.ok((await run(assertion)).pass, JSON.stringify(assertion));
    assert.equal((await run(negative[0], {...terminal, metadata: {...terminal.metadata,
      skillCalls: [{name: 'dotbrain:run-retro', source: 'tool'}]}})).pass, false);
    const complete = yaml.load(fs.readFileSync(path.join(__dirname, '../promptfooconfig.yaml'), 'utf8')).defaultTest.assert[0];
    assert.ok((await run(complete)).pass);
    assert.equal((await run(complete, {...terminal, raw: 'invalid'})).pass, false);
    const fallback = cases('parallel-reference.yaml').assert[2];
    assert.ok((await run(fallback, {...terminal, output: 'I used a serial fallback.'})).pass);
    assert.equal((await run(fallback, {...terminal, output: 'Dispatched workers.'})).pass, false);
});

test('the actual Promptfoo evaluator runs the workspace hook and prompt config with an offline provider', async () => {
  const config = yaml.load(fs.readFileSync(path.join(__dirname, '../promptfooconfig.yaml'), 'utf8'));
  const previous = {live: process.env.DOTBRAIN_EVAL_LIVE, model: process.env.EVAL_CLAUDE_MODEL};
  process.env.DOTBRAIN_EVAL_LIVE = '1';
  process.env.EVAL_CLAUDE_MODEL = 'offline-fixture';
  let root;
  try {
    const record = await evaluate({...config, tracing: {enabled: false}, writeLatestResults: false,
      tests: [cases('activation-review-gate.yaml')],
      providers: [{id: () => 'anthropic:claude-agent-sdk', callApi: async (prompt, context) => {
        root = context.vars.fixtureRoot;
        assert.equal(context.prompt.config.working_dir, path.join(root, 'workspace'));
        assert.equal(context.prompt.config.env.CODEX_HOME, path.join(root, 'home/.codex'));
        assert.equal(context.prompt.config.model, 'offline-fixture');
        assert.match(prompt, /code review gate/);
        return {...terminal, metadata: {...terminal.metadata,
          skillCalls: [{name: 'dotbrain:review-gate', source: 'tool'}]}};
      }}]}, {cache: false, maxConcurrency: 1});
    const summary = await record.toEvaluateSummary();
    assert.equal(summary.results.length, 1);
    assert.equal(summary.stats.successes, 1, JSON.stringify(summary.results));
    assert.ok(fs.existsSync(path.join(root, 'result.json')));
  } finally {
    for (const [key, value] of [['DOTBRAIN_EVAL_LIVE', previous.live], ['EVAL_CLAUDE_MODEL', previous.model]]) {
      if (value === undefined) delete process.env[key]; else process.env[key] = value;
    }
    if (root) {
      const results = fs.realpathSync(path.join(__dirname, '../results'));
      assert.ok(fs.realpathSync(root).startsWith(results + path.sep));
      fs.rmSync(root, {recursive: true, force: true});
    }
  }
});

test('native provider filters execute seven combinations and keep exclusions outside grading', async () => {
  const config = yaml.load(fs.readFileSync(path.join(__dirname, '../promptfooconfig.yaml'), 'utf8'));
  const tests = fs.readdirSync(path.join(__dirname, '../tests')).filter(file => file.endsWith('.yaml'))
    .flatMap(file => yaml.load(fs.readFileSync(path.join(__dirname, '../tests', file), 'utf8')));
  const keys = ['DOTBRAIN_EVAL_LIVE', 'EVAL_CLAUDE_MODEL', 'EVAL_CODEX_MODEL'];
  const previous = keys.map(key => process.env[key]);
  keys.forEach(key => { process.env[key] = key === 'DOTBRAIN_EVAL_LIVE' ? '1' : 'offline-fixture'; });
  const roots = [];
  const combinations = [];
  const providers = ['anthropic:claude-agent-sdk', 'openai:codex-app-server'].map(id => ({
    id: () => id,
    callApi: async (prompt, context) => {
      const {fixtureRoot: root, case: caseName} = context.vars;
      roots.push(root);
      combinations.push([id, caseName]);
      const count = caseName === 'parallel-reference-before-dispatch' ? 2 : caseName === 'worker-never-pushes' ? 1 : 0;
      if (count) fs.writeFileSync(path.join(root, 'calls.jsonl'), JSON.stringify({tool: 'bd', args: ['show', 'demo-2']}) + '\n');
      if (caseName === 'worker-never-pushes') {
        git(root, 'checkout', '-qb', 'candidate');
        fs.writeFileSync(path.join(root, 'workspace/CONTRIBUTING.md'), 'Run make test before sending changes.');
        git(root, 'add', 'CONTRIBUTING.md');
        git(root, 'commit', '-qm', 'Add contributing guide');
      }
      const skillCalls = caseName === 'activation-review-gate' ? [{name: 'review-gate', source: 'tool'}] : [];
      if (id.startsWith('anthropic:')) return {...terminal, output: 'I used a serial fallback.', metadata: {skillCalls,
        toolCalls: Array.from({length: count}, (_, i) => [
          {id: 'spawn-' + i, name: 'Agent', input: {subagent_type: 'dotbrain:worker'}, output: 'done'},
          {id: 'child-' + i, name: 'Read', input: {file_path: 'README.md'}, output: 'sample', parentToolUseId: 'spawn-' + i},
        ]).flat()}};
      const item = (method, item) => ({method, params: {threadId: 'lead', item}});
      const notifications = [item('item/completed', {id: 'read', type: 'commandExecution',
        command: 'cat .agents/skills/run-execution/references/parallel-execution.md', status: 'completed', exitCode: 0,
        cwd: path.join(root, 'workspace'),
        commandActions: [{type: 'read', path: '.agents/skills/run-execution/references/parallel-execution.md'}],
        aggregatedOutput: fs.readFileSync(path.join(root, 'workspace/.agents/skills/run-execution/references/parallel-execution.md'), 'utf8')})];
      for (let i = 0; i < count; i++) {
        const spawn = {id: 'spawn-' + i, type: 'collabAgentToolCall', tool: 'spawnAgent',
          status: 'completed', senderThreadId: 'lead', receiverThreadIds: ['child-' + i],
          agentsStates: {['child-' + i]: {status: 'completed'}}};
        notifications.push(item('item/started', {...spawn, status: 'inProgress'}), item('item/completed', spawn));
      }
      notifications.push({method: 'turn/completed', params: {threadId: 'lead', turn: {status: 'completed'}}});
      return {output: 'I used a serial fallback.', sessionId: 'lead', raw: JSON.stringify({notifications}),
        metadata: {codexAppServer: {threadId: 'lead'}, skillCalls}};
    },
  }));
  try {
    const record = await evaluate({...config, tracing: {enabled: false}, writeLatestResults: false,
      tests, providers}, {cache: false, maxConcurrency: 1});
    const summary = JSON.parse(JSON.stringify(await record.toEvaluateSummary()));
    assert.equal(summary.results.length, 7);
    assert.equal(summary.stats.successes, 6);
    assert.equal(summary.stats.failures, 1);
    assert.equal(new Set(roots).size, 7);
    assert.equal(combinations.filter(([id]) => id.startsWith('anthropic:')).length, 4);
    assert.equal(combinations.filter(([id]) => id.startsWith('openai:')).length, 3);
    assert.ok(!combinations.some(([id, name]) => id.startsWith('openai:') && name.startsWith('explicit-only')));
    for (const result of summary.results) {
      const codex = result.provider.id.startsWith('openai:');
      const name = result.testCase.vars.case;
      const components = result.gradingResult.componentResults;
      const exclusions = result.testCase.metadata?.capabilityExclusions || [];
      assert.equal(components.length, name === 'activation-review-gate' ? 2 : name === 'worker-never-pushes' ? 3 : 5);
      if (codex && ['worker-never-pushes', 'parallel-reference-before-dispatch'].includes(name)) {
        assert.equal(exclusions[0].status, 'SKIPPED_UNSUPPORTED');
        assert.ok(components.some(part => /CodexWorkers?Dispatched|codexWorkerDispatched/.test(part.assertion.value)));
        assert.ok(!components.some(part => /:workerDispatched|:twoWorkersDispatched/.test(part.assertion.value)));
      }
      assert.ok(!components.some(part => part.assertion.type === 'SKIPPED_UNSUPPORTED'));
      // No fabricated Claude timing spans: the offline replay must fail its order check.
      if (!codex && name === 'parallel-reference-before-dispatch') {
        assert.equal(result.success, false);
        assert.ok(components.some(part => /INCONCLUSIVE.*completion order/.test(part.reason)));
      } else assert.ok(result.success, JSON.stringify(result));
    }
    const negative = summary.results.find(result => result.testCase.vars.case.startsWith('explicit-only'));
    assert.equal(negative.gradingResult.componentResults.length, 5);
    assert.equal(negative.testCase.metadata.capabilityExclusions[0].provider, 'openai:codex-app-server');
  } finally {
    keys.forEach((key, i) => { if (previous[i] === undefined) delete process.env[key]; else process.env[key] = previous[i]; });
    const results = fs.realpathSync(path.join(__dirname, '../results'));
    for (const root of roots) {
      assert.ok(fs.realpathSync(root).startsWith(results + path.sep));
      fs.rmSync(root, {recursive: true, force: true});
    }
  }
});
