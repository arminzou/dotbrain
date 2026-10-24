const path = require('node:path');
const {environment} = require('./workspace.cjs');

module.exports = ({vars, provider}) => {
  if (!vars.fixtureRoot) throw new Error('The beforeEach workspace hook did not run');
  const root = vars.fixtureRoot;
  const claude = provider.id.startsWith('anthropic:');
  const config = {working_dir: path.join(root, 'workspace')};
  // Per-case data sits in one `fixture` object: Promptfoo expands array vars into a test matrix.
  // Tests opt into writing tools; only a lead with Bash, Write or Edit leaves Codex's read-only
  // sandbox, so decision exercises can offer `Agent` (to prove no dispatch) and stay read-only.
  const {tools = ['Read', 'Grep', 'Glob', 'Skill'], maxTurns = 60} = vars.fixture ?? {};
  const readOnly = !tools.some(tool => ['Bash', 'Write', 'Edit'].includes(tool));
  config.model = process.env[claude ? 'EVAL_CLAUDE_MODEL' : 'EVAL_CODEX_MODEL'];
  if (!config.model) throw new Error('Choose EVAL_CLAUDE_MODEL/EVAL_CODEX_MODEL before running a live provider');
  if (claude) {
    config.max_turns = maxTurns;
    config.env = environment(root);
    config.plugins = [{type: 'local', path: path.join(root, 'plugin')}];
    config.tools = tools;
    config.custom_allowed_tools = tools;
  } else {
    config.cli_env = environment(root);
    config.additional_directories = [root];
    if (readOnly) config.sandbox_mode = 'read-only';
  }
  return {prompt: vars.request.replaceAll('{{worker_role}}', claude ? 'dotbrain:worker' : 'dotbrain-worker'), config};
};
