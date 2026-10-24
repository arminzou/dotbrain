const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const checks = require('./evidence.cjs');

const call = (name, input, extra = {}) => ({id: 'call-' + name, name, input, output: 'ok', is_error: false, ...extra});
const claude = calls => ({providerResponse: {sessionId: 'lead', raw: JSON.stringify({subtype: 'success'}), metadata: {toolCalls: calls}}});
const event = (method, item, threadId = 'lead') => ({method, params: {threadId, item}});
function codex(events) {
  return {providerResponse: {sessionId: 'lead', metadata: {codexAppServer: {threadId: 'lead'}},
    raw: JSON.stringify({notifications: [...events, {method: 'turn/completed', params: {threadId: 'lead', turn: {status: 'completed'}}}]})}};
}

test('missing, malformed and incomplete telemetry cannot pass any negative check', () => {
  for (const context of [{}, {providerResponse: {}}, claude([call('Read', {}, {output: undefined})]),
    {providerResponse: {...claude([]).providerResponse, raw: 'invalid'}},
    {providerResponse: {...codex([]).providerResponse, raw: '{"notifications":[]}'}}]) {
    for (const name of ['responseComplete', 'noRetroRead', 'noRetroSearch', 'noRetroInvocation', 'workerDispatched',
      'codexWorkerDispatched', 'twoCodexWorkersDispatched', 'parallelOrdering']) {
      assert.equal(checks[name]('answer', context).pass, false, name);
    }
  }
});

test('Codex counts distinct successful lead spawns with observed completion, without claiming roles', () => {
  const spawn = (id, extra = {}) => event('item/completed', {id: 'spawn-' + id,
    type: 'collabAgentToolCall', tool: 'spawnAgent', status: 'completed', senderThreadId: 'lead',
    receiverThreadIds: [id], agentsStates: {[id]: {status: 'running'}}, ...extra});
  const wait = (...ids) => event('item/completed', {id: 'wait', type: 'collabAgentToolCall',
    tool: 'wait', status: 'completed', senderThreadId: 'lead', receiverThreadIds: ids,
    agentsStates: Object.fromEntries(ids.map(id => [id, {status: 'completed'}]))});
  assert.ok(checks.codexWorkerDispatched('', codex([spawn('one'), wait('one')])).pass);
  assert.ok(checks.twoCodexWorkersDispatched('', codex([spawn('one'), spawn('two'), wait('one', 'two')])).pass);
  assert.equal(checks.twoCodexWorkersDispatched('', codex([spawn('one'), spawn('one'), wait('one')])).pass, false);
  assert.equal(checks.twoCodexWorkersDispatched('', codex([spawn('one'), spawn('two', {id: 'spawn-one'}), wait('one', 'two')])).pass, false);
  assert.equal(checks.twoCodexWorkersDispatched('', codex([spawn('one'), spawn('two'), wait('one')])).pass, false);
  for (const events of [[], [wait('one')], [spawn('one')], [wait('one'), spawn('one')],
    [spawn('one'), wait('other')], [spawn('one', {status: 'failed'}), wait('one')],
    [spawn('one', {senderThreadId: 'child'}), wait('one')],
    [event('item/completed', spawn('one').params.item, 'child'), wait('one')],
    [spawn('one', {receiverThreadIds: []}), wait('one')],
    [spawn('one', {id: ''}), wait('one')],
    [spawn('lead'), wait('lead')], [spawn('one'), {...wait('one'), method: 'item/started'}],
    [spawn('one'), event('item/completed', {...wait('one').params.item, receiverThreadIds: 'one'})],
    [spawn('one'), event('item/completed', {...wait('one').params.item, agentsStates: {one: {status: 'errored'}}})],
    [spawn('one'), event('item/completed', {...wait('one').params.item, status: 'failed'})]]) {
    assert.equal(checks.codexWorkerDispatched('', codex(events)).pass, false, JSON.stringify(events));
  }
  assert.match(checks.codexWorkerDispatched('', claude([])).reason, /INCONCLUSIVE/);
});

test('separate explicit-only boundaries reject reads, searches and invocation', () => {
  const clean = claude([call('Read', {file_path: 'src/main.py'})]);
  for (const name of ['noRetroRead', 'noRetroSearch', 'noRetroInvocation']) assert.ok(checks[name]('run-retro', clean).pass);
  for (const file_path of ['skills/run-retro/SKILL.md', 'C:\\skills\\run-retro\\references\\scope.md']) {
    assert.equal(checks.noRetroRead('', claude([call('Read', {file_path})])).pass, false);
  }
  assert.equal(checks.noRetroSearch('', claude([call('Grep', {path: 'skills/run-retro'})])).pass, false);
  assert.equal(checks.noRetroInvocation('', claude([call('Skill', {skill: 'dotbrain:run-retro'})])).pass, false);
  const shell = command => codex([event('item/completed', {type: 'commandExecution', command, exitCode: 0, status: 'completed'})]);
  for (const command of ['cat .agents/skills/run-retro/SKILL.md', 'rg lessons .agents/skills/run-retro',
    'cat README.md', 'python -c "from pathlib import Path; print(Path(\'.agents/skills/run-retro/SKILL.md\').open().read())"',
    'node opaque-script.cjs']) {
    for (const name of ['noRetroRead', 'noRetroSearch', 'noRetroInvocation']) {
      assert.match(checks[name]('', shell(command)).reason, /INCONCLUSIVE.*Codex shell/);
    }
  }
  const hiddenChild = codex([event('item/completed', {type: 'collabAgentToolCall', tool: 'spawnAgent'})]);
  for (const name of ['noRetroRead', 'noRetroSearch', 'noRetroInvocation']) {
    assert.match(checks[name]('', hiddenChild).reason, /INCONCLUSIVE.*Codex shell/);
    assert.match(checks[name]('', claude([call('Agent', {subagent_type: 'worker'})])).reason,
      /INCONCLUSIVE.*native/);
    assert.match(checks[name]('', claude([call('Bash', {command: 'node opaque-script.cjs'})])).reason,
      /INCONCLUSIVE.*native/);
    assert.match(checks[name]('', claude([call('Read', {})])).reason, /INCONCLUSIVE.*target/);
  }
});

test('packaged-role dispatch requires a successful named invocation and child activity', () => {
  const worker = call('Agent', {subagent_type: 'dotbrain:worker'}, {id: 'dispatch'});
  const child = call('Bash', {command: 'git status'}, {parentToolUseId: 'dispatch'});
  assert.ok(checks.workerDispatched('', claude([worker, child])).pass);
  for (const calls of [[worker], [child], [{...worker, is_error: true}, child],
    [{...worker, input: {subagent_type: 'worker'}}, child],
    [worker, {...child, parentToolUseId: 'other'}]]) {
    assert.equal(checks.workerDispatched('', claude(calls)).pass, false);
  }
  assert.equal(checks.twoWorkersDispatched('', claude([worker, child])).pass, false);
  const second = {...worker, id: 'second'};
  assert.ok(checks.twoWorkersDispatched('', claude([worker, child, second, {...child, parentToolUseId: 'second'}])).pass);
  assert.match(checks.workerDispatched('', codex([])).reason, /INCONCLUSIVE.*child-thread/);
});

test('completion order requires a native reference read with corroborating output before dispatch', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'order-evidence-'));
  t.after(() => {
    assert.ok(fs.realpathSync(root).startsWith(fs.realpathSync(os.tmpdir()) + path.sep));
    fs.rmSync(root, {recursive: true, force: true});
  });
  const relative = '.agents/skills/run-execution/references/parallel-execution.md';
  const cwd = path.join(root, 'workspace');
  const reference = path.join(cwd, relative);
  fs.mkdirSync(path.dirname(reference), {recursive: true});
  const contents = 'Full synthetic parallel reference\n';
  fs.writeFileSync(reference, contents);
  fs.writeFileSync(path.join(cwd, 'other.md'), contents);
  const context = events => ({...codex(events), vars: {fixtureRoot: root}});
  const read = event('item/completed', {type: 'commandExecution', command: 'cat ' + relative,
    commandActions: [{type: 'read', path: relative}], cwd, aggregatedOutput: contents, exitCode: 0, status: 'completed'});
  const dispatch = event('item/started', {type: 'collabAgentToolCall', tool: 'spawnAgent'});
  assert.ok(checks.parallelOrdering('', context([read, dispatch])).pass);
  const print = {...read.params.item, command: "printf '%s\\n' 'cat " + relative + "'",
    commandActions: [{type: 'unknown'}], aggregatedOutput: 'cat ' + relative};
  for (const events of [[dispatch, read], [dispatch], [read],
    [event(read.method, print), dispatch],
    [event(read.method, {...print, commandActions: read.params.item.commandActions}), dispatch],
    [event(read.method, {...read.params.item, commandActions: [{type: 'unknown'}]}), dispatch],
    [event(read.method, {...read.params.item, commandActions: [{type: 'read', path: 'other.md'}]}), dispatch],
    [event(read.method, {...read.params.item, commandActions: undefined}), dispatch],
    [event(read.method, {...read.params.item, aggregatedOutput: undefined}), dispatch],
    [event(read.method, {...read.params.item, aggregatedOutput: 'truncated'}), dispatch],
    [event(read.method, {...read.params.item, cwd: root}), dispatch],
    [event(read.method, {...read.params.item, exitCode: 1}), dispatch],
    [event(read.method, read.params.item, 'child'), dispatch],
    [event('item/started', read.params.item), dispatch]]) {
    assert.equal(checks.parallelOrdering('', context(events)).pass, false, JSON.stringify(events));
  }
  assert.match(checks.parallelOrdering('', claude([])).reason, /INCONCLUSIVE.*completion order/);
});

test('Claude completion spans link the successful lead read to dispatch timing', () => {
  const read = call('Read', {file_path: 'skills/run-execution/references/parallel-execution.md'});
  const dispatch = call('Agent', {subagent_type: 'dotbrain:worker'});
  const context = claude([read, dispatch]);
  const span = (id, startTime, endTime, attributes = {}) => ({startTime, endTime,
    attributes: {'gen_ai.tool.call.id': id, 'tool.is_error': false, ...attributes}});
  context.trace = {spans: [span(read.id, 1, 3), span(dispatch.id, 4, 10)]};
  assert.ok(checks.parallelOrdering('', context).pass);
  for (const readSpan of [span(read.id, 1, 5), span('other-id', 1, 3),
    span(read.id, 1, 3, {'tool.incomplete': true}), span(read.id, 1, 3, {'tool.is_error': true})]) {
    context.trace.spans[0] = readSpan;
    assert.equal(checks.parallelOrdering('', context).pass, false);
  }
  context.trace.spans[0] = span(read.id, 1, 3);
  read.parentToolUseId = 'child';
  assert.equal(checks.parallelOrdering('', context).pass, false);
});
