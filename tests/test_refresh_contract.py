"""Existing-project maintenance, preservation and per-target outcomes."""
import json
import subprocess

import pytest
import yaml
from typer.testing import CliRunner

from dotbrain import assets, beads, brainspaces, config, doctor, opencode, paths, projects, runtimes, workflows
from dotbrain.cli import app


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True)


def project(home, checkout, name='custom', agents='[]'):
    brainspace = home / 'brainspaces' / name
    brain = brainspace / '.brain'
    brain.mkdir(parents=True)
    declaration = f'# Preserve this comment\nversion: 2\nagents: {agents}\nskills: []\nbeads: {{mode: none}}\ncustom: [a, b]\n'
    (brain / 'project.yaml').write_text(declaration, encoding='utf-8')
    (brain / 'AGENTS.md').write_text('User instructions\n', encoding='utf-8')
    brainspaces.seed_brain(brainspace, home)
    if checkout is not None:
        checkout.mkdir()
        git(checkout, 'init')
        (checkout / '.brain').symlink_to(brain, target_is_directory=True)
        (brainspace / '.repo').write_text(str(checkout), encoding='utf-8')
    else:
        (brainspace / '.repo').write_text('(brain-only)', encoding='utf-8')
    return brainspace


@pytest.fixture
def setup(tmp_path):
    home = tmp_path / 'home'
    home.mkdir()
    git(home, 'init')
    checkout = tmp_path / 'different-name'
    brainspace = project(home, checkout)
    return home, brainspace, checkout


@pytest.mark.parametrize('set_up', [False, True])
@pytest.mark.parametrize('cli_installed', [False, True])
@pytest.mark.parametrize('agents', [None, '[]', '[hermes]', '[codex]', '[claude, codex]', '[claude, codex, opencode]', '[codex, claude]'])
def test_refresh_follows_machine_only_without_agents_and_notices_old_defaults(setup, monkeypatch, tmp_path, set_up, cli_installed, agents):
    home, brainspace, checkout = setup
    monkeypatch.setattr(runtimes, 'installed', lambda rt: cli_installed and rt.name in ('claude', 'codex'))
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'config'))
    runtime_home = runtimes.user_dir(runtimes.find('opencode'), tmp_path / 'user-home')
    if set_up:
        assert not opencode.deliver(runtime_home).warnings
    declaration = brainspace / '.brain/project.yaml'
    content = 'version: 2\nskills: [sample]\nbeads: {mode: none}\n'
    if agents is not None:
        content += f'agents: {agents}\n'
    declaration.write_text(content, encoding='utf-8')
    source = home / 'skills/sample'
    source.mkdir(parents=True)
    (source / 'SKILL.md').write_text('sample', encoding='utf-8')
    before = declaration.read_bytes()

    result = CliRunner().invoke(app, ['refresh', '--project', 'custom', '--home', str(home), '--json'])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)['targets'][0]
    expected_link = (set_up if agents is None else 'opencode' in agents)
    assert (checkout / '.opencode/skills/sample').is_symlink() == expected_link
    expected_agents = (['claude', 'codex'] if cli_installed else []) + (['opencode'] if set_up else [])
    if agents is not None:
        expected_agents = yaml.safe_load(agents)
    for rt in runtimes.RUNTIMES.values():
        assert (checkout / rt.workspace).exists() == (rt.name in expected_agents)
    assert declaration.read_bytes() == before
    notices = [f for f in report['findings'] if 'follow the machine' in f['message']]
    assert bool(notices) == (set_up and agents == '[claude, codex]')
    if notices:
        assert len(notices) == 1 and notices[0]['severity'] == 'warning'
        assert 'custom: opencode' in notices[0]['message']
        assert 'add to agents: or delete the agents: list' in notices[0]['message']
    target = projects.ProjectTarget('custom', brainspace, checkout)
    expected_workspaces = assets.project_workspaces(home, target, 'all')
    assert brainspaces.active_agent_workspaces(brainspace, home) == expected_workspaces
    assert projects.inspect_project(home, target)['runtimes'] == [runtimes.for_workspace(ws).name for ws in expected_workspaces]
    checked = set()

    def check_assets(root, receiver, selected, kind, runtime):
        checked.add(receiver.parent.name)
        return []

    monkeypatch.setattr(doctor, '_check_assets', check_assets)
    doctor._check_project(target, home, run=workflows._default_run)
    expected_receivers = set(expected_workspaces)
    if '.codex' in expected_receivers:
        expected_receivers.add('.agents')
    assert checked == expected_receivers
    assert not workflows.unwire_project(dotbrain_home=home, repo=checkout).errors
    assert all(not (checkout / ws / 'skills/sample').is_symlink() for ws in expected_workspaces)


def test_nested_worktree_refresh_preserves_shared_identity_and_repeats(setup, tmp_path, monkeypatch):
    home, brainspace, main = setup
    git(main, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-m', 'seed')
    worktree = tmp_path / 'worktree'
    git(main, 'worktree', 'add', '-b', 'test', str(worktree))
    workflows.wire_project(dotbrain_home=home, repo=worktree)
    nested = worktree / 'nested'
    nested.mkdir()
    monkeypatch.chdir(nested)
    registration = (brainspace / '.repo').read_bytes()
    result = CliRunner().invoke(app, ['refresh', '--home', str(home), '--json'])
    assert result.exit_code == 0, result.output
    target = json.loads(result.stdout)['targets'][0]
    assert target['project'] == 'custom' and target['checkout'] == str(worktree)
    assert target['changes'] == []
    assert (brainspace / '.repo').read_bytes() == registration
    assert set(target['data']) == {'shared_brain_changes', 'shared_tracker_changes', 'checkout_changes'}


def test_refresh_only_designated_conventions_preserves_user_bytes(setup):
    home, brainspace, checkout = setup
    brain = brainspace / '.brain'
    authored = ['AGENTS.md', 'project.yaml', 'CONTEXT.md', 'docs/sub/README.md', 'docs/sub/DOTBRAIN.md',
                'site/site.yaml', 'site/index.md', 'adr/decision.md']
    for relative in authored:
        path = brain / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative not in ('AGENTS.md', 'project.yaml'):
            path.write_text(f'Authored {relative}\n', encoding='utf-8')
    before = {relative: (brain / relative).read_bytes() for relative in authored}
    for relative in ('DOTBRAIN.md', 'docs/README.md', 'site/configure.md'):
        (brain / relative).write_text('old managed\n', encoding='utf-8')
    result = workflows.refresh_project(home, 'custom')
    assert not result.errors
    assert {relative: (brain / relative).read_bytes() for relative in authored} == before
    assert set(result.targets[0].data['shared_brain_changes']) == {'DOTBRAIN.md', 'docs/README.md', 'site/configure.md'}
    assert workflows.refresh_project(home, 'custom').logs == []


@pytest.mark.parametrize('problem', ['legacy', 'missing-source', 'foreign-receiver'])
def test_preflight_preserves_workspace_links_and_conventions(setup, tmp_path, problem):
    home, brainspace, checkout = setup
    brain = brainspace / '.brain'
    (brain / 'project.yaml').write_text('agents: [codex]\nskills: []\nbeads: {mode: none}\n', encoding='utf-8')
    workspace = brainspace / '.codex'
    workspace.mkdir()
    (checkout / '.codex').symlink_to(workspace, target_is_directory=True)
    if problem == 'legacy':
        legacy = brain / 'agents' / 'skills.yaml'
        legacy.parent.mkdir()
        legacy.write_text('skills: []\n', encoding='utf-8')
    elif problem == 'missing-source':
        (brain / 'project.yaml').write_text('agents: [codex]\nskills: [missing]\nbeads: {mode: none}\n', encoding='utf-8')
    else:
        outside = tmp_path / 'outside'
        outside.mkdir()
        (workspace / 'skills').symlink_to(outside, target_is_directory=True)
    (brain / 'DOTBRAIN.md').write_text('old\n', encoding='utf-8')
    declaration = (brain / 'project.yaml').read_bytes()
    result = workflows.refresh_project(home, 'custom')
    assert result.errors
    assert (checkout / '.codex').is_symlink()
    assert (brain / 'DOTBRAIN.md').read_text() == 'old\n'
    assert (brain / 'project.yaml').read_bytes() == declaration


def test_owned_workspace_migrates_and_undeclared_runtime_rejected_before_writes(setup):
    home, brainspace, checkout = setup
    brain = brainspace / '.brain'
    (brain / 'project.yaml').write_text('agents: [codex]\nskills: []\nbeads: {mode: none}\n', encoding='utf-8')
    (brainspace / '.codex').mkdir()
    (checkout / '.codex').symlink_to(brainspace / '.codex', target_is_directory=True)
    with pytest.raises(ValueError, match='not declared'):
        workflows.refresh_project(home, 'custom', runtime='claude')
    assert (checkout / '.codex').is_symlink()
    result = workflows.refresh_project(home, 'custom', runtime='codex')
    assert not result.errors
    assert not (checkout / '.codex').is_symlink()
    assert (checkout / '.codex' / 'agents' / 'dotbrain-reviewer.toml').is_file()
    assert workflows.refresh_project(home, 'custom', runtime='codex').logs == []


def test_partial_batch_propagates_tracker_failure_and_continues(setup, tmp_path, monkeypatch):
    home, brainspace, _ = setup
    project(home, tmp_path / 'second', name='second')
    calls = []

    def sync(root, *, projects, run):
        calls.extend(projects)
        return beads.BootstrapResult(errors=['tracker unavailable']) if projects == ['custom'] else beads.BootstrapResult()

    monkeypatch.setattr(workflows.beads, 'pull_beads_for_all', sync)
    result = CliRunner().invoke(app, ['refresh', '--all', '--home', str(home), '--json'])
    assert result.exit_code == 1, result.output
    report = json.loads(result.stdout)
    assert report['status'] == 'partial'
    assert calls == ['custom', 'second']
    assert report['targets'][0]['errors'] == ['tracker unavailable']
    assert report['targets'][1]['status'] == 'success'


def test_invalid_or_missing_selection_never_creates_setup(setup):
    home, _, _ = setup
    for arguments in (['--project', 'absent'], ['--project', 'custom', '--all'], ['--name', 'custom'],
                      ['--repo-base', str(home)], ['--dry-run']):
        result = CliRunner().invoke(app, ['refresh', '--home', str(home), '--json', *arguments])
        assert result.exit_code == 2, result.output
        assert json.loads(result.stdout)['status'] == 'failure'
    assert sorted(p.name for p in (home / 'brainspaces').iterdir()) == ['custom']


def test_missing_brain_fails_without_recreating_it(setup):
    home, brainspace, _ = setup
    missing = home / 'brainspaces' / 'missing'
    missing.mkdir()
    result = workflows.refresh_project(home, 'missing')
    assert result.errors and not (missing / '.brain').exists()


def test_brain_only_named_refresh_is_valid_and_repeatable(setup, tmp_path):
    home, _, _ = setup
    project(home, None, name='brain-only')
    result = workflows.refresh_project(home, 'brain-only')
    assert not result.errors
    assert result.targets[0].checkout is None
    assert workflows.refresh_project(home, 'brain-only').logs == []


def test_actual_remote_pull_is_reported_as_shared_tracker_change(setup, monkeypatch):
    home, _, _ = setup
    monkeypatch.setattr(workflows.beads, 'pull_beads_for_all', lambda *args, **kwargs:
                        beads.BootstrapResult(targets=[{'status': 'success', 'changes': ['pulled configured remote example']}]))
    result = workflows.refresh_project(home, 'custom')
    assert not result.errors
    assert result.targets[0].data['shared_tracker_changes'] == ['pulled configured remote example']
    assert 'shared tracker: pulled configured remote example' in result.logs


def test_batch_malformed_project_yaml_does_not_stop_independent_targets(setup, tmp_path):
    home, _, _ = setup
    second = project(home, tmp_path / 'second', name='second')
    (second / '.brain' / 'project.yaml').write_text('agents: [broken', encoding='utf-8')
    result = workflows.refresh_projects(home, all_projects=True)
    assert result.refreshed == ['custom']
    assert result.targets[1].status == 'failure'
    assert result.targets[1].errors


def test_failed_tracker_after_shared_update_is_partial(setup, monkeypatch):
    home, brainspace, _ = setup
    (brainspace / '.brain' / 'DOTBRAIN.md').write_text('old\n', encoding='utf-8')
    monkeypatch.setattr(workflows.beads, 'pull_beads_for_all', lambda *args, **kwargs:
                        beads.BootstrapResult(errors=['tracker unavailable']))
    result = CliRunner().invoke(app, ['refresh', '--project', 'custom', '--home', str(home), '--json'])
    assert result.exit_code == 1
    report = json.loads(result.stdout)
    assert report['status'] == 'partial'
    assert report['targets'][0]['status'] == 'partial'
    assert report['targets'][0]['changes'] == ['shared Brain: updated DOTBRAIN.md']


def test_managed_convention_parent_symlink_preserves_user_content_before_writes(setup):
    home, brainspace, _ = setup
    brain = brainspace / '.brain'
    (brain / 'docs').rename(brain / 'original-docs')
    knowledge = brain / 'knowledge'
    knowledge.mkdir()
    authored = knowledge / 'README.md'
    authored.write_text('User-authored content\n', encoding='utf-8')
    (brain / 'docs').symlink_to(knowledge, target_is_directory=True)
    (brain / 'DOTBRAIN.md').write_text('Old convention\n', encoding='utf-8')
    result = workflows.refresh_project(home, 'custom')
    assert result.errors
    assert result.logs == []
    assert authored.read_text() == 'User-authored content\n'
    assert (brain / 'DOTBRAIN.md').read_text() == 'Old convention\n'


def test_batch_skips_checkout_on_another_machine_but_refreshes_shared_brain(setup, tmp_path):
    home, _, _ = setup
    second = project(home, tmp_path / 'elsewhere', name='second')
    (tmp_path / 'elsewhere').rename(tmp_path / 'gone')
    (second / '.brain' / 'DOTBRAIN.md').write_text('old\n', encoding='utf-8')
    result = CliRunner().invoke(app, ['refresh', '--all', '--home', str(home), '--json'])
    assert result.exit_code == 0, result.output
    target = json.loads(result.stdout)['targets'][1]
    assert target['status'] == 'success'
    assert target['data']['shared_brain_changes'] == ['DOTBRAIN.md']
    assert any('not on this machine' in f['message'] for f in target['findings'])
    assert not (tmp_path / 'elsewhere').exists()


@pytest.mark.parametrize('local_override', [False, True])
def test_absent_checkout_still_fails_when_named_or_overridden(setup, tmp_path, local_override):
    home, _, _ = setup
    second = project(home, tmp_path / 'elsewhere', name='second')
    (tmp_path / 'elsewhere').rename(tmp_path / 'gone')
    if local_override:
        (second / '.repo.local').write_text(str(tmp_path / 'missing-local'), encoding='utf-8')
        result = workflows.refresh_projects(home, all_projects=True)
        assert result.targets[1].status == 'failure'
    else:
        result = workflows.refresh_project(home, 'second')
    assert any('registered checkout is missing' in e for e in result.errors)


def test_filtered_batch_isolates_invalid_config_and_continues(setup, tmp_path):
    home, brainspace, _ = setup
    (brainspace / '.brain' / 'project.yaml').write_text('agents: [codex]\nbeads: {mode: none}\n', encoding='utf-8')
    second = project(home, tmp_path / 'second', name='second')
    (second / '.brain' / 'project.yaml').write_text('agents: [broken', encoding='utf-8')
    result = workflows.refresh_projects(home, all_projects=True, runtime='codex')
    assert result.refreshed == ['custom']
    assert result.targets[1].status == 'failure'
    assert result.targets[1].errors


def test_filtered_batch_undeclared_runtime_rejected_before_any_writes(setup, tmp_path):
    home, brainspace, _ = setup
    (brainspace / '.brain' / 'project.yaml').write_text('agents: [codex]\nbeads: {mode: none}\n', encoding='utf-8')
    project(home, tmp_path / 'second', name='second', agents='[claude]')
    (brainspace / '.brain' / 'DOTBRAIN.md').write_text('Old convention\n', encoding='utf-8')
    with pytest.raises(ValueError, match='not declared'):
        workflows.refresh_projects(home, all_projects=True, runtime='codex')
    assert (brainspace / '.brain' / 'DOTBRAIN.md').read_text() == 'Old convention\n'


def test_refresh_upgrades_unversioned_declaration_once_preserving_lines(setup):
    home, brainspace, _ = setup
    declaration = brainspace / '.brain' / 'project.yaml'
    before = '# Preserve this comment\nagents: []\nbeads: {mode: none}  # trailing\n'
    declaration.write_text(before, encoding='utf-8')
    result = workflows.refresh_project(home, 'custom')
    assert not result.errors
    after = declaration.read_text(encoding='utf-8')
    assert after.startswith(before)
    assert yaml.safe_load(after[len(before):]) == {'version': 2, 'packaged-subagents': list(config.PACKAGED_ROLES)}
    assert any('packaged-subagents' in line for line in result.logs)
    second = workflows.refresh_project(home, 'custom')
    assert declaration.read_text(encoding='utf-8') == after
    assert not any('packaged-subagents' in line for line in second.logs)


def test_refresh_never_modifies_version_two_declaration(setup):
    home, brainspace, _ = setup
    declaration = brainspace / '.brain' / 'project.yaml'
    declaration.write_text('# mine\nversion: 2\nbeads: {mode: none}\n', encoding='utf-8')
    assert not workflows.refresh_project(home, 'custom').errors
    assert declaration.read_text(encoding='utf-8') == '# mine\nversion: 2\nbeads: {mode: none}\n'


@pytest.mark.parametrize('text', ['version: 2\npackaged-subagents: [nope]\n', '[not, a, mapping]\n',
                                  'null\n', '~\n', '', '# only a comment\n'])
def test_refresh_rejects_bad_packaged_record_naming_roles(setup, text):
    home, brainspace, _ = setup
    declaration = brainspace / '.brain' / 'project.yaml'
    declaration.write_bytes(text.encode())
    result = workflows.refresh_project(home, 'custom')
    assert any('researcher, reviewer, verifier, worker' in error for error in result.errors)
    assert declaration.read_bytes() == text.encode()


@pytest.mark.parametrize('text', [
    b'# keep\r\nagents: []\r\nbeads: {mode: none}\r\n',
    b'agents: []\nbeads: {mode: none}',
    b'agents: []\nbeads: {mode: none}\ncustom: |+\n  keep\n',
])
def test_refresh_upgrade_keeps_line_endings_and_values(setup, text):
    home, brainspace, _ = setup
    declaration = brainspace / '.brain' / 'project.yaml'
    declaration.write_bytes(text)
    assert not workflows.refresh_project(home, 'custom').errors
    after = declaration.read_bytes()
    assert after.startswith(text)
    assert (b'\r\n' in text) == (after.count(b'\n') == after.count(b'\r\n'))
    expected = {**yaml.safe_load(text), 'version': 2, 'packaged-subagents': list(config.PACKAGED_ROLES)}
    assert yaml.safe_load(after) == expected


@pytest.mark.parametrize('text', [
    b'{agents: [], beads: {mode: none}}\n',
    b'agents: []\nbeads: {mode: none}\n...\n',
    b'  agents: []\n  beads: {mode: none}\n',
    b'agents: []\nbeads: {mode: none}\nloop: &loop [*loop]\n',
    b'agents: []\nbeads: &b {mode: none}\ncopy: *b\n',
    b'agents: []\nbeads: {mode: none}\nbase: {x: 1}\nmerged:\n  <<: {x: 2}\n',
])
def test_refresh_refuses_upgrade_that_would_change_the_declaration(setup, text):
    home, brainspace, _ = setup
    declaration = brainspace / '.brain' / 'project.yaml'
    declaration.write_bytes(text)
    result = workflows.refresh_project(home, 'custom')
    assert any('cannot append the packaged-subagents record' in error for error in result.errors)
    assert not any('upgraded' in line for line in result.logs)
    assert declaration.read_bytes() == text
