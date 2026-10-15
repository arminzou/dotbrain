"""Written promotion guarantees and illustrative, dated contract examples.

These check the skill's contract and the consistency of acceptance fixtures, not native
agent execution, semantic equivalence judgments, or real PR delivery.
The hand-written examples below are not outputs produced by retro. Their arithmetic and
canary checks illustrate the written requirements; they are not deterministic behavior evidence.
"""

from pathlib import Path
import re

import pytest
import yaml


ROOT = Path("plugin/skills/retro")


def text(name):
    return " ".join((ROOT / name).read_text(encoding="utf-8").split())


@pytest.mark.parametrize("contracts", [
    ("trigger, required behavior", "enough rationale to stand alone", "ordinary clone",
     "Derive fresh public wording", "Private paths, Bead IDs, design/review identifiers",
     "private evidence", "including slash variants", "paraphrased private incident details",
     "Keep provenance only in `RETRO.md`"),
    ("at least three supported days", "Several observations on one day count once",
     "copied reviews and reruns add neither a day nor a rule", "Resolve finding redirects",
     "saved count and dates disagree", "do not invent dates"),
    ("Compare rules by trigger and required behavior", "proposals attached to other finding IDs",
     "Reuse an equivalent rule", "amend its section", "Several findings can share one proposal",
     "never overrides an established rule or acceptance criterion", "Hold a conflicting proposal"),
    ("before applying the edit", "promotion.status: pending", "compare the saved proposal",
     "If already present, reuse it", "never appends a second section",
     "A closed unmerged PR stays pending", "retains its prior revisions"),
    ("Reconcile recorded pending proposals even when capture has no changed evidence",
     "At most one bounded merge-state lookup per recorded PR per invocation",
     "do not scan all PR history", "merge watcher, polling hook, or background job",
     "no push, PR, merge, release, or publication authority"),
    ("--json state,mergedAt,mergeCommit,baseRefName,url", "git merge-base --is-ancestor",
     "ancestry exit 1", "other failures are gaps", "git show <target-oid>:RULES.md",
     "repository and base match", "observed on the target branch",
     "semantically equivalent reviewed amendment", "squash/rebase merge",
     "stale tracking ref", "A merged PR that dropped the rule is not adoption"),
    ("Approval alone", "PR closed unmerged never mark promotion",
     "Integration into a delivery branch never marks promotion", "ambiguous evidence",
     "actual merge timestamp", "not today's retrospective date", "commit-pinned URL",
     "A repeated reconciliation is a no-op", "target commit's date",
     "`RULES.md` is now the authority"),
    ("When `promotion.pr` is null", "one bounded read-only identification attempt per proposal",
     "git log -n 50 -S", "verifying the section against the saved public text/fingerprint",
     "gh api repos/<owner>/<repo>/commits/<sha>/pulls", "persist the identified PR in `promotion.pr`",
     "existing adoption checks below unchanged", "multiple ambiguous matches"),
    ("presence at a verified target OID establishes repository acceptance for reuse",
     "without a prior PR lookup", "that commit's date as `adopted_at`",
     "history action `reuse`", "never relabel a pending add/amend proposal as reuse"),
    ("clean checkout or worktree based on that recorded target branch",
     "Never edit `RULES.md` on an unrelated feature branch", "private patch fallback"),
    ("recheck a fixable hold's recorded condition once", "clear `hold`",
     "retry the same proposal", "requires the recorded human decision",
     "A held proposal that subsequently merges", "otherwise keep it pending",
     "A rejected or closed-unmerged PR remains pending", "new explicit human direction"),
])
def test_public_rule_promotion_guards(contracts):
    reference = text("references/promotion.md")
    for contract in contracts:
        assert contract in reference


def test_promotion_runs_after_checkpoint_even_without_new_capture():
    skill = text("SKILL.md")
    assert skill.index("### 4. Persist") < skill.index("### 5. Prepare") < skill.index("### 6. Report")
    for contract in ("references/promotion.md", "even when discovery skipped unchanged evidence",
                     "do not recapture evidence", "Promotion never advances capture cursors",
                     "clean checkout or worktree based on the recorded target branch",
                     "otherwise persist the patch privately", "unrelated feature branch"):
        assert contract in skill
    notebook = text("references/notebook.md")
    for contract in ("collecting | eligible | pending | promoted", "proposal_id", "public_patch",
                     "preserve unknown fields", "one canonical proposal", "proposal redirects",
                     "remain null until acceptance is verified", "evidence dates/counts",
                     "do not erase a public rule automatically", "Closed unmerged disposition remains pending"):
        assert contract in notebook
    for contract in ("clear the hold before retrying the same proposal", "new explicit human direction",
                     "accepted text resolves the hold", "that commit's date", "no prior PR is required",
                     "Persist a PR found by the bounded identification step"):
        assert contract in notebook


@pytest.fixture
def dated_notebook(tmp_path):
    path = tmp_path / "private" / "RETRO.md"
    path.parent.mkdir()
    # Independent events on one day; later reviews quote the first event, not new events.
    finding = {
        "finding_id": "f-fixture",
        "evidence": [
            {"occurrence_id": "a", "date": "2026-04-01", "counted": True,
             "aliases": ["private-item-canary-72", "private-review-canary-91"],
             "locator": "/private-canary/cache", "design": "private-design-canary-63"},
            {"occurrence_id": "b", "date": "2026-04-01", "counted": True},
            {"occurrence_id": "c", "date": "2026-04-02", "counted": True},
            {"occurrence_id": "d", "date": "2026-04-03", "counted": True},
            {"occurrence_id": "review-copy", "date": "2026-04-04", "counted": False},
        ],
        "promotion": {"status": "pending", "proposal_id": "p-fixture",
                      "destination": None, "adopted_at": None},
    }
    path.write_text(yaml.safe_dump(finding), encoding="utf-8")
    return path


@pytest.mark.parametrize("through,days", [(2, 1), (3, 2), (4, 3), (5, 3)])
def test_written_contract_dated_examples(dated_notebook, through, days):
    """Illustrate unique-day arithmetic; this does not invoke capture or promotion."""
    finding = yaml.safe_load(dated_notebook.read_text(encoding="utf-8"))
    evidence = finding["evidence"][:through]
    dates = sorted({event["date"] for event in evidence if event["counted"]})
    assert len(dates) == days
    assert (len(dates) >= 3) == (through >= 4)
    # Reviewing the same saved evidence again cannot increment the derived count.
    assert dates == sorted({event["date"] for event in evidence * 2 if event["counted"]})
    assert "`evidence_dates` is the unique set of supported evidence days" in text("references/promotion.md")
    assert "For each eligible finding with at least three supported days" in text("references/promotion.md")
    assert "Automatically prepare one standalone root `RULES.md` change" in text("SKILL.md")


def test_written_contract_public_wording_example(tmp_path, dated_notebook):
    """Check a hand-written safe wording example, not an automated derivation or reuse."""
    public = tmp_path / "public"
    public.mkdir()
    rules = public / "RULES.md"
    rules.write_text(
        "# Repository rules\n\n## Verify destructive targets\n\n"
        "Before deleting a generated directory, resolve its absolute path and verify it is\n"
        "inside the intended output root. Stop if the target escapes that root. This keeps\n"
        "a malformed output path from deleting unrelated files.\n", encoding="utf-8",
    )
    # A safe proposal contains actionable context and rationale, without incident provenance.
    notebook = yaml.safe_load(dated_notebook.read_text(encoding="utf-8"))
    notebook["promotion"]["public_text"] = rules.read_text(encoding="utf-8")
    notebook["promotion"]["section"] = "RULES.md#verify-destructive-targets"
    dated_notebook.write_text(yaml.safe_dump(notebook), encoding="utf-8")
    candidate = rules.read_text(encoding="utf-8")
    for canary in ("private-item-canary-72", "private-review-canary-91", "private-design-canary-63",
                   "/private-canary/cache", "f-fixture", "p-fixture"):
        assert canary not in candidate
        assert canary in dated_notebook.read_text(encoding="utf-8")
    assert all(word in candidate for word in ("Before", "verify", "This keeps"))
    # The reuse fixture is the same section, not a second copy with a new heading.
    assert candidate.count("## Verify destructive targets") == 1
    assert notebook["promotion"]["public_text"] == candidate
    assert "Search both accepted rules and prepared changes" in text("references/promotion.md")
    assert "Keep provenance only in `RETRO.md`" in text("references/promotion.md")


@pytest.mark.parametrize("classification,pr,expected", [
    ("pending", {"state": "OPEN", "mergedAt": None}, "pending"),
    ("approved", {"state": "OPEN", "reviewDecision": "APPROVED", "mergedAt": None}, "pending"),
    ("closed_unmerged", {"state": "CLOSED", "mergedAt": None}, "pending"),
    ("merged_wrong_target", {"state": "MERGED", "baseRefName": "delivery"}, "pending"),
    ("merged_rule_missing", {"state": "MERGED", "rule_present": False}, "pending"),
    ("merged_unverified", {"state": "MERGED", "target_reachable": False}, "pending"),
    ("verified", {"state": "MERGED", "baseRefName": "main", "rule_present": True,
                  "target_reachable": True, "mergedAt": "2026-04-05T12:00:00Z",
                  "mergeCommit": {"oid": "a" * 40}}, "promoted"),
    ("reuse_verified", {"target_oid": "b" * 40, "equivalent_section_present": True,
                        "commit_date": "2026-04-01T12:00:00Z", "pr": None}, "promoted"),
])
def test_written_acceptance_state_table_examples(tmp_path, classification, pr, expected):
    """Assert the skill's declared table; fixtures do not classify actual hosting responses."""
    reference = (ROOT / "references/promotion.md").read_text(encoding="utf-8")
    block = re.search(r"```yaml\n(.*?)```", reference, re.S).group(1)
    states = yaml.safe_load(block)["acceptance_states"]
    fixture = tmp_path / "pr.yaml"
    fixture.write_text(yaml.safe_dump({"classification": classification, "pr": pr}), encoding="utf-8")
    observed = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    assert states[observed["classification"]] == expected
    assert "Apply this decision table only after those checks" in text("references/promotion.md")


@pytest.mark.parametrize("path", ["docs/skills.md", "docs/zh/skills.md", "plugin/skills/README.md"])
def test_retro_catalog_mentions_public_edit_and_read_only_reconciliation(path):
    catalog = Path(path).read_text(encoding="utf-8")
    paragraph = next(part for part in catalog.split("\n- ") if "`retro`" in part or "[retro]" in part)
    assert "RULES.md" in paragraph
    assert "PR" in paragraph
    assert "read-only" in paragraph or "只读" in paragraph
