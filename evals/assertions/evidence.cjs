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

function mentionsRetro(input) { return /(?:^|[\\/\s:"'])run-retro(?:[\\/\s:"']|$)/i.test(input); }
function requireNegativeEvidence(trace) {
  if (trace.runtime === 'codex') {
    throw new Error('INCONCLUSIVE: Codex shell events cannot establish absence of skill reads, searches or invocation');
  }
  if (trace.calls.some(call => !['Read', 'Grep', 'Glob', 'Skill'].includes(call.name))) {
    throw new Error('INCONCLUSIVE: explicit-only checks require the configured native read/search/skill tools');
  }
  if (trace.calls.some(call => call.name === 'Read' &&
    typeof (call.input.file_path || call.input.path) !== 'string' ||
    call.name === 'Skill' && typeof call.input.skill !== 'string')) {
    throw new Error('INCONCLUSIVE: missing native read/skill target');
  }
}

function noRetroRead(output, context) {
  return check(context, trace => {
    requireNegativeEvidence(trace);
    return !trace.calls.some(call => call.name === 'Read' &&
      mentionsRetro(call.input.file_path || call.input.path || ''));
  }, 'run-retro skill/reference reads are forbidden');
}

function noRetroSearch(output, context) {
  return check(context, trace => {
    requireNegativeEvidence(trace);
    return !trace.calls.some(call => ['Grep', 'Glob'].includes(call.name) &&
      mentionsRetro(call.input.path || ''));
  },
  'Searching the run-retro path is forbidden');
}

function noRetroInvocation(output, context) {
  return check(context, trace => {
    requireNegativeEvidence(trace);
    return !trace.calls.some(call => call.name === 'Skill' && /(?:^|:)run-retro$/.test(call.input?.skill || ''));
  },
  'Invoking run-retro is forbidden; built-in not-skill-used checks inferred uses too');
}

function workers(trace) {
  if (trace.runtime === 'claude') return trace.calls.filter(call =>
    call.name === 'Agent' && call.input?.subagent_type === 'dotbrain:worker' && !call.is_error &&
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

function completedCodexWorkers(trace) {
  if (trace.runtime !== 'codex') throw new Error('INCONCLUSIVE: Codex lead events required');
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
  return check(context, trace => completedCodexWorkers(trace) >= 1,
    'One observable Codex agent spawn and completion required; packaged role/child tools are SKIPPED_UNSUPPORTED');
}

function twoCodexWorkersDispatched(output, context) {
  return check(context, trace => completedCodexWorkers(trace) >= 2,
    'Two distinct observable Codex agent spawns and completions required; packaged roles/child tools are SKIPPED_UNSUPPORTED');
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
    const firstDispatch = events.findIndex(event => event.method === 'item/started' &&
      event.params?.threadId === trace.lead && event.params?.item?.type === 'collabAgentToolCall' &&
      event.params.item.tool === 'spawnAgent');
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
        item?.type !== 'commandExecution' || item.status !== 'completed' || item.exitCode !== 0) return false;
      if (!Array.isArray(item.commandActions) || typeof item.cwd !== 'string' ||
        typeof item.aggregatedOutput !== 'string') {
        throw new Error('INCONCLUSIVE: native read actions, cwd and complete output required');
      }
      return item.commandActions.some(action => {
        if (action.type !== 'read' || typeof action.path !== 'string') return false;
        try { return fs.realpathSync(path.resolve(item.cwd, action.path)) === target; }
        catch { return false; }
      }) && normalize(item.aggregatedOutput).includes(contents);
    });
    if (!readBeforeDispatch) throw new Error('INCONCLUSIVE: no corroborated native reference read before dispatch');
    return true;
  }, 'A successful lead reference read must complete before the first writing dispatch; Codex requires a native read action and matching reference output');
}

module.exports = {evidence, responseComplete, noRetroRead, noRetroSearch, noRetroInvocation,
  workerDispatched, twoWorkersDispatched, codexWorkerDispatched, twoCodexWorkersDispatched, parallelOrdering};
