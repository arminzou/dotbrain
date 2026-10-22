"""Hermes entry point for the dotbrain plugin.

Registers each skill under ``skills/`` from its own SKILL.md, so supporting files stay next to it,
and keeps explicit-only skills manual: Hermes ignores ``disable-model-invocation``, so a
``pre_tool_call`` veto refuses the model's own ``skill_view`` of them while the user's
``/dotbrain:<skill>`` command, which loads the skill without a tool call, still works. The veto
resolves each request to the file Hermes would serve, so it covers every alias Hermes accepts and
the private skills dotbrain links for Hermes too.

Session hooks hand each Hermes event to ``dotbrain hook run``, which decides wiring, assembles the
convention and syncs; this file only maps events and caches what the CLI printed:

- the first ``pre_llm_call`` of a session runs ``startup`` (``resume`` when Hermes restored an
  existing session) and injects the convention;
- a later turn whose history no longer holds the convention (compaction) runs ``compaction`` and
  injects it again; Hermes keeps injected context in its history, so it is never added twice;
- ``on_session_end`` ends every turn: ``turn-end`` pushes in the background;
- ``on_session_finalize`` is a real exit: ``session-end`` schedules a full sync;
- delegated children get no convention and no sync.

Every hook fails open: a missing or failing ``dotbrain`` leaves the agent untouched. The skill veto
is the exception: it blocks a manual-only skill whose request or policy it cannot judge.

Hermes runs this in its own environment: standard library only. The veto uses Hermes's own skill
lookup and frontmatter parser when it can import them.
"""

import os
import posixpath
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

SKILLS = Path(__file__).resolve().parent / "skills"
NAMESPACE = "dotbrain"


def _block(style, lines):
    """A YAML literal (``|``) or folded (``>``) block scalar with clip, strip or keep chomping."""
    lines = textwrap.dedent("\n".join(lines)).split("\n")
    if style[0] == "|":
        text = "\n".join(lines)
    else:
        # ponytail: more-indented folded lines are folded too; YAML keeps their line breaks.
        text = ""
        for line in lines:
            if not line.strip():
                text += "\n"
            else:
                text += (" " if text and not text.endswith("\n") else "") + line.strip()
    chomp = style[1:2]
    if chomp == "-":
        return text.rstrip("\n")
    return text + "\n" if chomp == "+" else text.rstrip("\n") + "\n"


def _frontmatter(text):
    """Top-level fields of a SKILL.md frontmatter block, as strings."""
    lines = text.removeprefix("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields = {}
    key, block = None, []
    for line in lines[1:] + ["---"]:
        if key is not None and (not line.strip() or line[:1].isspace()) and line.strip() != "---":
            block.append(line)
            continue
        if key is not None:
            fields[key] = _block(style, block)
            key, block = None, []
        if line.strip() == "---":
            break
        name, sep, value = line.partition(":")
        if not sep or line[:1].isspace():
            continue
        value = value.strip()
        if value[:1] in ("|", ">"):
            key, style = name.strip(), value
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif value[:1] in ("\"", "'") and value.find(value[0], 1) > 0:  # a quoted scalar, then a comment
            value = value[1:value.find(value[0], 1)]  # ponytail: no escape handling inside quotes
        elif value.startswith("#"):
            value = ""
        else:
            value = value.split(" #", 1)[0].split("\t#", 1)[0].rstrip()
        fields[name.strip()] = value
    return fields


def skills():
    """``(name, SKILL.md path, frontmatter)`` for each packaged skill."""
    for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
        yield skill_md.parent.name, skill_md, _frontmatter(skill_md.read_text(encoding="utf-8"))


def _supporting_file(skill_md, file_path):
    """Whether ``file_path``, which Hermes resolves against the skill directory, names a file other
    than the skill's SKILL.md inside it; a supporting-file read belongs to a skill the user already invoked."""
    text = str(file_path or "").strip()
    path = posixpath.normpath(text.replace("\\", "/"))
    if path in (".", "..") or path.startswith(("../", "/")) or ":" in path or path.casefold() == "skill.md":
        return False
    # The host may resolve aliases the text hides: Windows drops trailing dots, so SKILL.md. is SKILL.md.
    root = os.path.normcase(os.path.realpath(skill_md.parent))
    target = os.path.normcase(os.path.realpath(os.path.join(root, text)))
    try:
        if os.path.commonpath([root, target]) != root or target == root:
            return False
    except ValueError:  # another drive
        return False
    if target == os.path.normcase(os.path.realpath(skill_md)):
        return False
    return not (os.path.exists(target) and os.path.samefile(target, skill_md))


def _hermes_home():
    try:
        from hermes_constants import get_hermes_home  # not public Hermes API; may move
        return Path(get_hermes_home())
    except Exception:  # noqa: BLE001
        return Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")


def _project_root():
    """The project root Hermes reads project skills from: the nearest ancestor holding ``.git``."""
    try:
        from agent.skill_utils import find_project_root  # not public Hermes API; may move
    except Exception:  # noqa: BLE001
        find_project_root = None
    if find_project_root is not None:
        return find_project_root()
    start = Path(_checkout()).resolve()
    for directory in (start, *start.parents):
        if (directory / ".git").exists():
            return None if directory == Path.home().resolve() else directory  # Hermes skips the home
    return None


def _policy(text):
    """Frontmatter fields as Hermes reads them: with Hermes's own parser, else PyYAML, else stdlib."""
    try:
        from agent.skill_utils import parse_frontmatter  # not public Hermes API; may move
    except ImportError:
        pass
    else:
        return parse_frontmatter(text)[0]
    text = text.removeprefix("\ufeff")
    try:
        import yaml
    except ImportError:
        return _frontmatter(text)
    end = re.search(r"\n---\s*\n", text[3:]) if text.startswith("---") else None
    if end is None:
        return {}
    block = text[3:end.start() + 3]
    try:
        fields = yaml.safe_load(block)
    except yaml.YAMLError:  # Hermes falls back to key: value lines
        pairs = (line.split(":", 1) for line in block.strip().split("\n") if ":" in line)
        fields = {key.strip(): value.strip() for key, value in pairs}
    return fields if isinstance(fields, dict) else {}


def _is_manual(skill_md):
    """Whether this SKILL.md is manual-only; one whose policy cannot be read counts as manual-only."""
    try:
        text = Path(skill_md).read_text(encoding="utf-8-sig", errors="replace")
        flag = _policy(text).get("disable-model-invocation")
    except Exception:  # noqa: BLE001 - fail closed for this skill
        return True
    return flag is True or str(flag).strip().lower() == "true"


def _hermes_served(name, file_path):
    """``(SKILL.md, served file)`` for what Hermes's ``skill_view`` would serve, found with the
    lookup skill_view itself uses; None when it would serve nothing. Raises outside Hermes."""
    from agent.skill_utils import is_valid_namespace, parse_qualified_name  # not public Hermes API
    from hermes_cli.plugins import get_plugin_manager
    from tools import skills_tool
    from tools.path_security import has_traversal_component, validate_within_dir

    def served(skill_dir, skill_md):
        if not file_path:
            return skill_md, skill_md
        target = skill_dir / file_path
        if has_traversal_component(file_path) or validate_within_dir(target, skill_dir) or not target.is_file():
            return None
        return skill_md, target

    if skills_tool._skill_lookup_path_error(name):
        return None
    local = None
    if ":" in name:
        namespace, bare = parse_qualified_name(name)
        if not is_valid_namespace(namespace):
            return None
        plugins = get_plugin_manager()
        skill_md = plugins.find_plugin_skill(name)
        if skill_md is not None:
            return served(skill_md.parent, skill_md) if skill_md.exists() else None
        if plugins.list_plugin_skills(namespace):
            return None
        local = f"{namespace}/{bare}" if bare else None
        if local and skills_tool._skill_lookup_path_error(local):
            return None
    roots, _ = skills_tool._skill_search_dirs()
    error, skill_dir, skill_md = skills_tool._locate_skill(name, local, roots)
    if error is not None:
        return None
    # A flat <name>.md skill has no directory, and Hermes then serves it whatever file_path says.
    return served(skill_dir, skill_md) if skill_dir else (skill_md, skill_md)


def _serves_manual(skill_md, target):
    """Whether serving ``target`` hands over the instructions of a manual-only skill."""
    skill_md, target = Path(skill_md), Path(target)
    if target == skill_md or (target.exists() and os.path.samefile(target, skill_md)):
        return _is_manual(skill_md)
    return target.name.casefold() == "skill.md" and _is_manual(target)  # a nested skill's own SKILL.md


def _fallback_blocks(name, file_path, manual):
    """Without Hermes's lookup, fail closed: block a name whose last path component names a
    manual-only packaged or linked skill, unless ``file_path`` names one of its supporting files."""
    path = posixpath.normpath(str(name or "").strip().rpartition(":")[2].replace("\\", "/"))
    if path in (".", "..") or path.startswith(("../", "/")):
        return False  # Hermes refuses traversal and absolute names
    last = path.rsplit("/", 1)[-1]
    project = _project_root()
    roots = ([project / ".hermes" / "skills"] if project else []) + [_hermes_home() / "skills"]
    packaged = [md for key, md in manual.items() if os.path.normcase(key) == os.path.normcase(last)]
    linked = [root / last / "SKILL.md" for root in roots if (root / last / "SKILL.md").is_file()]
    candidates = packaged + [md for md in linked if _is_manual(md)]
    return any(not _supporting_file(md, file_path) for md in candidates)


def manual_only_veto(manual):
    """A ``pre_tool_call`` hook that blocks the model from loading a manual-only skill.

    It resolves the request with Hermes's own lookup to the file Hermes would serve, and blocks it
    when that is the SKILL.md of a manual-only skill, packaged or private alike. ``manual`` maps
    each packaged manual-only skill to its SKILL.md, for the fallback when that lookup fails.
    """

    def veto(tool_name="", args=None, **_):
        if tool_name != "skill_view" or not isinstance(args, dict):
            return None
        name, file_path = args.get("name"), args.get("file_path")
        try:
            found = _hermes_served(name, file_path)
            blocked = found is not None and _serves_manual(*found)
        except Exception:  # noqa: BLE001 - outside Hermes, or its lookup failed
            blocked = _fallback_blocks(name, file_path, manual)
        if blocked:
            label = str(name).strip()
            return {"action": "block", "message": f"{label} runs only when the user invokes /{label}."}
        return None

    return veto


def register(ctx):
    manual = {}
    for name, skill_md, fields in skills():
        ctx.register_skill(name, skill_md, description=fields.get("description", ""), frontmatter=fields)
        if fields.get("disable-model-invocation", "").lower() == "true":
            manual[name] = skill_md
    ctx.register_hook("pre_tool_call", _fail_open(manual_only_veto(manual)))
    for name, hook in HOOKS.items():
        ctx.register_hook(name, _fail_open(hook))


# The CLI's session start waits at most 10 s for sync; Hermes allows a hook 30 s.
START_TIMEOUT = 25
# Hermes time-boxes finalize (10 s in the gateway); session-end only launches a sync and returns.
END_TIMEOUT = 5
# First line of every convention `dotbrain hook run` prints.
HEADING = "## dotbrain convention"

_conventions = {}  # session id -> convention the CLI printed for it ("" when unwired)
_children = set()  # delegated child session ids: no convention, no sync


def _checkout():
    try:
        from agent.runtime_cwd import resolve_agent_cwd  # not public Hermes API; may move
        return str(resolve_agent_cwd())
    except Exception:  # noqa: BLE001
        return os.getcwd()


def _argv(event):
    exe = shutil.which("dotbrain")
    return [exe, "hook", "run", "--event", event, "--checkout", _checkout()] if exe else None


def _hook_run(event, timeout):
    """What ``dotbrain hook run`` printed for this event; "" when it is absent or fails."""
    argv = _argv(event)
    if argv is None:
        return ""
    try:
        done = subprocess.run(argv, capture_output=True, encoding="utf-8", errors="replace",
                              stdin=subprocess.DEVNULL, timeout=timeout, check=False)
    except Exception:  # noqa: BLE001 - cached as "", so a broken CLI is not retried every turn
        return ""
    return done.stdout.strip() if done.returncode == 0 and done.stdout else ""


def _launch(event):
    """Start ``dotbrain hook run`` without waiting; the CLI starts its own detached sync."""
    argv = _argv(event)
    if argv is None:
        return
    detach = ({"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
              if sys.platform == "win32" else {"start_new_session": True})
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **detach)


def _in_history(history):
    """Whether a message already carries a convention; Hermes replays injected context as ``api_content``.

    Matched by the heading the CLI prints, not the body: a restored history may hold an older
    convention, which Hermes cannot remove, so a newer one must not be added beside it.
    """
    return any(isinstance(message, dict) and any(isinstance(message.get(key), str) and HEADING in message[key]
                                                 for key in ("api_content", "content"))
               for message in history or ())


def _pre_llm_call(session_id=None, conversation_history=None, is_first_turn=False, parent_session_id=None, **_):
    if parent_session_id:
        _children.add(session_id)
    if not session_id or session_id in _children:
        return None
    if session_id not in _conventions:
        _conventions[session_id] = _hook_run("startup" if is_first_turn else "resume", START_TIMEOUT)
    elif _conventions[session_id] and not _in_history(conversation_history):
        # Compaction dropped it from the history: refresh it and inject it again.
        _conventions[session_id] = _hook_run("compaction", START_TIMEOUT)
    text = _conventions[session_id]
    return {"context": text} if text and not _in_history(conversation_history) else None


def _subagent_start(child_session_id=None, **_):
    if child_session_id:
        _children.add(child_session_id)


def _on_session_end(session_id=None, **_):
    # Hermes fires this at the end of every turn, not at exit.
    if session_id in _conventions:
        _launch("turn-end")


def _on_session_finalize(session_id=None, **_):
    if _conventions.pop(session_id, None) is not None:
        _hook_run("session-end", END_TIMEOUT)


def _on_session_reset(session_id=None, **_):
    _conventions.pop(session_id, None)
    _children.discard(session_id)


HOOKS = {
    "pre_llm_call": _pre_llm_call,
    "subagent_start": _subagent_start,
    "on_session_end": _on_session_end,
    "on_session_finalize": _on_session_finalize,
    "on_session_reset": _on_session_reset,
}


def _fail_open(hook):
    def run(**kwargs):
        try:
            return hook(**kwargs)
        except Exception:  # noqa: BLE001 - a hook must never break the agent
            return None

    return run
