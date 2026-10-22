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
 * Node built-ins only: OpenCode installs no dependencies for this file.
 */
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

async function server({ directory, worktree } = {}) {
  const project = [...new Set([worktree, directory].filter(Boolean))].map((dir) => path.join(dir, ".opencode", "skills"))
  return {
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
    // Session hooks join this object.
  }
}

export default { id: "dotbrain", server }
