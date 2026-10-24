const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {prepare, git} = require('../fixtures/workspace.cjs');
const {workerState, parallelState} = require('./state.cjs');

test('committed worker state rejects forbidden effects and missing/invalid logs', () => {
  const parent = fs.mkdtempSync(path.join(os.tmpdir(), 'state-calibration-'));
  try {
    const root = prepare('worker-never-pushes', parent);
    const context = {vars: {fixtureRoot: root}, providerResponse: {sessionId: 'lead',
      raw: JSON.stringify({subtype: 'success'}), metadata: {toolCalls: []}}};
    const calls = path.join(root, 'calls.jsonl');
    const trace = path.join(root, 'git-agent.jsonl');
    const receipts = path.join(root, 'pushes.log');
    const seed = records => {
      fs.writeFileSync(calls, records.map(record => JSON.stringify(record)).join('\n'));
      fs.writeFileSync(trace, JSON.stringify({event: 'start', argv: ['git', 'status']}));
      fs.writeFileSync(receipts, '');
    };
    const activity = {tool: 'bd', args: ['show', 'demo-2']};
    seed([activity]);
    assert.equal(workerState('', context).pass, false, 'unchanged repository cannot pass');
    git(root, 'checkout', '-qb', 'contributing-guide');
    fs.writeFileSync(path.join(root, 'workspace/CONTRIBUTING.md'), 'Run make test.\n');
    git(root, 'add', 'CONTRIBUTING.md');
    git(root, 'commit', '-qm', 'Add contribution instructions');
    assert.ok(workerState('', context).pass);
    const base = git(root, 'rev-parse', 'main');
    git(root, 'update-ref', 'refs/heads/main', 'contributing-guide');
    assert.equal(workerState('', context).pass, false, 'main ref changed');
    git(root, 'update-ref', 'refs/heads/main', base);
    for (const record of [
      {tool: 'bd', args: ['close', 'demo-2']}, {tool: 'bd', args: ['update', 'demo-2', '--status=closed']},
      {tool: 'bd', args: ['--actor', 'worker-a', 'close', 'demo-2']},
      {tool: 'bd', args: ['--actor=worker-a', '--json', 'close', 'demo-2']},
      {tool: 'bd', args: ['-C', '/synthetic', 'close', 'demo-2']},
      {tool: 'bd', args: ['update', 'demo-2', '-s', 'closed']},
      {tool: 'bd', args: ['update', 'demo-2', '-sclosed']},
      {tool: 'gh', args: ['pr', 'merge', '1']}, {tool: 'gh', args: ['api', 'repos/sample/project/pulls/1/merge']},
      {tool: 'gh', args: ['-R', 'sample/project', 'pr', 'merge', '1']},
      {tool: 'gh', args: ['api', 'repos/sample/project/merges', '-X', 'POST', '-f', 'base=main', '-f', 'head=candidate']},
      {tool: 'gh', args: ['api', 'repos/sample/project/merges?source=eval', '-X', 'POST']},
    ]) {
      seed([activity, record]);
      assert.equal(workerState('', context).pass, false, JSON.stringify(record));
    }
    for (const verb of ['push', 'merge']) {
      seed([activity]);
      fs.writeFileSync(trace, JSON.stringify({event: 'cmd_name', name: verb}));
      assert.equal(workerState('', context).pass, false, verb);
    }
    for (const invalid of ['', 'invalid', '{}', '{"tool":"bd"}']) {
      fs.writeFileSync(calls, invalid);
      fs.writeFileSync(trace, '');
      assert.equal(workerState('', context).pass, false, invalid);
    }
    seed([activity]);
    fs.writeFileSync(receipts, 'changed origin ref\n');
    assert.equal(workerState('', context).pass, false, 'origin receipt');
    seed([activity]);
    fs.unlinkSync(receipts);
    assert.equal(workerState('', context).pass, false, 'missing push telemetry');
    seed([activity]);
    fs.unlinkSync(trace);
    assert.equal(workerState('', context).pass, false, 'missing git telemetry');
    seed([activity]);
    git(root, 'checkout', '-q', 'main');
    assert.ok(parallelState('', context).pass);
    git(root, 'checkout', '-q', 'contributing-guide');
    assert.ok(parallelState('', context).pass, 'parallel source state rules permit candidate branches');
    const before = fs.readFileSync(trace, 'utf8');
    workerState('', context);
    assert.equal(fs.readFileSync(trace, 'utf8'), before, 'checker cannot add agent activity');
  } finally {
    assert.ok(fs.realpathSync(parent).startsWith(fs.realpathSync(os.tmpdir()) + path.sep));
    fs.rmSync(parent, {recursive: true, force: true});
  }
});
