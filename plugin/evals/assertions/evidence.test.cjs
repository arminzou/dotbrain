const {test} = require('node:test');
const assert = require('node:assert/strict');
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
    for (const name of ['responseComplete', 'noRetroRead', 'noRetroSearch', 'noRetroInvocation', 'workerDispatched', 'parallelOrdering']) {
      assert.equal(checks[name]('answer', context).pass, false, name);
    }
  }
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
  assert.equal(checks.noRetroRead('', shell('cat .agents/skills/run-retro/SKILL.md')).pass, false);
  assert.equal(checks.noRetroSearch('', shell('rg lessons .agents/skills/run-retro')).pass, false);
  assert.ok(checks.noRetroRead('', shell('cat README.md')).pass);
  const hiddenChild = codex([event('item/completed', {type: 'collabAgentToolCall', tool: 'spawnAgent'})]);
  for (const name of ['noRetroRead', 'noRetroSearch', 'noRetroInvocation']) {
    assert.match(checks[name]('', hiddenChild).reason, /INCONCLUSIVE.*child activity/);
    assert.match(checks[name]('', claude([call('Agent', {subagent_type: 'worker'})])).reason,
      /INCONCLUSIVE.*child activity/);
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

test('completion order rejects child reads, failed reads and reads after dispatch', () => {
  const read = event('item/completed', {type: 'commandExecution', command: 'cat .agents/skills/run-execution/references/parallel-execution.md', exitCode: 0, status: 'completed'});
  const dispatch = event('item/started', {type: 'collabAgentToolCall', tool: 'spawnAgent'});
  assert.ok(checks.parallelOrdering('', codex([read, dispatch])).pass);
  for (const events of [[dispatch, read], [dispatch], [read],
    [event(read.method, {...read.params.item, exitCode: 1}), dispatch],
    [event(read.method, read.params.item, 'child'), dispatch],
    [event('item/started', read.params.item), dispatch]]) {
    assert.equal(checks.parallelOrdering('', codex(events)).pass, false);
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
