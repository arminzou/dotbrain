// The coding agents dotbrain delivers to, in the order the site lists them. Icons live under
// public/assets/agents/; a monochrome icon has one file per colour scheme.
export interface Agent {
  name: string
  icon: string
  themed?: boolean
}

export const agents: Agent[] = [
  { name: 'Claude Code', icon: 'claudecode-color' },
  { name: 'Codex', icon: 'codex-color' },
  { name: 'OpenCode', icon: 'opencode', themed: true },
  { name: 'Cursor', icon: 'cursor', themed: true },
  { name: 'Hermes', icon: 'hermesagent', themed: true },
  { name: 'Pi', icon: 'pi', themed: true },
]
