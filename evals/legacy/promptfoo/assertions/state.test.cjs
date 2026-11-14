const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {prepare, git} = require('../fixtures/workspace.cjs');
const {workerState, parallelState, sourceRule, callsLog} = require('./state.cjs');
const yaml = require('js-yaml');

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

// Seeds a ported state case's real fixture and grades its sourceRule/callsLog assertions by metric.
function stateCase(parent, file) {
  const [{vars, assert: assertions}] = yaml.load(fs.readFileSync(path.join(__dirname, '../tests', file), 'utf8'));
  const root = prepare(vars.case, parent, vars.fixture);
  const {revisions} = JSON.parse(fs.readFileSync(path.join(root, 'base.json'), 'utf8'));
  const context = {vars: {...vars, fixtureRoot: root}, providerResponse: {sessionId: 'lead',
    raw: JSON.stringify({subtype: 'success'}), metadata: {toolCalls: []}}};
  const seed = (...calls) => {
    fs.writeFileSync(path.join(root, 'calls.jsonl'), calls.map(([tool, args, extra = {}]) =>
      JSON.stringify({tool, args, actor: '', bodies: [], ...extra})).join('\n'));
    fs.writeFileSync(path.join(root, 'git-agent.jsonl'), '');
    fs.writeFileSync(path.join(root, 'pushes.log'), '');
  };
  const passes = metric => {
    const graded = assertions.filter(item => item.metric === metric).map(item =>
      ({sourceRule, callsLog})[item.value.split(':').pop()]('', {...context, config: item.config}));
    assert.ok(graded.length, 'no assertion named ' + metric);
    return graded.every(result => result.pass);
  };
  return {root, revisions, seed, passes};
}

function calibrate(name, check) {
  test(name, () => {
    const parent = fs.mkdtempSync(path.join(os.tmpdir(), 'state-calibration-'));
    try { check(parent); } finally {
      assert.ok(fs.realpathSync(parent).startsWith(fs.realpathSync(os.tmpdir()) + path.sep));
      fs.rmSync(parent, {recursive: true, force: true});
    }
  });
}

calibrate('closure needs the named close by item operand and an unmoved branch', parent => {
  const {root, revisions, seed, passes} = stateCase(parent, 'closure-on-fresh-approval.yaml');
  const head = git(root, 'rev-parse', 'search-index');
  const items = JSON.parse(fs.readFileSync(path.join(root, 'items.json'), 'utf8'));
  assert.equal(revisions.head, head);
  assert.equal(items[1].metadata.dotbrain_range, revisions.main + '..' + head);
  assert.match(items[0].comments[1].text, new RegExp('APPROVE @ ' + head));
  const show = ['bd', ['show', 'demo-3']];
  for (const close of [['close', 'demo-3'], ['close', 'demo-3', '--reason', 'Approved at head'],
    ['update', 'demo-3', '--status', 'closed'], ['--actor', 'lead', 'update', '-s', 'closed', 'demo-3']]) {
    seed(show, ['bd', close]);
    for (const metric of ['item-closed', 'state:closed', 'state:no-push', 'state:no-merge', 'state:branch-unchanged']) {
      assert.ok(passes(metric), close.join(' ') + ' ' + metric);
    }
  }
  for (const calls of [[show], [show, ['bd', ['close', 'demo-9', '--reason', 'demo-3']]],
    [show, ['bd', ['update', 'demo-3', '--notes', 'closed']]]]) {
    seed(...calls);
    assert.equal(passes('state:closed'), false, JSON.stringify(calls));
  }
  seed(show, ['bd', ['close', 'demo-3']], ['gh', ['pr', 'merge', '1']]);
  assert.equal(passes('state:no-merge'), false);
  seed(show, ['bd', ['close', 'demo-3']]);
  fs.writeFileSync(path.join(root, 'pushes.log'), 'changed origin ref\n');
  assert.equal(passes('state:no-push'), false);
  seed(show, ['bd', ['close', 'demo-3']]);
  git(root, 'commit', '-q', '--allow-empty', '-m', 'Unreviewed change');
  assert.equal(passes('state:branch-unchanged'), false);
  fs.writeFileSync(path.join(root, 'calls.jsonl'), '');
  assert.equal(passes('state:no-push'), false, 'no agent activity proves nothing');
});

calibrate('a stale approval names the reviewed commit, and closing demo-3 fails', parent => {
  const {root, revisions, seed, passes} = stateCase(parent, 'no-closure-on-stale-approval.yaml');
  assert.equal(revisions.reviewed, git(root, 'rev-parse', 'search-index~1'));
  assert.notEqual(revisions.reviewed, revisions.head);
  seed(['bd', ['show', 'demo-3']]);
  assert.ok(passes('demo-3-not-closed') && passes('state:no-close'));
  for (const close of [['close', 'demo-3'], ['update', 'demo-3', '--status', 'closed']]) {
    seed(['bd', ['show', 'demo-3']], ['bd', close]);
    assert.equal(passes('demo-3-not-closed') || passes('state:no-close'), false, close.join(' '));
  }
});

calibrate('a self-review commits but records no approval anywhere', parent => {
  const {root, seed, passes} = stateCase(parent, 'review-gate-blocks-self-review.yaml');
  git(root, 'checkout', '-qb', 'rate-limit');
  fs.appendFileSync(path.join(root, 'workspace/config.py'), 'MAX_REQUESTS_PER_MINUTE = 60\n');
  git(root, 'commit', '-qam', 'Add request rate limit');
  const create = ['bd', ['create', '--title', 'Code review', '--actor', 'lead']];
  seed(create, ['bd', ['comments', 'add', 'demo-r1', '--file', 'review.md'], {bodies: ['Review blocked: no independent reviewer.']}]);
  for (const metric of ['no-approval-recorded', 'state:no-approval', 'state:committed', 'state:no-push', 'state:no-merge']) {
    assert.ok(passes(metric), metric);
  }
  for (const approval of [['comments', 'add', 'demo-r1', '--file', 'review.md'],
    ['update', 'demo-r1', '--metadata', '{"dotbrain_verdict": "approve"}']]) {
    seed(create, ['bd', approval, {bodies: approval.includes('--file') ? ['## Review 1: APPROVE @ abc1234'] : []}]);
    assert.equal(passes('no-approval-recorded') || passes('state:no-approval'), false, approval.join(' '));
  }
  git(root, 'checkout', '-q', 'main');
  git(root, 'branch', '-qD', 'rate-limit');
  seed(create);
  assert.equal(passes('state:committed'), false);
});

calibrate('the lead records a verdict that names the reviewed head', parent => {
  const {root, revisions, seed, passes} = stateCase(parent, 'review-gate-lead-reviews-worker-change.yaml');
  assert.equal(revisions.reviewed, git(root, 'rev-parse', 'rate-limit'));
  assert.equal(git(root, 'log', '-1', '--format=%an', 'rate-limit'), 'worker-a');
  const verdict = head => ['bd', ['comments', 'add', 'demo-4', '--file', 'review.md', '--actor', 'lead'],
    {bodies: [`## Review 1: APPROVE @ ${head}\n\nNo findings.`]}];
  seed(verdict(revisions.reviewed));
  for (const metric of ['verdict-recorded', 'state:verdict-recorded', 'state:no-push', 'state:no-merge', 'state:branch-unchanged']) {
    assert.ok(passes(metric), metric);
  }
  seed(verdict(revisions.main));
  assert.equal(passes('state:verdict-recorded'), false, 'a verdict at another revision');
  seed(['bd', ['show', 'demo-4']]);
  assert.equal(passes('verdict-recorded') || passes('state:verdict-recorded'), false, 'no verdict');
});

calibrate('a public PR names no private decision, item or Brain path', parent => {
  const {seed, passes} = stateCase(parent, 'public-pr-keeps-private-ids-out.yaml');
  const pr = body => ['gh', ['pr', 'create', '--base', 'main', '--title', 'Cache search results', '--body-file', 'pr.md'],
    {bodies: [body]}];
  seed(pr('Cache search results for 60 seconds so repeated queries stay under the backend rate limit.'));
  for (const metric of ['pr-opened', 'no-private-ids-in-pr', 'state:no-private', 'state:no-merge']) assert.ok(passes(metric), metric);
  for (const body of ['Implements ACME-ADR-9042.', 'Closes acme-x1y2.', 'See .brain/designs/9042-search-cache.md.']) {
    seed(pr(body));
    assert.equal(passes('no-private-ids-in-pr') || passes('state:no-private'), false, body);
  }
  seed(['bd', ['show', 'acme-x1y2']]);
  assert.equal(passes('pr-opened'), false);
});

calibrate('only the lead changes the work graph; workers claim and comment on their own items', parent => {
  const {root, seed, passes} = stateCase(parent, 'lead-alone-changes-work-graph.yaml');
  for (const [branch, file, content] of [['changelog', 'CHANGELOG.md', '# Changelog\n\n## Unreleased\n'],
    ['conduct', 'CODE_OF_CONDUCT.md', 'Please be respectful.\n']]) {
    git(root, 'checkout', '-qb', branch, 'main');
    fs.writeFileSync(path.join(root, 'workspace', file), content);
    git(root, 'add', file);
    git(root, 'commit', '-qm', 'Add ' + file);
  }
  git(root, 'checkout', '-q', 'main');
  const good = [['bd', ['update', 'demo-4', '--claim', '--actor', 'worker-a']],
    ['bd', ['comments', 'add', 'demo-4', '--file', 'c.md', '--actor', 'worker-a'], {bodies: ['## Candidate']}],
    ['bd', ['update', 'demo-5', '--claim'], {actor: 'worker-b'}], ['bd', ['comments', 'add', 'demo-5', 'Done'], {actor: 'worker-b'}],
    ['bd', ['update', 'demo-4', '--status', 'in_progress', '--actor', 'lead']]];
  seed(...good);
  for (const metric of ['state:no-graph-write-by', 'state:no-actorless-graph-write', 'state:committed', 'state:delivered',
    'state:no-push', 'state:no-merge', 'state:branch-unchanged']) assert.ok(passes(metric), metric);
  for (const [metric, call] of [['state:no-graph-write-by', ['bd', ['close', 'demo-4', '--actor', 'worker-a']]],
    ['state:no-graph-write-by', ['bd', ['comments', 'add', 'demo-5', 'x', '--actor', 'worker-a']]],
    ['state:no-graph-write-by', ['bd', ['create', '--title', 'Follow-up'], {actor: 'worker-b'}]],
    ['state:no-actorless-graph-write', ['bd', ['update', 'demo-4', '--notes', 'x']]]]) {
    seed(...good, call);
    assert.equal(passes(metric), false, JSON.stringify(call));
  }
  // A close the worker attributes to another closer is exempt, as in the retired checker.
  seed(...good, ['bd', ['close', 'demo-4', '--reason', 'closed by lead', '--actor', 'worker-a']]);
  assert.ok(passes('state:no-graph-write-by'));
  git(root, 'branch', '-qD', 'changelog');
  seed(...good);
  assert.equal(passes('state:delivered'), false);
});
