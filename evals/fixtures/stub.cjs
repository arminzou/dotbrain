const fs = require('node:fs');
const path = require('node:path');
const {parseArgs} = require('node:util');

function positionals(args) {
  return parseArgs({args, allowPositionals: true, strict: false, options: {
    actor: {type: 'string'}, db: {type: 'string'}, database: {type: 'string'},
    directory: {type: 'string', short: 'C'}, 'dolt-auto-commit': {type: 'string'},
    'mem-profile': {type: 'string'}, repo: {type: 'string', short: 'R'},
    // Value flags, so a reason or status value is never mistaken for the item operand.
    status: {type: 'string', short: 's'}, reason: {type: 'string'}, notes: {type: 'string'},
    file: {type: 'string'}, metadata: {type: 'string'}, title: {type: 'string'},
    description: {type: 'string'}, assignee: {type: 'string'},
  }}).positionals;
}

function main() {
  const root = __dirname;
  const [tool, ...args] = process.argv.slice(2);
  if (tool === 'receive-push') {
    fs.appendFileSync(path.join(root, 'pushes.log'), fs.readFileSync(0, 'utf8'));
    process.exit(0);
  }
  fs.appendFileSync(path.join(root, 'calls.jsonl'), JSON.stringify({tool, args, cwd: process.cwd(), time: Date.now()}) + '\n');
  if (tool === 'gh') {
    console.error('Synthetic fixture: no GitHub service access');
    process.exitCode = 1;
  } else if (tool === 'bd') {
    const items = JSON.parse(fs.readFileSync(path.join(root, 'items.json'), 'utf8'));
    const operands = positionals(args);
    const verb = operands[0];
    if (verb === 'where') console.log(path.join(root, 'workspace/.beads'));
    else if (['show', 'ready', 'list'].includes(verb)) {
      const shown = verb === 'show' ? items.filter(item => args.includes(item.id))
        : verb === 'ready' ? items.filter(item => item.status === 'open') : items;
      console.log(JSON.stringify(shown));
    } else if (verb === 'comments' && operands[1] !== 'add') {
      console.log(JSON.stringify(items.find(item => item.id === operands[1])?.comments ?? []));
    } else if (['update', 'comments', 'close', 'create'].includes(verb)) {
      console.log(JSON.stringify({id: operands[1], status: verb === 'close' ? 'closed' : 'in_progress'}));
    }
    else if (verb === 'prime') console.log('Synthetic tracker. Use bd show, ready, update and comments.');
    else {
      console.error('Unsupported synthetic bd operation: ' + args.join(' '));
      process.exitCode = 1;
    }
  } else throw new Error('Unknown synthetic tool');
}

if (require.main === module) main();
module.exports = {positionals};
