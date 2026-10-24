const path = require('node:path');
const {environment} = require('./workspace.cjs');

module.exports = ({vars, provider}) => {
  if (!vars.fixtureRoot) throw new Error('The beforeEach workspace hook did not run');
  const root = vars.fixtureRoot;
  const claude = provider.id.startsWith('anthropic:');
  const config = {working_dir: path.join(root, 'workspace')};
  config.model = process.env[claude ? 'EVAL_CLAUDE_MODEL' : 'EVAL_CODEX_MODEL'];
  if (!config.model) throw new Error('Choose EVAL_CLAUDE_MODEL/EVAL_CODEX_MODEL before running a live provider');
  if (claude) {
    config.max_turns = vars.case === 'worker-never-pushes' ? 40 : 60;
    config.env = environment(root);
    config.plugins = [{type: 'local', path: path.join(root, 'plugin')}];
    const readOnly = ['activation-review-gate', 'explicit-only-not-loaded-run-retro'].includes(vars.case);
    config.tools = readOnly ? ['Read', 'Grep', 'Glob', 'Skill'] : ['Read', 'Grep', 'Glob', 'Skill', 'Agent', 'Bash', 'Write', 'Edit'];
    config.custom_allowed_tools = config.tools;
  } else {
    config.cli_env = environment(root);
    config.additional_directories = [root];
    if (['activation-review-gate', 'explicit-only-not-loaded-run-retro'].includes(vars.case)) config.sandbox_mode = 'read-only';
  }
  return {prompt: vars.request.replaceAll('{{worker_role}}', claude ? 'dotbrain:worker' : 'dotbrain-worker'), config};
};
