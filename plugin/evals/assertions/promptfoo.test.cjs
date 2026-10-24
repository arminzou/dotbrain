const {test, after} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const yaml = require('js-yaml');

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
