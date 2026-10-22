// dotbrain-managed: the dotbrain CLI delivers this file and replaces it on update; edits are lost.
/**
 * OpenCode entry point for the dotbrain plugin.
 *
 * The CLI copies this file to `<opencode config>/plugins/dotbrain.js`, the packaged skills to
 * `<opencode config>/dotbrain/packaged/skills/`, and links the operator's global skills into
 * `<opencode config>/dotbrain/skills/`. OpenCode scans neither directory on its own; the `config`
 * hook adds both to `skills.paths`, so each skill keeps its supporting files next to its SKILL.md.
 *
 * Explicit-only skills (`disable-model-invocation: true`) stay manual: the hook appends a
 * `permission.skill` deny rule for each, after the user's own rules, since the last matching rule
 * wins. A denied skill is hidden from the model and its `skill` tool refuses it, while the user's
 * `/<skill>` command still loads it. Project skills the CLI links into `.opencode/skills/` get the
 * same rule.
 *
 * Session hooks hand each OpenCode event to `dotbrain hook run --checkout <worktree>`, which decides
 * wiring, assembles the convention and syncs; this file only maps events and caches what the CLI
 * printed, and only in git projects:
 *
 * - the first `chat.message` of a root session runs `startup` (`resume` for a session this instance
 *   did not see created) and caches the convention; `experimental.chat.system.transform` adds it to
 *   every request of that session, since OpenCode rebuilds the system prompt each time;
 * - `session.compacted` runs `compaction` and refreshes the cached convention;
 * - `session.idle` ends every run loop: `turn-end` pushes in the background;
 * - `dispose` tears the instance down, as on exit: `session-end` schedules a full sync;
 * - child sessions (task subagents, which have a `parentID`) get no convention and no sync.
 *
 * Every hook fails open: OpenCode gives hooks no timeout and a throwing hook fails the prompt, so a
 * missing, failing or slow `dotbrain` leaves the agent untouched.
 *
 * Node built-ins only: OpenCode installs no dependencies for this file.
 */
import { spawn } from "node:child_process"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

// OpenCode records no version for file plugins, so the release is named here.
const VERSION = "0.11.0" // x-release-please-version

const CONFIG_DIR = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const SKILL_ROOTS = [
  path.join(CONFIG_DIR, "dotbrain", "packaged", "skills"),
  path.join(CONFIG_DIR, "dotbrain", "skills"),
]

function isDir(target) {
  try {
    return fs.statSync(target).isDirectory()
  } catch {
    return false
  }
}

/** Top-level `key: value` fields of a SKILL.md frontmatter block, as strings. */
function frontmatter(text) {
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/)
  const fields = {}
  if (lines[0]?.trim() !== "---") return fields
  for (const line of lines.slice(1)) {
    if (line.trim() === "---") break
    const match = /^([A-Za-z0-9_-]+):(.*)$/.exec(line)
    if (!match) continue
    let value = match[2].trim()
    const quote = value[0]
    const end = quote === '"' || quote === "'" ? value.indexOf(quote, 1) : -1
    value = end > 0 ? value.slice(1, end) : value.startsWith("#") ? "" : value.replace(/\s+#.*$/, "")
    fields[match[1]] = value
  }
  return fields
}

/** SKILL.md files below `root`, following links as OpenCode's scan does. */
function skillFiles(root, depth = 0) {
  let entries
  try {
    entries = fs.readdirSync(root, { withFileTypes: true })
  } catch {
    return []
  }
  const found = []
  for (const entry of entries) {
    const full = path.join(root, entry.name)
    if (entry.name === "SKILL.md") found.push(full)
    // ponytail: depth cap instead of cycle detection; skills nest a few levels at most.
    else if (depth < 8 && entry.name !== "node_modules" && isDir(full)) found.push(...skillFiles(full, depth + 1))
  }
  return found
}

/** Names of the explicit-only skills below `roots`, as OpenCode names them (frontmatter `name`). */
function manualOnly(roots) {
  const names = new Set()
  for (const root of roots) {
    for (const file of skillFiles(root)) {
      let fields
      try {
        fields = frontmatter(fs.readFileSync(file, "utf8"))
      } catch {
        continue // OpenCode cannot load it either
      }
      if (String(fields["disable-model-invocation"] ?? "").toLowerCase() === "true") {
        names.add(fields.name || path.basename(path.dirname(file)))
      }
    }
  }
  return [...names].sort()
}

/** `permission` with a deny rule for each name appended last under `skill`; other keys untouched. */
function denyLast(permission, names) {
  const rules = permission == null ? {} : typeof permission === "string" ? { "*": permission } : permission
  if (typeof rules !== "object" || Array.isArray(rules)) return permission
  const skill = rules.skill
  const own = typeof skill === "string" ? { "*": skill } : skill && typeof skill === "object" ? { ...skill } : {}
  for (const name of names) {
    delete own[name]
    own[name] = "deny"
  }
  // Re-adding the key moves it after every other permission, `*` included.
  delete rules.skill
  rules.skill = own
  return rules
}

// The CLI's session start waits at most 10 s for sync.
const START_TIMEOUT_MS = 12_000
// First line of every convention `dotbrain hook run` prints.
const HEADING = "## dotbrain convention"

function isExecutable(target) {
  try {
    if (!fs.statSync(target).isFile()) return false
    if (process.platform !== "win32") fs.accessSync(target, fs.constants.X_OK)
    return true
  } catch {
    return false
  }
}

/** `dotbrain` on PATH, as a shell would find it; undefined when absent. */
function findCli() {
  const exts = process.platform === "win32" ? (process.env.PATHEXT || ".COM;.EXE;.BAT;.CMD").split(";") : [""]
  for (const dir of (process.env.PATH || "").split(path.delimiter)) {
    if (!dir) continue
    for (const ext of exts) {
      const file = path.join(dir, "dotbrain" + ext)
      if (isExecutable(file)) return file
    }
  }
}

function spawnCli(event, checkout, options) {
  const exe = findCli()
  if (!exe) return undefined
  const args = ["hook", "run", "--event", event, "--checkout", checkout]
  const opts = { windowsHide: true, ...options }
  // Node runs .cmd and .bat files only through cmd.exe.
  // ponytail: cmd.exe still expands %VAR% inside a quoted path; an .exe has no such issue.
  const child = /\.(cmd|bat)$/i.test(exe)
    ? spawn(`"${exe}"`, args.map((arg) => `"${arg}"`), { ...opts, shell: true })
    : spawn(exe, args, opts)
  child.on("error", () => {}) // an unhandled spawn error would crash OpenCode
  return child
}

/** What `dotbrain hook run` printed for this event; "" when it is absent, fails or overruns. */
function hookRun(event, checkout) {
  return new Promise((resolve) => {
    let out = ""
    let child
    // A timer of its own: a process the CLI leaves behind can hold the pipe open past the kill.
    const timer = setTimeout(() => {
      child?.kill()
      resolve("")
    }, START_TIMEOUT_MS)
    const done = (text) => {
      clearTimeout(timer)
      resolve(text)
    }
    child = spawnCli(event, checkout, { stdio: ["ignore", "pipe", "ignore"] })
    if (!child) return done("")
    child.stdout.setEncoding("utf8").on("data", (chunk) => (out += chunk))
    child.on("error", () => done(""))
    child.on("close", (code) => done(code === 0 ? out.trim() : ""))
  })
}

/** Start `dotbrain hook run` without waiting; the CLI starts its own detached sync. */
function launch(event, checkout) {
  spawnCli(event, checkout, { detached: true, stdio: "ignore" })?.unref()
}

/** `hook`, made never to throw or reject. */
function failOpen(hook) {
  return async (...args) => {
    try {
      await hook(...args)
    } catch {
      // a hook must never break the agent
    }
  }
}

function sessionHooks(client, checkout) {
  const created = new Set() // sessions this instance saw created
  const children = new Set() // child sessions: no convention, no sync
  const conventions = new Map() // root session id -> Promise of its convention ("" when unwired)

  async function isChild(id) {
    if (children.has(id)) return true
    if (created.has(id)) return false
    try {
      return Boolean((await client.session.get({ path: { id } }))?.data?.parentID)
    } catch {
      return false // an unknown session counts as a root: missing the convention costs more
    }
  }

  return {
    "chat.message": failOpen(async ({ sessionID } = {}) => {
      if (!sessionID || children.has(sessionID)) return
      if (!conventions.has(sessionID)) {
        const event = created.has(sessionID) ? "startup" : "resume"
        conventions.set(sessionID, isChild(sessionID).then((child) => {
          if (!child) return hookRun(event, checkout)
          children.add(sessionID)
          conventions.delete(sessionID)
          return ""
        }))
      }
      await conventions.get(sessionID)
    }),
    "experimental.chat.system.transform": failOpen(async ({ sessionID } = {}, output) => {
      if (!sessionID || !conventions.has(sessionID)) return
      const text = await conventions.get(sessionID)
      if (text && !output.system.some((part) => part.includes(HEADING))) output.system.push(text)
    }),
    event: failOpen(async ({ event } = {}) => {
      const props = event?.properties ?? {}
      if (event?.type === "session.created" && props.info?.id) {
        created.add(props.info.id)
        if (props.info.parentID) children.add(props.info.id)
      } else if (event?.type === "session.compacted" && conventions.has(props.sessionID)) {
        const old = conventions.get(props.sessionID)
        conventions.set(props.sessionID, hookRun("compaction", checkout).then(async (text) => text || (await old)))
      } else if (event?.type === "session.idle" && conventions.has(props.sessionID)) {
        launch("turn-end", checkout)
      }
    }),
    // Awaited at instance teardown (exit, quit, config reload); a killed process skips it.
    dispose: failOpen(() => {
      for (const _ of conventions.keys()) launch("session-end", checkout)
      conventions.clear()
    }),
  }
}

async function server({ client, project: info, directory, worktree } = {}) {
  const project = [...new Set([worktree, directory].filter(Boolean))].map((dir) => path.join(dir, ".opencode", "skills"))
  return {
    // A git project's worktree is the checkout; elsewhere there is nothing to wire.
    ...(info?.vcs === "git" && worktree ? sessionHooks(client, worktree) : {}),
    async config(cfg) {
      const roots = SKILL_ROOTS.filter(isDir)
      cfg.skills ??= {}
      const listed = cfg.skills.paths ?? []
      cfg.skills.paths = [...listed, ...roots.filter((root) => !listed.includes(root))]
      const names = manualOnly([...roots, ...project])
      if (!names.length) return
      cfg.permission = denyLast(cfg.permission, names)
      // An agent's own permission is applied after the global one, so it needs the rules too.
      // ponytail: legacy `mode` entries are not covered; OpenCode merges them into `agent`.
      for (const agent of Object.values(cfg.agent ?? {})) {
        if (agent && agent.permission != null) agent.permission = denyLast(agent.permission, names)
      }
    },
  }
}

export default { id: "dotbrain", server }
