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
      !call.id || !call.name || typeof call.input !== 'object' || call.output === undefined)) {
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
function command(call) { return call.command || call.input?.command || ''; }
function requireVisibleChildren(trace) {
  if (trace.runtime === 'claude' && trace.calls.some(call => call.name === 'Agent' &&
    !trace.calls.some(child => child.parentToolUseId === call.id))) {
    throw new Error('INCONCLUSIVE: Claude child activity is absent from the provider evidence');
  }
  if (trace.runtime === 'codex' && trace.notifications.some(event =>
    event.params?.item?.type === 'collabAgentToolCall' && event.params.item.tool === 'spawnAgent')) {
    throw new Error('INCONCLUSIVE: Codex child activity is absent from the provider evidence');
  }
}

function noRetroRead(output, context) {
  return check(context, trace => {
    requireVisibleChildren(trace);
    return !trace.calls.some(call => {
    const input = call.input || {};
    return (call.name === 'Read' && mentionsRetro(input.file_path || input.path || '')) ||
      (mentionsRetro(command(call)) && /\b(cat|type|head|tail|sed|awk|Get-Content|readFile|read_text)\b/i.test(command(call)));
    });
  }, 'run-retro skill/reference reads are forbidden');
}

function noRetroSearch(output, context) {
  return check(context, trace => {
    requireVisibleChildren(trace);
    return !trace.calls.some(call =>
    (['Grep', 'Glob'].includes(call.name) && mentionsRetro(call.input?.path || '')) ||
    (mentionsRetro(command(call)) && /\b(rg|grep|find|Get-ChildItem|Select-String)\b/i.test(command(call))));
  },
  'Searching the run-retro path is forbidden');
}

function noRetroInvocation(output, context) {
  return check(context, trace => {
    requireVisibleChildren(trace);
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
    return firstDispatch > 0 && events.slice(0, firstDispatch).some(event => {
      const item = event.params?.item;
      return event.method === 'item/completed' && event.params?.threadId === trace.lead &&
        item?.type === 'commandExecution' && item.status === 'completed' && item.exitCode === 0 &&
        /run-execution[\\/]+references[\\/]+parallel-execution\.md/.test(item.command || '') &&
        /\b(cat|type|Get-Content|readFile|read_text)\b/i.test(item.command || '');
    });
  }, 'A successful lead reference read must complete before the first writing dispatch');
}

module.exports = {evidence, responseComplete, noRetroRead, noRetroSearch, noRetroInvocation,
  workerDispatched, twoWorkersDispatched, parallelOrdering};
