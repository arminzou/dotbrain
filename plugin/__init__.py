"""Hermes entry point for the dotbrain plugin.

Registers each skill under ``skills/`` from its own SKILL.md, so supporting files stay next to it,
and keeps explicit-only skills manual: Hermes ignores ``disable-model-invocation``, so a
``pre_tool_call`` veto refuses the model's own ``skill_view`` of them while the user's
``/dotbrain:<skill>`` command, which loads the skill without a tool call, still works.

Hermes runs this in its own environment: standard library only.
"""

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


def manual_only_veto(manual):
    """A ``pre_tool_call`` hook that blocks the model from loading a manual-only skill."""

    def veto(tool_name="", args=None, **_):
        # A supporting-file read (file_path) belongs to a skill the user already invoked.
        if tool_name != "skill_view" or not isinstance(args, dict) or args.get("file_path"):
            return None
        namespace, _, name = str(args.get("name") or "").strip().lstrip("/").rpartition(":")
        if namespace == NAMESPACE and name in manual:
            return {"action": "block",
                    "message": f"{NAMESPACE}:{name} runs only when the user invokes /{NAMESPACE}:{name}."}
        return None

    return veto


def register(ctx):
    manual = set()
    for name, skill_md, fields in skills():
        ctx.register_skill(name, skill_md, description=fields.get("description", ""), frontmatter=fields)
        if fields.get("disable-model-invocation", "").lower() == "true":
            manual.add(name)
    if manual:
        ctx.register_hook("pre_tool_call", manual_only_veto(manual))
    # Session hooks are not registered yet; they belong here, beside the skills.
