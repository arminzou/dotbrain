const fs = require('node:fs');
const path = require('node:path');
const yaml = require('js-yaml');
const request = require('../fixtures/request.cjs');
const {lendCodexLogin, returnCodexLogin} = require('../fixtures/workspace.cjs');
const {evidence} = require('../assertions/evidence.cjs');

const read = (root, file) => fs.readFileSync(path.join(root, file), 'utf8');
const records = root => Object.fromEntries(['workspace/.brain/docs/investigation.json', 'items.json']
  .map(file => [file, read(root, file)]));

function resetRuntime(root, configuration) {
  returnCodexLogin(root);
  for (const directory of ['home/.codex', 'home/.claude', 'tmp']) {
    const target = path.resolve(root, directory);
    if (!target.startsWith(path.resolve(root) + path.sep) || fs.lstatSync(target).isSymbolicLink()) {
      throw new Error('Refusing to reset a runtime outside the synthetic fixture');
    }
    fs.rmSync(target, {recursive: true, force: true});
    fs.mkdirSync(target, {recursive: true});
  }
  fs.writeFileSync(path.join(root, 'home/.codex/config.toml'), configuration);
  for (const file of ['calls.jsonl', 'git-agent.jsonl']) fs.writeFileSync(path.join(root, file), '');
  lendCodexLogin(root);
}

class ContinuationProvider {
  constructor(options) {
    this.config = options.config;
  }
  id() { return 'continuation:' + this.config.runtime; }

  async callApi(prompt, context, callOptions) {
    if (process.env.DOTBRAIN_EVAL_LIVE !== '1') {
      throw new Error('Continuation requires the shared live authorization gate');
    }
    const root = context.vars.fixtureRoot;
    const runtime = this.config.runtime;
    const file = runtime === 'anthropic:claude-agent-sdk' ? 'claude.yaml'
      : runtime === 'openai:codex-app-server' ? 'codex.yaml' : null;
    if (!file) throw new Error('Unsupported continuation runtime');
    const native = yaml.load(fs.readFileSync(path.join(__dirname, file), 'utf8'));
    const configuration = read(root, 'home/.codex/config.toml');
    const load = this.loadProvider ?? require('promptfoo').loadApiProvider;
    const invoke = async task => {
      const vars = {fixtureRoot: root, fixture: context.vars.fixture, request: task};
      const built = request({vars, provider: {id: runtime}});
      const config = {...native.config, ...context.originalProvider?.config,
        ...this.config.nativeConfig, ...built.config};
      if (['resume', 'continue', 'resume_session_at', 'fork_session', 'session_id', 'thread_id']
        .some(key => config[key]) || config.persist_session || config.persist_threads || config.reuse_server) {
        throw new Error('Continuation requires fresh sessions without resume or persistence options');
      }
      const provider = await load(runtime, {options: {config}});
      try {
        const response = await provider.callApi(built.prompt, {vars, prompt: {config}}, callOptions);
        evidence({providerResponse: response});
        return {response, input: {prompt: built.prompt, fresh: file === 'claude.yaml'
          ? {persist_session: config.persist_session}
          : {persist_threads: config.persist_threads, reuse_server: config.reuse_server}}};
      } finally { await provider.cleanup?.(); }
    };
    try {
      const first = await invoke(context.vars.continuation.first);
      const before = records(root);
      const firstCalls = read(root, 'calls.jsonl');
      const firstGit = read(root, 'git-agent.jsonl');
      resetRuntime(root, configuration);
      const second = await invoke(prompt);
      const secondCalls = read(root, 'calls.jsonl');
      fs.writeFileSync(path.join(root, 'calls.jsonl'), firstCalls + secondCalls);
      fs.writeFileSync(path.join(root, 'git-agent.jsonl'), firstGit + read(root, 'git-agent.jsonl'));
      return {...second.response,
        ...(first.response.cost !== undefined && second.response.cost !== undefined
          ? {cost: first.response.cost + second.response.cost} : {}),
        metadata: {...second.response.metadata, continuation: {
          first, secondInput: second.input, before, after: records(root), firstCalls, secondCalls,
        }}};
    } finally { returnCodexLogin(root); }
  }
}

module.exports = ContinuationProvider;
