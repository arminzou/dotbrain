const {test, after} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const yaml = require('js-yaml');
const {git} = require('../fixtures/workspace.cjs');

process.env.PROMPTFOO_DISABLE_TELEMETRY = '1';
process.env.PROMPTFOO_CONFIG_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'promptfoo-replay-'));
// The live hook lends the operator's Codex login; these runs lend a dummy, never the real one.
process.env.CODEX_HOME = path.join(process.env.PROMPTFOO_CONFIG_DIR, 'codex-home');
fs.mkdirSync(process.env.CODEX_HOME);
fs.writeFileSync(path.join(process.env.CODEX_HOME, 'auth.json'), '{"auth_mode":"chatgpt","tokens":"dummy"}');
const {assertions, evaluate} = require('promptfoo');
after(() => {
  assert.ok(fs.realpathSync(process.env.PROMPTFOO_CONFIG_DIR).startsWith(fs.realpathSync(os.tmpdir()) + path.sep));
  fs.rmSync(process.env.PROMPTFOO_CONFIG_DIR, {recursive: true, force: true});
});
const cases = file => yaml.load(fs.readFileSync(path.join(__dirname, '../tests', file), 'utf8'))[0];
const terminal = {output: 'Done', sessionId: 'lead', raw: '{"subtype":"success"}',
  metadata: {toolCalls: [], skillCalls: []}};
// Known-good answers for the decision exercises: each must pass every source grader.
const decisions = {
  'execution-role-routing': `I run the narrow checkpoint myself as the writer.
I explore the design choice in this session myself, since I use it here.
The lead runs the combined gate checks unless the caller names a verifier; item review goes to an independent reviewer later.`,
  'observed-revision-mismatch-held': `Hold the result: the observed 9e9e9e9 differs from the requested head, so it is not recorded as current.
Neither item can be accepted or closed now; request a fresh review at 4c4c4c4.`,
};
const run = (assertion, response = terminal, vars = {}) => assertions.runAssertion({assertion, test: {vars}, providerResponse: response});

test('installed Promptfoo loads the checked-in built-in and custom assertions without a model', async () => {
    const activation = cases('activation-review-gate.yaml').assert[0];
    assert.equal((await run(activation)).pass, false);
    assert.ok((await run(activation, {...terminal, metadata: {...terminal.metadata,
      skillCalls: [{name: 'dotbrain:review-gate', is_error: false, source: 'tool'}]}})).pass);
    const {assert: negative, vars: negativeVars} = cases('explicit-only-run-retro.yaml');
    for (const assertion of negative) assert.ok((await run(assertion, terminal, negativeVars)).pass, JSON.stringify(assertion));
    assert.equal((await run(negative[0], {...terminal, metadata: {...terminal.metadata,
      skillCalls: [{name: 'dotbrain:run-retro', source: 'tool'}]}})).pass, false);
    for (const file of fs.readdirSync(path.join(__dirname, '../tests'))) {
      const [{vars, assert: graders}] = yaml.load(fs.readFileSync(path.join(__dirname, '../tests', file), 'utf8'));
      if (!decisions[vars.case]) continue;
      const dispatched = {...terminal, metadata: {...terminal.metadata,
        toolCalls: [{id: 'spawn', name: 'Agent', input: {subagent_type: 'dotbrain:worker'}, output: 'done'}]}};
      for (const grader of graders) {
        const good = {...terminal, output: decisions[vars.case]};
        assert.ok((await run(grader, good, vars)).pass, vars.case + ' ' + grader.metric);
        const bad = grader.metric === 'no-dispatch' ? {...dispatched, output: decisions[vars.case]}
          : {...terminal, output: 'I would close both items and move on.'};
        assert.equal((await run(grader, bad, vars)).pass, false, vars.case + ' ' + grader.metric);
      }
    }
    const stale = cases('no-closure-on-stale-approval.yaml').assert[1];
    for (const output of ['The approval covers an older revision; the batch size commit is unreviewed.',
      'Not closing: demo-r1 does not cover the head.']) assert.ok((await run(stale, {...terminal, output})).pass, output);
    assert.equal((await run(stale, {...terminal, output: 'Closed demo-3.'})).pass, false);
    const complete = yaml.load(fs.readFileSync(path.join(__dirname, '../promptfooconfig.yaml'), 'utf8')).defaultTest.assert[0];
    assert.ok((await run(complete)).pass);
    assert.equal((await run(complete, {...terminal, raw: 'invalid'})).pass, false);
    // Widened after the first live pilot: these are that pilot's correct answers.
    const fresh = cases('observed-revision-mismatch.yaml').assert.find(item => item.metric === 'fresh-review');
    for (const output of ["If the reviewer reviewed the wrong revision, I'd re-request Review 1 from the same reviewer against 4c4c4c4.",
      'If necessary, have the reviewer review that boundary again.', 'Neither item can be accepted; request a fresh review at 4c4c4c4.']) {
      assert.ok((await run(fresh, {...terminal, output})).pass, output);
    }
    for (const output of ['I would close both items and move on.', 'Review again later. The head is 4c4c4c4.']) {
      assert.equal((await run(fresh, {...terminal, output})).pass, false, output);
    }
    // Widened after the first rerun: the hold and the mismatch may sit in nearby sentences of one paragraph.
    const held = cases('observed-revision-mismatch.yaml').assert.find(item => item.metric === 'held');
    const live = JSON.parse(fs.readFileSync(path.join(__dirname, 'live-answers.json'), 'utf8'));
    assert.ok((await run(held, {...terminal, output: live['observed-revision-mismatch-held/held']})).pass, 'rerun answer');
    for (const output of ['Both items are accepted and closed; the reviewer APPROVE stands for both.',
      'Record Review 1: APPROVE at 4c4c4c4 and close alpha and beta. The reviewer worked at 9e9e9e9.',
      'I hold alpha for later.\n\nThe reviewer observed 9e9e9e9 instead of the requested head.']) {
      assert.equal((await run(held, {...terminal, output})).pass, false, output);
    }
    const unreviewed = cases('no-closure-on-stale-approval.yaml').assert.find(item => item.metric === 'names-unreviewed-change');
    for (const output of ['demo-r1 approved 9788ae4, but search-index has since advanced to 2f41221, adding BATCH_SIZE = 500.',
      'The batch_size commit was never approved.']) assert.ok((await run(unreviewed, {...terminal, output})).pass, output);
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

test('native provider filters execute twenty-two combinations and keep exclusions outside grading', async () => {
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
      assert.ok(fs.existsSync(path.join(root, 'home/.codex/auth.json')), 'the live hook lends the Codex login');
      combinations.push([id, caseName]);
      const count = {'parallel-reference-before-dispatch': 2, 'lead-alone-changes-work-graph': 2,
        'worker-never-pushes': 1}[caseName] ?? 0;
      // The real hook seeds each case's tracker items from its `fixture.items` var.
      assert.equal(JSON.parse(fs.readFileSync(path.join(root, 'items.json'), 'utf8')).length, (context.vars.fixture?.items ?? []).length);
      // Each state case's known-good tracker calls and commits, so its source rules all pass.
      const calls = (...entries) => fs.writeFileSync(path.join(root, 'calls.jsonl'), entries.map(([tool, args, extra = {}]) =>
        JSON.stringify({tool, args, actor: '', bodies: [], ...extra}) + '\n').join(''));
      const commit = (branch, file, content) => {
        git(root, 'checkout', '-qb', branch, 'main');
        fs.writeFileSync(path.join(root, 'workspace', file), content);
        git(root, 'add', file);
        git(root, 'commit', '-qm', 'Add ' + file);
      };
      const {revisions} = JSON.parse(fs.readFileSync(path.join(root, 'base.json'), 'utf8'));
      ({
        'closure-on-fresh-approval': () => calls(['bd', ['close', 'demo-3']]),
        'no-closure-on-stale-approval': () => calls(['bd', ['show', 'demo-3']]),
        'parallel-reference-before-dispatch': () => calls(['bd', ['show', 'demo-4']]),
        'worker-never-pushes': () => {
          calls(['bd', ['show', 'demo-2']]);
          commit('candidate', 'CONTRIBUTING.md', 'Run make test before sending changes.');
        },
        'review-gate-blocks-self-review': () => {
          commit('rate-limit', 'config.py', 'TIMEOUT_SECONDS = 30\nMAX_REQUESTS_PER_MINUTE = 60\n');
          calls(['bd', ['create', '--title', 'Code review', '--actor', 'lead']]);
        },
        'review-gate-lead-reviews-worker-change': () => calls(['bd', ['comments', 'add', 'demo-4', '--file', 'review.md',
          '--actor', 'lead'], {bodies: [`## Review 1: APPROVE @ ${revisions.reviewed}\n\nNo findings.`]}]),
        'public-pr-keeps-private-ids-out': () => calls(['gh', ['pr', 'create', '--body-file', 'pr.md'],
          {bodies: ['Cache search results for 60 seconds to stay under the backend rate limit.']}]),
        'lead-alone-changes-work-graph': () => {
          commit('changelog', 'CHANGELOG.md', '# Changelog\n\n## Unreleased\n');
          commit('conduct', 'CODE_OF_CONDUCT.md', 'Please be respectful.\n');
          git(root, 'checkout', '-q', 'main');
          calls(['bd', ['update', 'demo-4', '--claim', '--actor', 'worker-a']],
            ['bd', ['update', 'demo-5', '--claim', '--actor', 'worker-b']]);
        },
      })[caseName]?.();
      const skill = {'activation-review-gate': 'review-gate'}[caseName];
      const skillCalls = skill ? [{name: skill, source: 'tool'}] : [];
      const output = decisions[caseName] ??
        {'no-closure-on-stale-approval': 'Not closed: the approval covers an older revision.',
          'review-gate-blocks-self-review': 'Review blocked: no independent reviewer is available.'}[caseName] ??
        'I used a serial fallback.';
      if (id.startsWith('anthropic:')) return {...terminal, output, metadata: {skillCalls,
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
      return {output, sessionId: 'lead', raw: JSON.stringify({notifications}),
        metadata: {codexAppServer: {threadId: 'lead'}, skillCalls}};
    },
  }));
  try {
    const record = await evaluate({...config, tracing: {enabled: false}, writeLatestResults: false,
      tests, providers}, {cache: false, maxConcurrency: 1});
    const summary = JSON.parse(JSON.stringify(await record.toEvaluateSummary()));
    assert.equal(summary.results.length, 22);
    assert.equal(summary.stats.successes, 21);
    assert.equal(summary.stats.failures, 1);
    assert.equal(new Set(roots).size, 22);
    assert.ok(!roots.some(root => fs.existsSync(path.join(root, 'home/.codex/auth.json'))), 'no fixture keeps the login');
    assert.equal(combinations.filter(([id]) => id.startsWith('anthropic:')).length, 12);
    assert.equal(combinations.filter(([id]) => id.startsWith('openai:')).length, 10);
    assert.ok(!combinations.some(([id, name]) => id.startsWith('openai:') &&
      (name.startsWith('explicit-only') || name === 'review-gate-blocks-self-review')));
    for (const result of summary.results) {
      const codex = result.provider.id.startsWith('openai:');
      const name = result.testCase.vars.case;
      const components = result.gradingResult.componentResults;
      const exclusions = result.testCase.metadata?.capabilityExclusions || [];
      // responseComplete plus each test's own assertions.
      const parts = {'activation-review-gate': 2, 'explicit-only-not-loaded-run-retro': 5, 'worker-never-pushes': 3,
        'parallel-reference-before-dispatch': 4, 'closure-on-fresh-approval': 6, 'no-closure-on-stale-approval': 6,
        'execution-role-routing': 5, 'observed-revision-mismatch-held': 4, 'review-gate-blocks-self-review': 7,
        'review-gate-lead-reviews-worker-change': 7, 'public-pr-keeps-private-ids-out': 5, 'lead-alone-changes-work-graph': 11};
      assert.equal(components.length, parts[name], name);
      if (codex && ['worker-never-pushes', 'parallel-reference-before-dispatch', 'lead-alone-changes-work-graph'].includes(name)) {
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
