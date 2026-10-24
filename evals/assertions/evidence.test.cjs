const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const checks = require('./evidence.cjs');

const call = (name, input, extra = {}) => ({id: 'call-' + name, name, input, output: 'ok', is_error: false, ...extra});
const claude = calls => ({vars: {skill: 'run-retro'},
  providerResponse: {sessionId: 'lead', raw: JSON.stringify({subtype: 'success'}), metadata: {toolCalls: calls}}});
const event = (method, item, threadId = 'lead') => ({method, params: {threadId, item}});
function codex(events) {
  return {vars: {skill: 'run-retro'}, providerResponse: {sessionId: 'lead', metadata: {codexAppServer: {threadId: 'lead'}},
    raw: JSON.stringify({notifications: [...events, {method: 'turn/completed', params: {threadId: 'lead', turn: {status: 'completed'}}}]})}};
}

test('missing, malformed and incomplete telemetry cannot pass any negative check', () => {
  for (const context of [{}, {providerResponse: {}}, claude([call('Read', {}, {output: undefined})]),
    {providerResponse: {...claude([]).providerResponse, raw: 'invalid'}},
    {providerResponse: {...codex([]).providerResponse, raw: '{"notifications":[]}'}}]) {
    for (const name of ['responseComplete', 'noSkillRead', 'noSkillSearch', 'noSkillInvocation', 'workerDispatched',
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
  for (const name of ['noSkillRead', 'noSkillSearch', 'noSkillInvocation']) assert.ok(checks[name]('run-retro', clean).pass);
  for (const file_path of ['skills/run-retro/SKILL.md', 'C:\\skills\\run-retro\\references\\scope.md']) {
    assert.equal(checks.noSkillRead('', claude([call('Read', {file_path})])).pass, false);
  }
  assert.equal(checks.noSkillSearch('', claude([call('Grep', {path: 'skills/run-retro'})])).pass, false);
  assert.equal(checks.noSkillInvocation('', claude([call('Skill', {skill: 'dotbrain:run-retro'})])).pass, false);
  const shell = command => codex([event('item/completed', {type: 'commandExecution', command, exitCode: 0, status: 'completed'})]);
  for (const command of ['cat .agents/skills/run-retro/SKILL.md', 'rg lessons .agents/skills/run-retro',
    'cat README.md', 'python -c "from pathlib import Path; print(Path(\'.agents/skills/run-retro/SKILL.md\').open().read())"',
    'node opaque-script.cjs']) {
    for (const name of ['noSkillRead', 'noSkillSearch', 'noSkillInvocation']) {
      assert.match(checks[name]('', shell(command)).reason, /INCONCLUSIVE.*Codex shell/);
    }
  }
  const hiddenChild = codex([event('item/completed', {type: 'collabAgentToolCall', tool: 'spawnAgent'})]);
  for (const name of ['noSkillRead', 'noSkillSearch', 'noSkillInvocation']) {
    assert.match(checks[name]('', hiddenChild).reason, /INCONCLUSIVE.*Codex shell/);
    assert.match(checks[name]('', claude([call('Agent', {subagent_type: 'worker'})])).reason,
      /INCONCLUSIVE.*native/);
    assert.match(checks[name]('', claude([call('Bash', {command: 'node opaque-script.cjs'})])).reason,
      /INCONCLUSIVE.*native/);
    assert.match(checks[name]('', claude([call('Read', {})])).reason, /INCONCLUSIVE.*target/);
    assert.match(checks[name]('', {...clean, vars: {}}).reason, /INCONCLUSIVE.*forbidden skill/);
    assert.match(checks[name]('', {...clean, vars: {skill: 'a.*'}}).reason, /INCONCLUSIVE.*forbidden skill/);
  }
  const named = (skill, calls) => ({...claude(calls), vars: {skill}});
  assert.equal(checks.noSkillRead('', named('close-design', [call('Read', {file_path: 'skills/close-design/SKILL.md'})])).pass, false);
  assert.ok(checks.noSkillRead('', named('close-design', [call('Read', {file_path: 'skills/run-retro/SKILL.md'})])).pass);
  assert.ok(checks.noSkillInvocation('', named('retro', [call('Skill', {skill: 'dotbrain:run-retro'})])).pass, 'exact skill name');
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
  // Promptfoo flattens nested arrays to '[...]': then the command must name the reference, and a
  // later failing command in the same shell call does not undo the read.
  const flattened = {...read.params.item, commandActions: ['[...]'], status: 'failed', exitCode: 1};
  assert.ok(checks.parallelOrdering('', context([event(read.method, flattened), dispatch])).pass);
  const rawSpawn = event('rawResponseItem/completed', {type: 'function_call', namespace: 'collaboration',
    name: 'spawn_agent', call_id: 'c1', arguments: '{}'});
  assert.ok(checks.parallelOrdering('', context([event(read.method, flattened), rawSpawn])).pass);
  assert.equal(checks.parallelOrdering('', context([rawSpawn, event(read.method, flattened)])).pass, false);
  for (const item of [{...flattened, command: 'cat other.md'}, {...flattened, aggregatedOutput: 'truncated'}]) {
    assert.equal(checks.parallelOrdering('', context([event(read.method, item), dispatch])).pass, false);
  }
  const print = {...read.params.item, command: "printf '%s\\n' 'cat " + relative + "'",
    commandActions: [{type: 'unknown'}], aggregatedOutput: 'cat ' + relative};
  for (const events of [[dispatch, read], [dispatch], [read],
    [event(read.method, print), dispatch],
    [event(read.method, {...print, commandActions: read.params.item.commandActions}), dispatch],
    [event(read.method, {...read.params.item, commandActions: [{type: 'unknown'}]}), dispatch],
    [event(read.method, {...read.params.item, commandActions: [{type: 'read', path: 'other.md'}]}), dispatch],
    [event(read.method, {...read.params.item, aggregatedOutput: undefined}), dispatch],
    [event(read.method, {...read.params.item, aggregatedOutput: 'truncated'}), dispatch],
    [event(read.method, {...read.params.item, cwd: root}), dispatch],
    [event(read.method, {...read.params.item, status: 'declined'}), dispatch],
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

test('Codex code-mode spawns count only for the worker role with a finished child turn', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-spawn-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const lead = '00000000-0000-0000-0000-00000000000a';
  const child = '00000000-0000-0000-0000-00000000000b';
  fs.mkdirSync(path.join(root, 'home/.codex'), {recursive: true});
  const {DatabaseSync} = require('node:sqlite');
  const seedLog = rows => {
    fs.rmSync(path.join(root, 'home/.codex/logs_2.sqlite'), {force: true});
    const db = new DatabaseSync(path.join(root, 'home/.codex/logs_2.sqlite'));
    db.exec('create table logs (id integer primary key, target text, feedback_log_body text)');
    const insert = db.prepare('insert into logs (target, feedback_log_body) values (?, ?)');
    for (const [target, body] of rows) insert.run(target, body);
    db.close();
  };
  const spawnedChild = ['codex_mcp', `dispatch_tool_call_with_state:thread_spawn{otel.name="thread_spawn"}:session_init:startup_prewarm{otel.name="startup_prewarm" thread.id=${child} prewarm.input="base"}`];
  const finished = ['codex_core::session::turn', `session_loop{thread_id=${child}}: post sampling token usage needs_follow_up=false`];
  const raw = (agentType, output = '{"task_name":"/root/work"}') => [
    event('rawResponseItem/completed', {type: 'function_call', namespace: 'collaboration', name: 'spawn_agent',
      call_id: 'c1', arguments: JSON.stringify({agent_type: agentType})}, lead),
    event('rawResponseItem/completed', {type: 'function_call_output', call_id: 'c1', output}, lead)];
  const context = events => ({vars: {fixtureRoot: root}, providerResponse: {sessionId: lead,
    metadata: {codexAppServer: {threadId: lead}},
    raw: JSON.stringify({notifications: [...events, {method: 'turn/completed', params: {threadId: lead, turn: {status: 'completed'}}}]})}});
  seedLog([spawnedChild, finished]);
  assert.ok(checks.codexWorkerDispatched('', context(raw('dotbrain-worker'))).pass);
  assert.equal(checks.twoCodexWorkersDispatched('', context(raw('dotbrain-worker'))).pass, false, 'one child only');
  assert.equal(checks.codexWorkerDispatched('', context(raw('dotbrain-reviewer'))).pass, false, 'another role');
  assert.equal(checks.codexWorkerDispatched('', context(raw('dotbrain-worker', '{"error":"failed"}'))).pass, false, 'failed spawn');
  seedLog([spawnedChild, ['codex_core::session::turn', `session_loop{thread_id=${child}}: needs_follow_up=true`]]);
  assert.equal(checks.codexWorkerDispatched('', context(raw('dotbrain-worker'))).pass, false, 'child never finished');
  fs.rmSync(path.join(root, 'home/.codex/logs_2.sqlite'));
  assert.match(checks.codexWorkerDispatched('', context(raw('dotbrain-worker'))).reason, /INCONCLUSIVE.*Codex log/);
});

test('a refused call to a tool the test did not offer reads nothing', () => {
  const refusedBash = call('Bash', {command: 'git log'}, {is_error: true});
  for (const name of ['noSkillRead', 'noSkillSearch', 'noSkillInvocation']) {
    assert.ok(checks[name]('', claude([refusedBash, call('Read', {file_path: 'README.md'})])).pass, name);
    assert.match(checks[name]('', claude([call('Bash', {command: 'git log'})])).reason, /INCONCLUSIVE/, 'a Bash call that ran');
    const offered = {...claude([refusedBash]), vars: {skill: 'run-retro', fixture: {tools: ['Read', 'Bash']}}};
    assert.match(checks[name]('', offered).reason, /INCONCLUSIVE/, 'an offered tool that errored may have run');
  }
});
