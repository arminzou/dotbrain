// dotbrain-managed: the dotbrain CLI delivers this file and replaces it on update; edits are lost.
/**
 * OpenCode entry point for the dotbrain plugin.
 *
 * The CLI copies this file to `<opencode config>/plugins/dotbrain.js`, the packaged skills to
 * `<opencode config>/dotbrain/packaged/skills/`, and links the operator's global skills into
 * `<opencode config>/dotbrain/skills/`. OpenCode scans neither directory on its own; the `config`
 * hook adds both to `skills.paths`, so each skill keeps its supporting files next to its SKILL.md.
 *
 * Skills reached through a link, which is how the CLI delivers global and project skills, get an
 * `external_directory` allow rule for their resolved directory, so the model reads their supporting
 * files without an approval prompt. Manual-only skills (`disable-model-invocation: true`) are not
 * enforced: OpenCode lists them and the model can invoke them.
 *
 * Session hooks hand each OpenCode event to `dotbrain hook run --checkout <worktree>`, which decides
 * wiring, assembles the convention and syncs; this file only maps events and caches what the CLI
 * printed, and only in git projects:
 *
 * - the first `chat.message` of a confirmed root session runs `startup` (`resume` for a session this
 *   instance did not see created) and caches the convention; `experimental.chat.system.transform`
 *   adds it to every request of that session, since OpenCode rebuilds the system prompt each time;
 * - `session.compacted` runs `compaction` and refreshes the cached convention;
 * - `session.idle` ends every run loop: `turn-end` pushes in the background;
 * - `dispose` tears the instance down: `session-end` schedules a full sync for each idle session,
 *   and a session still running only pushes, since config reload disposes mid-run too;
 * - child sessions (task subagents, which have a `parentID`) and sessions OpenCode cannot classify
 *   get no convention and no sync.
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
const VERSION = "0.15.1" // x-release-please-version

const CONFIG_DIR = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const SKILL_ROOTS = [
  path.join(CONFIG_DIR, "dotbrain", "packaged", "skills"),
  path.join(CONFIG_DIR, "dotbrain", "skills"),
]
// The skill folders OpenCode reads from each `.opencode` config directory.
const PROJECT_SKILL_FOLDERS = ["skills", "skill"]

function isDir(target) {
  try {
    return fs.statSync(target).isDirectory()
  } catch {
    return false
  }
}

/** SKILL.md files below `root`, following links; hidden folders are skipped, as OpenCode's scan does. */
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
    else if (depth < 8 && !entry.name.startsWith(".") && isDir(full)) found.push(...skillFiles(full, depth + 1))
  }
  return found
}

/**
 * `<dir>/*` for each skill below `roots` that OpenCode reaches through a link, `<dir>` resolved.
 * OpenCode lets the model read a skill's own directory, but under the path it found the skill at,
 * while its read check resolves links: a linked skill's supporting files would need approval.
 */
function linkedSkillDirs(roots) {
  const patterns = new Set()
  for (const file of roots.flatMap((root) => skillFiles(root))) {
    try {
      const dir = path.dirname(file)
      const real = fs.realpathSync.native(dir)
      if (real !== path.resolve(dir)) patterns.add(path.join(real, "*"))
    } catch {
      // a broken link: OpenCode cannot load it either
    }
  }
  return [...patterns].sort()
}

/** `permission` with an `external_directory` allow for each pattern, appended last so it wins. */
function allowLast(permission, patterns) {
  const rules = permission == null ? {} : typeof permission === "string" ? { "*": permission } : permission
  if (typeof rules !== "object" || Array.isArray(rules)) return permission
  const current = rules.external_directory
  const own = typeof current === "string" ? { "*": current } : current && typeof current === "object" ? { ...current } : {}
  for (const pattern of patterns) {
    delete own[pattern]
    own[pattern] = "allow"
  }
  // Re-adding the key moves it after every other permission, `*` included.
  delete rules.external_directory
  rules.external_directory = own
  return rules
}

// The CLI's session start waits at most 10 s for sync; this caps the session lookup and the CLI call.
const START_TIMEOUT_MS = 12_000

function isExecutable(target) {
  try {
    if (!fs.statSync(target).isFile()) return false
    if (process.platform !== "win32") fs.accessSync(target, fs.constants.X_OK)
    return true
  } catch {
    return false
  }
}

/** An environment variable by any case: the TUI's worker gets Windows' `Path` as a plain, case-sensitive key. */
function env(name) {
  if (process.platform !== "win32") return process.env[name]
  const key = Object.keys(process.env).find((k) => k.toUpperCase() === name)
  return key === undefined ? undefined : process.env[key]
}

/** `dotbrain` on PATH, as a shell would find it; undefined when absent. */
function findCli() {
  const exts = process.platform === "win32" ? (env("PATHEXT") || ".COM;.EXE;.BAT;.CMD").split(";") : [""]
  for (const dir of (env("PATH") || "").split(path.delimiter)) {
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
    ? spawn(`"${exe}"`, args.map((arg) => `"${arg}"`), { ...opts, shell: env("COMSPEC") || true })
    : spawn(exe, args, opts)
  child.on("error", () => {}) // an unhandled spawn error would crash OpenCode
  return child
}

/** What `dotbrain hook run` printed for this event; "" when it is absent, fails or overruns. */
function hookRun(event, checkout, ms = START_TIMEOUT_MS) {
  return new Promise((resolve) => {
    let out = ""
    let child
    // A timer of its own: a process the CLI leaves behind can hold the pipe open past the kill.
    const timer = setTimeout(() => {
      child?.kill()
      resolve("")
    }, Math.max(ms, 0))
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

/** `promise`, or undefined once `ms` pass first. */
function within(promise, ms) {
  let timer
  const late = new Promise((resolve) => (timer = setTimeout(resolve, ms)))
  return Promise.race([promise, late]).finally(() => clearTimeout(timer))
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
  const roots = new Set() // sessions confirmed as roots: the only ones that sync
  const busy = new Set() // root sessions between a message and the end of their run loop
  const conventions = new Map() // root session id -> Promise of its convention ("" when unwired)

  function forget(id) {
    roots.delete(id)
    busy.delete(id)
    conventions.delete(id)
  }

  /** "root", "child", or undefined when OpenCode cannot say within `ms`. */
  async function role(id, ms) {
    if (children.has(id)) return "child"
    if (created.has(id)) return "root"
    try {
      const info = (await within(client.session.get({ path: { id } }), ms))?.data
      return info?.id ? (info.parentID ? "child" : "root") : undefined
    } catch {
      return undefined
    }
  }

  return {
    "chat.message": failOpen(async ({ sessionID } = {}) => {
      if (!sessionID || children.has(sessionID)) return
      if (!conventions.has(sessionID)) {
        const event = created.has(sessionID) ? "startup" : "resume"
        const deadline = Date.now() + START_TIMEOUT_MS // one cap for the lookup and the CLI
        conventions.set(sessionID, role(sessionID, START_TIMEOUT_MS).then((found) => {
          if (found === "root" && !children.has(sessionID)) {
            roots.add(sessionID)
            return hookRun(event, checkout, deadline - Date.now())
          }
          // A child, or unknown until a later message: a missed convention beats a child's sync.
          if (found === "child") children.add(sessionID)
          forget(sessionID)
          return ""
        }))
      }
      busy.add(sessionID)
      await conventions.get(sessionID)
    }),
    "experimental.chat.system.transform": failOpen(async ({ sessionID } = {}, output) => {
      if (!sessionID || !conventions.has(sessionID)) return
      const text = await conventions.get(sessionID)
      if (text && !output.system.some((part) => part.includes(text))) output.system.push(text)
    }),
    event: failOpen(async ({ event } = {}) => {
      const props = event?.properties ?? {}
      if (event?.type === "session.created" && props.info?.id) {
        created.add(props.info.id)
        if (props.info.parentID) {
          children.add(props.info.id)
          forget(props.info.id)
        }
      } else if (event?.type === "session.compacted" && roots.has(props.sessionID)) {
        const old = conventions.get(props.sessionID)
        conventions.set(props.sessionID, hookRun("compaction", checkout).then(async (text) => text || (await old)))
      } else if (event?.type === "session.idle" && roots.has(props.sessionID)) {
        busy.delete(props.sessionID)
        launch("turn-end", checkout)
      }
    }),
    // Awaited at instance teardown: exit and quit, but also config reload and worktree removal,
    // while runs may still be cancelling; a running session only pushes. A killed process skips it.
    dispose: failOpen(() => {
      for (const id of roots) launch(busy.has(id) ? "turn-end" : "session-end", checkout)
      for (const id of [...roots]) forget(id)
    }),
  }
}

async function server({ client, project: info, directory, worktree } = {}) {
  // ponytail: the directory and the worktree only; OpenCode also reads any .opencode between them.
  const dirs = [...new Set([directory, worktree].filter(Boolean))]
  const projectRoots = dirs.flatMap((dir) => PROJECT_SKILL_FOLDERS.map((name) => path.join(dir, ".opencode", name)))
  return {
    // A git project's worktree is the checkout; elsewhere there is nothing to wire.
    ...(info?.vcs === "git" && worktree ? sessionHooks(client, worktree) : {}),
    async config(cfg) {
      const roots = SKILL_ROOTS.filter(isDir)
      cfg.skills ??= {}
      const listed = cfg.skills.paths ?? []
      cfg.skills.paths = [...listed, ...roots.filter((root) => !listed.includes(root))]
      const dirs = linkedSkillDirs([...roots, ...projectRoots])
      if (!dirs.length) return
      cfg.permission = allowLast(cfg.permission, dirs)
      // An agent's own permission is applied after the global one, so it needs the rules too.
      // ponytail: legacy `mode` entries are not covered; OpenCode merges them into `agent`.
      for (const agent of Object.values(cfg.agent ?? {})) {
        if (agent && agent.permission != null) agent.permission = allowLast(agent.permission, dirs)
      }
    },
  }
}

export default { id: "dotbrain", server }
