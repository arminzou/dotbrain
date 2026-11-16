const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {evidence} = require('./evidence.cjs');
const {positionals} = require('../fixtures/stub.cjs');
const {git} = require('../fixtures/workspace.cjs');

function continuation(output, context) {
  try {
    const second = evidence(context);
    const journey = context.providerResponse.metadata?.continuation;
    if (!journey) throw new Error('INCONCLUSIVE: two-session provider evidence missing');
    const first = evidence({providerResponse: journey.first.response});
    assert.equal(first.runtime, second.runtime, 'Runtime changed between sessions');
    assert.notEqual(first.response.sessionId, second.response.sessionId, 'Session was resumed');
    for (const input of [journey.first.input, journey.secondInput]) {
      assert.ok(typeof input.prompt === 'string' && input.prompt.length, 'Missing session input');
      assert.deepEqual(input.fresh, first.runtime === 'claude' ? {persist_session: false}
        : {persist_threads: false, reuse_server: false}, 'Session persistence enabled');
    }
    assert.ok(!journey.secondInput.prompt.includes(first.response.output), 'First transcript leaked');
    assert.ok(!JSON.stringify(journey.secondInput).includes(first.response.sessionId), 'First session ID leaked');
    assert.equal(journey.secondInput.prompt.trimEnd(), context.vars.request.trimEnd(), 'Second task includes unexpected context');
    const root = context.vars.fixtureRoot;
    const source = fs.readFileSync(path.join(root, 'workspace/config/retry.json'));
    const expected = {
      discovery: {setting: 'retryLimit', value: 3, evidence: {path: 'config/retry.json',
        sha256: crypto.createHash('sha256').update(source).digest('hex')}},
      hypothesis: {claim: 'Fixed backoff may explain the timeout', status: 'unresolved'},
      nextWork: 'demo-next', requiresApproval: true,
    };
    const file = 'workspace/.brain/docs/investigation.json';
    for (const stage of [journey.before, journey.after]) {
      assert.deepEqual(JSON.parse(stage[file]), expected, 'Durable discovery, evidence, hypothesis or next work lost');
      const items = JSON.parse(stage['items.json']);
      const next = items.find(item => item.id === expected.nextWork);
      assert.equal(next?.status, 'open', 'Next investigation is not ready');
      assert.ok(next.comments.some(comment => comment.author &&
        comment.text.includes('docs/investigation.json') && comment.text.includes('config/retry.json')),
      'No durable Beads handoff with discovery evidence');
      assert.equal(items.find(item => item.id === 'demo-blocked')?.status, 'blocked', 'Approval gate changed');
    }
    const report = JSON.parse(fs.readFileSync(path.join(root, 'workspace/.brain/docs/continuation-check.json'), 'utf8'));
    assert.deepEqual(report, expected, 'Recovered discovery, hypothesis, next work or approval gate is wrong');
    assert.equal(fs.readFileSync(path.join(root, file), 'utf8'), journey.before[file], 'Investigation changed');
    const base = JSON.parse(fs.readFileSync(path.join(root, 'base.json'), 'utf8'));
    assert.equal(git(root, 'rev-parse', 'HEAD'), base.revisions.head, 'Product revision changed without approval');
    assert.equal(git(root, 'status', '--porcelain', '--untracked-files=all'), '', 'Product changed without approval');
    for (const [calls, needsComment] of [[journey.firstCalls, true], [journey.secondCalls, false]]) {
      const logged = calls.trim().split('\n').filter(Boolean).map(JSON.parse);
      assert.ok(logged.some(call => call.tool === 'bd' && positionals(call.args)[0] === 'ready'), 'No ready query');
      assert.ok(logged.some(call => call.tool === 'bd' && positionals(call.args)[0] === 'show' &&
        positionals(call.args)[1] === 'demo-next'), 'Next item was not inspected');
      if (needsComment) assert.ok(logged.some(call => call.tool === 'bd' &&
        positionals(call.args).slice(0, 3).join(' ') === 'comments add demo-next'), 'No Beads record action');
      else assert.ok(!logged.some(call => call.tool !== 'bd' ||
        !['show', 'ready', 'list', 'comments', 'where', 'prime'].includes(positionals(call.args)[0]) ||
        positionals(call.args)[0] === 'comments' && positionals(call.args)[1] === 'add'), 'Second session wrote work state');
    }
    const normalize = text => text.replace(/^\s*\d+[→\t] ?/gm, '').replace(/\s/g, '');
    const toolText = value => typeof value === 'string' ? value
      : value && typeof value === 'object' ? Object.values(value).map(toolText).join('\n') : '';
    for (const [trace, target, contents] of [
      [first, 'config/retry.json', source.toString()],
      [second, '.brain/docs/investigation.json', journey.before[file]],
      [second, 'config/retry.json', source.toString()],
    ]) {
      const resolved = fs.realpathSync(path.join(root, 'workspace', target));
      const read = trace.calls.some(call => {
        if (trace.runtime === 'claude') {
          if (call.name !== 'Read' || call.is_error) return false;
          const named = call.input.file_path || call.input.path;
          return typeof named === 'string' &&
            fs.realpathSync(path.resolve(root, 'workspace', named)) === resolved &&
            normalize(toolText(call.output)).includes(normalize(contents));
        }
        if (call.type !== 'commandExecution' || call.status !== 'completed' || call.exitCode !== 0 ||
          call.threadId !== trace.lead) return false;
        const actions = Array.isArray(call.commandActions) ? call.commandActions : [];
        return actions.some(action => action.type === 'read' && typeof action.path === 'string' &&
          fs.realpathSync(path.resolve(call.cwd, action.path)) === resolved) &&
          normalize(call.aggregatedOutput || '').includes(normalize(contents));
      });
      if (!read) throw new Error('INCONCLUSIVE: no corroborated ' +
        (trace === first ? 'first' : 'second') + '-session read of ' + target);
    }
    return {pass: true, score: 1, reason: 'Two fresh sessions recovered durable understanding and gated Beads work'};
  } catch (error) {
    return {pass: false, score: 0, reason: error.message};
  }
}

module.exports = {continuation};
