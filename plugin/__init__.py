"""Hermes entry point for the dotbrain plugin.

Registers each skill under ``skills/`` from its own SKILL.md, so supporting files stay next to it,
and keeps explicit-only skills manual: Hermes ignores ``disable-model-invocation``, so a
``pre_tool_call`` veto refuses the model's own ``skill_view`` of them while the user's
``/dotbrain:<skill>`` command, which loads the skill without a tool call, still works. The veto
covers the private skills dotbrain links into the checkout's and the Hermes home's ``skills/``
directories too.

Session hooks hand each Hermes event to ``dotbrain hook run``, which decides wiring, assembles the
convention and syncs; this file only maps events and caches what the CLI printed:

- the first ``pre_llm_call`` of a session runs ``startup`` (``resume`` when Hermes restored an
  existing session) and injects the convention;
- a later turn whose history no longer holds the convention (compaction) runs ``compaction`` and
  injects it again; Hermes keeps injected context in its history, so it is never added twice;
- ``on_session_end`` ends every turn: ``turn-end`` pushes in the background;
- ``on_session_finalize`` is a real exit: ``session-end`` schedules a full sync;
- delegated children get no convention and no sync.

Every hook fails open: a missing or failing ``dotbrain`` leaves the agent untouched.

Hermes runs this in its own environment: standard library only.
"""

import os
import posixpath
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
    lines = text.splitlines()
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


def _linked_manual(name):
    """SKILL.md of a manual-only skill in the checkout's or the Hermes home's ``skills/``, where
    dotbrain links private skills; the checkout wins, as in Hermes. None for any other skill."""
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        return None
    # ponytail: looks the skill up by directory name, which is how dotbrain links it.
    for root in (Path(_checkout()) / ".hermes" / "skills", _hermes_home() / "skills"):
        skill_md = root / name / "SKILL.md"
        if skill_md.is_file():
            fields = _frontmatter(skill_md.read_text(encoding="utf-8"))
            return skill_md if fields.get("disable-model-invocation", "").lower() == "true" else None
    return None


def manual_only_veto(manual):
    """A ``pre_tool_call`` hook that blocks the model from loading a manual-only skill.

    ``manual`` maps each packaged manual-only skill name to its SKILL.md path; an unnamespaced name
    is looked up among the linked private skills.
    """

    def veto(tool_name="", args=None, **_):
        if tool_name != "skill_view" or not isinstance(args, dict):
            return None
        namespace, _, name = str(args.get("name") or "").strip().lstrip("/").rpartition(":")
        skill_md = manual.get(name) if namespace == NAMESPACE else None if namespace else _linked_manual(name)
        if skill_md is not None and not _supporting_file(skill_md, args.get("file_path")):
            label = f"{namespace}:{name}" if namespace else name
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
