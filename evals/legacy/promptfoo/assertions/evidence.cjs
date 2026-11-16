const fs = require('node:fs');
const path = require('node:path');

function verdict(pass, reason) { return {pass, score: pass ? 1 : 0, reason}; }

function evidence(context) {
  const response = context.providerResponse;
  if (!response || response.error || !response.sessionId || response.sessionId === 'unknown') {
    throw new Error('INCONCLUSIVE: missing successful provider response/session');
  }
  const metadata = response.metadata;
  if (Array.isArray(metadata?.toolCalls)) {
    const terminal = JSON.parse(response.raw);
    if (terminal.subtype !== 'success' || metadata.toolCalls.some(call =>
      !call.id || !call.name || !call.input || typeof call.input !== 'object' ||
      Array.isArray(call.input) || call.output === undefined)) {
      throw new Error('INCONCLUSIVE: incomplete Claude tool/terminal evidence');
    }
    return {runtime: 'claude', response, calls: metadata.toolCalls};
  }
  const raw = JSON.parse(response.raw);
  const notifications = raw.notifications;
  const lead = metadata?.codexAppServer?.threadId;
  if (!lead || !Array.isArray(notifications) || !notifications.some(event =>
    event.method === 'turn/completed' && event.params?.threadId === lead &&
    event.params?.turn?.status === 'completed' && !event.params.turn.error)) {
    throw new Error('INCONCLUSIVE: Codex raw events and completed lead turn required');
  }
  return {runtime: 'codex', response, notifications, lead,
    calls: notifications.filter(event => event.method === 'item/completed').map(event => ({
      ...event.params.item, threadId: event.params.threadId,
    }))};
}

function check(context, predicate, reason) {
  try { return verdict(predicate(evidence(context)), reason); }
  catch (error) { return verdict(false, error.message); }
}

function responseComplete(output, context) {
  return check(context, () => typeof output === 'string' && output.trim().length > 0,
    'Successful terminal response and observable tool records required');
}

// The forbidden skill comes from the test's `skill` var.
function forbiddenSkill(context) {
  const skill = context.vars?.skill;
  if (!/^[a-z0-9-]+$/.test(skill || '')) throw new Error('INCONCLUSIVE: test must name the forbidden skill');
  return skill;
}
function mentions(skill, input) {
  return new RegExp(`(?:^|[\\\\/\\s:"'])${skill}(?:[\\\\/\\s:"']|$)`, 'i').test(input);
}
function requireNegativeEvidence(trace, context) {
  if (trace.runtime === 'codex') {
    throw new Error('INCONCLUSIVE: Codex shell events cannot establish absence of skill reads, searches or invocation');
  }
  // A call to a tool the test did not offer is refused before it runs, so it reads nothing.
  const offered = context.vars?.fixture?.tools ?? ['Read', 'Grep', 'Glob', 'Skill'];
  const refused = call => call.is_error === true && !offered.includes(call.name);
  if (trace.calls.some(call => !['Read', 'Grep', 'Glob', 'Skill'].includes(call.name) && !refused(call))) {
    throw new Error('INCONCLUSIVE: explicit-only checks require the configured native read/search/skill tools');
  }
  if (trace.calls.some(call => call.name === 'Read' &&
    typeof (call.input.file_path || call.input.path) !== 'string' ||
    call.name === 'Skill' && typeof call.input.skill !== 'string')) {
    throw new Error('INCONCLUSIVE: missing native read/skill target');
  }
}

function noSkillRead(output, context) {
  return check(context, trace => {
    const skill = forbiddenSkill(context);
    requireNegativeEvidence(trace, context);
    return !trace.calls.some(call => call.name === 'Read' &&
      mentions(skill, call.input.file_path || call.input.path || ''));
  }, 'Reading the forbidden skill or its references is forbidden');
}

function noSkillSearch(output, context) {
  return check(context, trace => {
    const skill = forbiddenSkill(context);
    requireNegativeEvidence(trace, context);
    return !trace.calls.some(call => ['Grep', 'Glob'].includes(call.name) &&
      mentions(skill, call.input.path || ''));
  },
  'Searching the forbidden skill path is forbidden');
}

function noSkillInvocation(output, context) {
  return check(context, trace => {
    const skill = forbiddenSkill(context);
    requireNegativeEvidence(trace, context);
    return !trace.calls.some(call => call.name === 'Skill' &&
      (call.input?.skill || '').split(':').pop() === skill);
  },
  'Invoking the forbidden skill is forbidden; built-in not-skill-used checks inferred uses too');
}

// The lead dispatched no agent: no Claude `Agent` call, no Codex spawn event, attempted or completed.
function noDispatch(output, context) {
  return check(context, trace => trace.runtime === 'claude'
    ? !trace.calls.some(call => ['Agent', 'Task'].includes(call.name))
    : !trace.notifications.some(event => event.params?.item?.type === 'collabAgentToolCall' &&
      event.params.item.tool === 'spawnAgent'),
  'Dispatching an agent is forbidden in this exercise');
}

function workers(trace) {
  if (trace.runtime === 'claude') return trace.calls.filter(call =>
    call.name === 'Agent' && call.input?.subagent_type === 'dotbrain-worker' && !call.is_error &&
    !call.parentToolUseId && trace.calls.some(child => child.parentToolUseId === call.id));
  throw new Error('INCONCLUSIVE: Promptfoo 0.125.0 app-server drops child-thread events; named role and child activity are unqualified');
}

function workerDispatched(output, context) {
  return check(context, trace => workers(trace).length >= 1,
    'A successful packaged named worker dispatch with linked child activity is required');
}

function twoWorkersDispatched(output, context) {
  return check(context, trace => workers(trace).length >= 2,
    'Two successful packaged named worker dispatches with linked child activity are required');
}

// Codex code mode spawns through raw `collaboration` function calls instead of collab items. A
// spawn counts when the lead asked for the packaged worker role and Codex answered with a task;
// the child's finished turn comes from the fixture-owned Codex log, since the stream omits it.
function rawCodexSpawns(trace) {
  const outputs = new Map();
  const spawns = new Map();
  for (const event of trace.notifications) {
    const item = event.params?.item;
    if (event.method !== 'rawResponseItem/completed' || event.params?.threadId !== trace.lead || !item) continue;
    if (item.type === 'function_call' && item.namespace === 'collaboration' && item.name === 'spawn_agent') {
      spawns.set(item.call_id, item);
    } else if (item.type === 'function_call_output') outputs.set(item.call_id, item.output);
  }
  return [...spawns.values()].filter(item => {
    try { return JSON.parse(item.arguments).agent_type === 'dotbrain-worker' && JSON.parse(outputs.get(item.call_id)).task_name; }
    catch { return false; }
  });
}

function finishedCodexChildren(context, lead) {
  const home = path.join(context.vars?.fixtureRoot || '', 'home/.codex');
  const log = fs.existsSync(home) && fs.readdirSync(home).find(file => /^logs_\d+\.sqlite$/.test(file));
  if (!log) throw new Error('INCONCLUSIVE: fixture Codex log required for child completion');
  const {DatabaseSync} = require('node:sqlite');
  const db = new DatabaseSync(path.join(home, log), {readOnly: true});
  try {
    const bodies = db.prepare('select target, feedback_log_body as body from logs').all();
    const children = new Set(bodies.flatMap(({body}) =>
      [...body.matchAll(/thread_spawn\{[^}]*\}:session_init:startup_prewarm\{[^}]*thread\.id=([0-9a-f-]{36})/g)].map(match => match[1])));
    children.delete(lead);
    return [...children].filter(child => bodies.some(({target, body}) =>
      target === 'codex_core::session::turn' && body.includes(child) && body.includes('needs_follow_up=false')));
  } finally { db.close(); }
}

function completedCodexWorkers(trace, context) {
  if (trace.runtime !== 'codex') throw new Error('INCONCLUSIVE: Codex lead events required');
  const raw = rawCodexSpawns(trace);
  if (raw.length) return Math.min(raw.length, finishedCodexChildren(context, trace.lead).length);
  const completed = new Set();
  const spawned = new Set();
  const dispatches = new Set();
  for (const item of trace.calls) {
    if (item.threadId !== trace.lead || item.type !== 'collabAgentToolCall' ||
      item.senderThreadId !== trace.lead || item.status !== 'completed') continue;
    if (!item.id || !Array.isArray(item.receiverThreadIds) ||
      item.receiverThreadIds.some(id => typeof id !== 'string' || !id || id === trace.lead)) {
      throw new Error('INCONCLUSIVE: missing successful Codex dispatch identity');
    }
    if (item.tool === 'spawnAgent') {
      if (item.receiverThreadIds.length !== 1) {
        throw new Error('INCONCLUSIVE: missing successful Codex spawn identity');
      }
      if (dispatches.has(item.id)) continue;
      dispatches.add(item.id);
      spawned.add(item.receiverThreadIds[0]);
    }
    for (const id of spawned) {
      if (item.receiverThreadIds?.includes(id) && item.agentsStates?.[id]?.status === 'completed') {
        completed.add(id);
      }
    }
  }
  return completed.size;
}

function codexWorkerDispatched(output, context) {
  return check(context, trace => completedCodexWorkers(trace, context) >= 1,
    'One observable Codex dotbrain-worker spawn and completion required; child tool activity is SKIPPED_UNSUPPORTED');
}

function twoCodexWorkersDispatched(output, context) {
  return check(context, trace => completedCodexWorkers(trace, context) >= 2,
    'Two distinct observable Codex dotbrain-worker spawns and completions required; child tool activity is SKIPPED_UNSUPPORTED');
}

function parallelOrdering(output, context) {
  return check(context, trace => {
    if (trace.runtime === 'claude') {
      const spans = context.trace?.spans;
      if (!Array.isArray(spans)) throw new Error('INCONCLUSIVE: Claude completion order requires trace spans');
      const spanFor = call => spans.find(span => span.attributes?.['gen_ai.tool.call.id'] === call.id);
      const dispatches = trace.calls.filter(call => call.name === 'Agent' && !call.parentToolUseId &&
        /worker/.test(call.input?.subagent_type || '')).map(spanFor);
      if (!dispatches.length || dispatches.some(span => !Number.isFinite(span?.startTime))) return false;
      const firstStart = Math.min(...dispatches.map(span => span.startTime));
      return trace.calls.some(call => {
        const span = spanFor(call);
        return call.name === 'Read' && !call.parentToolUseId && !call.is_error &&
          /run-execution[\\/]+references[\\/]+parallel-execution\.md/.test(call.input?.file_path || '') &&
          Number.isFinite(span?.endTime) && span.endTime < firstStart &&
          span.attributes?.['tool.is_error'] === false && !span.attributes['tool.incomplete'];
      });
    }
    const events = trace.notifications;
    const firstDispatch = events.findIndex(event => event.params?.threadId === trace.lead && (
      event.method === 'item/started' && event.params?.item?.type === 'collabAgentToolCall' &&
        event.params.item.tool === 'spawnAgent' ||
      event.method === 'rawResponseItem/completed' && event.params?.item?.type === 'function_call' &&
        event.params.item.namespace === 'collaboration' && event.params.item.name === 'spawn_agent'));
    const root = context.vars?.fixtureRoot;
    if (!root) throw new Error('INCONCLUSIVE: staged reference path required');
    const reference = path.join(root, 'workspace/.agents/skills/run-execution/references/parallel-execution.md');
    const target = fs.realpathSync(reference);
    const normalize = text => text.replaceAll('\r\n', '\n').trim();
    const contents = normalize(fs.readFileSync(reference, 'utf8'));
    if (!contents) throw new Error('INCONCLUSIVE: staged reference is empty');
    const readBeforeDispatch = firstDispatch > 0 && events.slice(0, firstDispatch).some(event => {
      const item = event.params?.item;
      if (event.method !== 'item/completed' || event.params?.threadId !== trace.lead ||
        item?.type !== 'commandExecution' || !['completed', 'failed'].includes(item.status)) return false;
      if (typeof item.cwd !== 'string' || typeof item.aggregatedOutput !== 'string') {
        throw new Error('INCONCLUSIVE: command cwd and complete output required');
      }
      // Native read actions where Promptfoo keeps them; it flattens nested arrays to '[...]', so
      // otherwise the command must name the reference. Either way the output must carry its full
      // contents, which a later failing command in the same shell call does not undo.
      const actions = Array.isArray(item.commandActions) ? item.commandActions.filter(action => typeof action === 'object') : [];
      const named = actions.length ? actions.some(action => {
        if (action.type !== 'read' || typeof action.path !== 'string') return false;
        try { return fs.realpathSync(path.resolve(item.cwd, action.path)) === target; }
        catch { return false; }
      }) : /run-execution[\\/]+references[\\/]+parallel-execution\.md/.test(item.command || '');
      return named && normalize(item.aggregatedOutput).includes(contents);
    });
    if (!readBeforeDispatch) throw new Error('INCONCLUSIVE: no corroborated native reference read before dispatch');
    return true;
  }, 'A successful lead reference read must complete before the first writing dispatch; Codex requires a native read action and matching reference output');
}

module.exports = {evidence, responseComplete, noDispatch, noSkillRead, noSkillSearch, noSkillInvocation,
  workerDispatched, twoWorkersDispatched, codexWorkerDispatched, twoCodexWorkersDispatched, parallelOrdering};
