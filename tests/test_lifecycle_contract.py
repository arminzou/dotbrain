"""Lifecycle contracts through real Git metadata and disposable local checkouts."""
import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotbrain import adopter_repos, assets, beads, cursor, doctor, hermes, opencode, runtimes, workflows, subagents
from dotbrain.cli import app


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True)


@pytest.fixture
def lifecycle(tmp_path):
    home = tmp_path / 'home'
    home.mkdir()
    git(home, 'init')
    brainspace = home / 'brainspaces' / 'custom'
    brain = brainspace / '.brain'
    brain.mkdir(parents=True)
    (brain / 'project.yaml').write_text('agents: []\nskills: []\nbeads:\n  mode: none\n', encoding='utf-8')
    repo = tmp_path / 'main'
    repo.mkdir()
    git(repo, 'init')
    git(repo, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-m', 'seed')
    (brainspace / '.repo').write_text(str(repo), encoding='utf-8')
    (repo / '.brain').symlink_to(brain, target_is_directory=True)
    worktree = tmp_path / 'other-name'
    git(repo, 'worktree', 'add', '-b', 'worktree-test', str(worktree))
    return home, brainspace, repo, worktree


def test_wire_worktree_preserves_registration_and_declarations(lifecycle):
    home, brainspace, main, worktree = lifecycle
    (brainspace / '.repo.local').write_text(str(main), encoding='utf-8')
    before = {name: (brainspace / name).read_bytes() for name in ('.repo', '.repo.local', '.brain/project.yaml')}
    result = workflows.wire_project(dotbrain_home=home, repo=worktree)
    assert not result.errors
    assert result.project == 'custom'
    assert (worktree / '.brain').resolve() == brainspace / '.brain'
    assert not (worktree / '.beads').exists()
    assert {name: (brainspace / name).read_bytes() for name in before} == before
    assert sorted(p.name for p in (home / 'brainspaces').iterdir()) == ['custom']
    repeated = workflows.wire_project(dotbrain_home=home, repo=worktree)
    assert not repeated.errors
    assert repeated.logs == []


@pytest.mark.parametrize('linked_worktree', [True, False])
def test_wire_shared_maintenance_only_for_main_checkout(lifecycle, monkeypatch, linked_worktree):
    home, brainspace, main, worktree = lifecycle
    brain = brainspace / '.brain'
    (brain / 'project.yaml').write_text(
        'agents: [codex]\nskills: []\nbeads:\n  mode: embedded\n', encoding='utf-8'
    )
    (brainspace / '.beads').mkdir()
    convention = brain / 'DOTBRAIN.md'
    convention.write_text('previous convention\n', encoding='utf-8')
    before = {p.relative_to(brain): p.read_bytes() for p in brain.rglob('*') if p.is_file()}
    pulls = []

    def pull(dotbrain_home, *, projects, run):
        pulls.append(projects)
        return beads.BootstrapResult(logs=['tracker synced'])

    monkeypatch.setattr(workflows.beads, 'pull_beads_for_all', pull)
    checkout = worktree if linked_worktree else main
    result = workflows.wire_project(dotbrain_home=home, repo=checkout)

    assert not result.errors
    assert (checkout / '.brain').resolve() == brain
    assert (checkout / '.beads').resolve() == brainspace / '.beads'
    assert subagents.is_managed_copy(checkout / '.codex' / 'agents' / 'dotbrain-reviewer.toml')
    if linked_worktree:
        assert {p.relative_to(brain): p.read_bytes() for p in brain.rglob('*') if p.is_file()} == before
        assert pulls == []
    else:
        assert convention.read_text(encoding='utf-8') != 'previous convention\n'
        assert pulls == [['custom']]


@pytest.mark.parametrize('mode, synced, hinted', [
    ('embedded', False, True),
    ('embedded', True, False),
    ('none', False, False),
])
def test_wire_worktree_names_refresh_for_an_unsynced_tracker(lifecycle, monkeypatch, mode, synced, hinted):
    # A worktree attachment no longer pulls the tracker, so a main checkout attached with
    # --skip-beads (or a failed pull) leaves .beads missing; refresh is the recovery.
    home, brainspace, main, worktree = lifecycle
    (brainspace / '.brain' / 'project.yaml').write_text(
        f'agents: []\nskills: []\nbeads:\n  mode: {mode}\n', encoding='utf-8'
    )
    if synced:
        (brainspace / '.beads').mkdir()
    monkeypatch.setattr(workflows.beads, 'pull_beads_for_all',
                        lambda *a, **k: pytest.fail('a worktree attachment must not pull the tracker'))
    result = workflows.wire_project(dotbrain_home=home, repo=worktree)

    assert not result.errors
    hint = [w for w in result.warnings if 'dotbrain refresh' in w]
    assert bool(hint) is hinted, result.warnings
    if hinted:
        assert hint == ['shared tracker is not synced; run `dotbrain refresh` to sync it and attach .beads']


@pytest.mark.parametrize('problem', ['unwired', 'conflict', 'foreign'])
def test_wire_worktree_rejects_parent_conflicts_before_writes(lifecycle, problem, tmp_path):
    home, brainspace, main, worktree = lifecycle
    if problem in ('unwired', 'foreign'):
        (main / '.brain').unlink()
    if problem == 'foreign':
        foreign = tmp_path / 'foreign' / 'brainspaces' / 'custom' / '.brain'
        foreign.mkdir(parents=True)
        (main / '.brain').symlink_to(foreign, target_is_directory=True)
    before = sorted(str(p.relative_to(home)) for p in home.rglob('*'))
    with pytest.raises((ValueError, RuntimeError)):
        workflows.wire_project(dotbrain_home=home, repo=worktree, project='wrong' if problem == 'conflict' else None)
    assert sorted(str(p.relative_to(home)) for p in home.rglob('*')) == before
    assert not (worktree / '.brain').exists()


def test_detach_worktree_preserves_sibling_excludes_and_user_files(lifecycle):
    home, brainspace, main, worktree = lifecycle
    workflows.wire_project(dotbrain_home=home, repo=worktree)
    source = home / 'skills' / 'test'
    source.mkdir(parents=True)
    for checkout in (main, worktree):
        receiver = checkout / '.claude' / 'skills'
        receiver.mkdir(parents=True)
        (receiver / 'test').symlink_to(source, target_is_directory=True)
    agents = worktree / '.codex' / 'agents'
    agents.mkdir(parents=True)
    marked = agents / 'reviewer.toml'
    marked.write_text(subagents.GENERATED_NOTICE + '\n' + subagents.MANAGED_MARKER + '\n\nname = "reviewer"\n', encoding='utf-8')
    user = agents / 'mine.toml'
    user.write_text('name = "mine"\n', encoding='utf-8')
    empty = worktree / '.claude' / 'user-empty-directory'
    empty.mkdir()
    adopter_repos.reconcile_link_excludes(worktree, linked=['.claude/skills/test', '.codex/agents/reviewer.toml'])
    result = workflows.unwire_project(dotbrain_home=home, repo=worktree)
    assert not result.errors
    assert not (worktree / '.brain').exists()
    assert (main / '.brain').is_symlink()
    assert user.is_file() and not marked.exists()
    assert empty.is_dir()
    lines = adopter_repos.git_exclude_file(main).read_text().splitlines()
    assert '/.brain' in lines and '/.claude/skills/test' in lines
    assert '/.codex/agents/reviewer.toml' not in lines
    workflows.unwire_project(dotbrain_home=home, repo=main)
    lines = adopter_repos.git_exclude_file(main).read_text().splitlines()
    assert '/.brain' not in lines and '/.claude/skills/test' not in lines
    assert brainspace.is_dir()


def test_wire_and_unwire_cli_json_and_clean_break(lifecycle):
    home, brainspace, main, worktree = lifecycle
    runner = CliRunner()
    result = runner.invoke(app, ['wire', '--repo', str(worktree), '--home', str(home), '--json'])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)['targets'][0]['project'] == 'custom'
    result = runner.invoke(app, ['unwire', '--repo', str(worktree), '--home', str(home), '--json'])
    assert result.exit_code == 0, result.output
    for command, flag in [('wire', '--all'), ('wire', '--name'), ('unwire', '--archive'),
                          ('unwire', '--delete'), ('unwire', '--no-repo'), ('unwire', '--dry-run'),
                          ('unwire', '--all')]:
        result = runner.invoke(app, [command, flag, '--json'])
        assert result.exit_code == 2
        assert json.loads(result.stdout)['status'] == 'failure'


def test_submodule_git_file_is_not_a_linked_worktree(lifecycle, tmp_path):
    _, _, main, _ = lifecycle
    superproject = tmp_path / 'superproject'
    superproject.mkdir()
    git(superproject, 'init')
    git(superproject, '-c', 'protocol.file.allow=always', 'submodule', 'add', str(main), 'child')
    submodule = superproject / 'child'
    assert (submodule / '.git').is_file()
    assert adopter_repos.linked_worktree_parent(submodule) is None


def test_wire_registers_previously_brain_only_main_checkout(lifecycle):
    home, brainspace, main, _ = lifecycle
    (brainspace / '.repo').unlink()
    result = workflows.wire_project(dotbrain_home=home, repo=main)
    assert not result.errors
    assert Path((brainspace / '.repo').read_text().strip()).expanduser() == main


@pytest.mark.parametrize('problem', ['legacy', 'missing-skill', 'missing-agent'])
def test_wire_selection_failure_does_not_migrate_or_write(lifecycle, problem):
    home, brainspace, main, worktree = lifecycle
    declaration = brainspace / '.brain' / 'project.yaml'
    if problem == 'legacy':
        legacy = brainspace / '.brain' / 'agents' / 'skills.yaml'
        legacy.parent.mkdir()
        legacy.write_text('skills: []\n', encoding='utf-8')
    elif problem == 'missing-skill':
        declaration.write_text('agents: [codex]\nskills: [absent]\nbeads: {mode: none}\n', encoding='utf-8')
    else:
        declaration.write_text('agents: [codex]\nskills: []\nsubagents: [absent]\nbeads: {mode: none}\n', encoding='utf-8')
    before = declaration.read_bytes()
    result = CliRunner().invoke(app, ['wire', '--repo', str(worktree), '--home', str(home), '--json'])
    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout)['status'] == 'failure'
    assert declaration.read_bytes() == before
    assert not (worktree / '.brain').exists()
    assert not (home / '.gitignore').exists()


def test_runtime_with_skills_and_hooks_but_no_subagents(lifecycle, monkeypatch, tmp_path):
    # A runtime known only to this test: skills and hooks, no native subagents. 'later' stands for a
    # runtime a newer dotbrain sharing this home knows; every command warns about and skips it.
    monkeypatch.setitem(runtimes.RUNTIMES, 'skillsonly',
                        runtimes.Runtime('skillsonly', 'skillsonly', 'Skills Only', '.skillsonly', hooks=True))
    monkeypatch.setattr(workflows.beads, 'pull_beads_for_all', lambda *a, **k: beads.BootstrapResult())
    home, brainspace, main, worktree = lifecycle
    skill = home / 'skills' / 'one'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('# one\n', encoding='utf-8')
    (brainspace / '.brain' / 'project.yaml').write_text(
        'agents: [skillsonly, later]\nskills: [one]\nbeads:\n  mode: none\n', encoding='utf-8')
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    runner = CliRunner()

    def foreign(checkout):
        workspace = checkout / '.skillsonly'
        return {workspace / 'skills' / 'mine' / 'SKILL.md': 'mine', workspace / 'agents' / 'user.md': 'user'}

    for checkout in (main, worktree):
        entries = foreign(checkout)
        for path, text in entries.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')
        (checkout / '.skillsonly' / 'skills' / 'outside').symlink_to(elsewhere, target_is_directory=True)

        result = workflows.wire_project(dotbrain_home=home, repo=checkout)
        assert not result.errors, result.errors
        assert any(w.endswith(': later') for w in result.warnings), result.warnings
        delivered = checkout / '.skillsonly' / 'skills' / 'one'
        assert delivered.is_symlink() and delivered.resolve() == skill.resolve()
        assert not (checkout / '.later').exists()
        assert sorted(p.name for p in (checkout / '.skillsonly' / 'agents').iterdir()) == ['user.md']
        assert not workflows.wire_project(dotbrain_home=home, repo=checkout).logs

        refreshed = workflows.refresh_projects(home, cwd=checkout)
        assert not refreshed.errors and any(w.endswith(': later') for w in refreshed.warnings)
        assert not workflows.refresh_projects(home, cwd=checkout, runtime='skillsonly').errors
        for argv, code in ((['skills', 'link', '--runtime', 'skillsonly'], 0),
                           (['agents', 'link'], 0),
                           (['agents', 'link', '--runtime', 'skillsonly'], 1),
                           (['skills', 'link', '--runtime', 'later'], 2)):
            invoked = runner.invoke(app, [*argv, '--repo', str(checkout), '--home', str(home), '--json'])
            assert invoked.exit_code == code, (argv, invoked.output)
            assert code != 1 or 'no native subagent delivery' in invoked.output

        assert delivered.is_symlink() and (checkout / '.skillsonly' / 'skills' / 'outside').is_symlink()
        assert {path: path.read_text(encoding='utf-8') for path in entries} == entries
        report = doctor.run_doctor(home, home=tmp_path / 'user', cwd=checkout)
        findings = report.projects['custom']
        assert not [f.message for f in findings if f.status == 'error']
        assert any(f.status == 'warn' and f.message.endswith(': later') for f in findings)

    for kind in ('skills', 'agents'):
        for json_flag in (['--json'], []):
            listed = runner.invoke(app, [kind, 'list', '--project', 'custom', '--home', str(home), *json_flag])
            assert listed.exit_code == 0, listed.output
            assert 'ignored unknown agent workspace' in listed.output and ': later' in listed.output, listed.output
    unwired = runner.invoke(app, ['unwire', '--repo', str(worktree), '--home', str(home), '--json'])
    assert unwired.exit_code == 0, unwired.output
    assert any(f['message'].endswith(': later') for f in json.loads(unwired.stdout)['targets'][0]['findings'])
    assert not (worktree / '.skillsonly' / 'skills' / 'one').exists()
    assert (worktree / '.skillsonly' / 'skills' / 'mine' / 'SKILL.md').is_file()


@pytest.mark.parametrize('runtime', runtimes.RUNTIMES)
def test_refresh_preserves_undeclared_workspace_and_warns(lifecycle, monkeypatch, tmp_path, runtime):
    home, brainspace, main, worktree = lifecycle
    monkeypatch.setattr(workflows.beads, 'pull_beads_for_all', lambda *a, **k: beads.BootstrapResult())
    monkeypatch.setattr(Path, 'home', lambda: tmp_path / 'user')
    source = home / 'skills' / 'one'
    source.mkdir(parents=True)
    (source / 'SKILL.md').write_text('# one\n', encoding='utf-8')
    declaration = brainspace / '.brain/project.yaml'
    declaration.write_text(f'agents: [{runtime}]\nskills: [one]\nbeads: {{mode: none}}\n', encoding='utf-8')
    workspace = runtimes.find(runtime).workspace
    foreign = tmp_path / 'foreign'
    foreign.mkdir()
    for checkout in (main, worktree):
        assert not workflows.wire_project(dotbrain_home=home, repo=checkout).errors
        receiver = checkout / workspace / 'skills'
        assert (receiver / 'one').is_symlink()
        (receiver / 'mine').mkdir()
        (receiver / 'foreign').symlink_to(foreign, target_is_directory=True)
        (checkout / workspace / 'settings.json').write_text('{}', encoding='utf-8')

    before = {checkout: sorted(p.name for p in (checkout / workspace / 'skills').iterdir())
              for checkout in (main, worktree)}
    declaration.write_text('agents: []\nskills: [one]\nbeads: {mode: none}\n', encoding='utf-8')
    for checkout, sibling in ((worktree, main), (main, None)):
        result = workflows.refresh_projects(home, cwd=checkout)
        assert not result.errors
        receiver = checkout / workspace / 'skills'
        assert (receiver / 'one').is_symlink()
        assert sorted(p.name for p in receiver.iterdir()) == before[checkout]
        assert (receiver / 'foreign').resolve() == foreign.resolve()
        assert (checkout / workspace / 'settings.json').read_text() == '{}'
        assert not result.targets[0].data['checkout_changes']
        assert any(f['severity'] == 'warning' and f['message'] ==
                   f'{workspace} exists but {runtime} is not in agents:; dotbrain will not link project skills there'
                   for f in result.targets[0].findings)
        if sibling:
            assert (sibling / workspace / 'skills/one').is_symlink()
    assert f'/{workspace}/skills/one' in adopter_repos.git_exclude_file(main).read_text().splitlines()
    # Explicit removal still cleans dotbrain's links, including undeclared workspaces.
    assert not workflows.unwire_project(dotbrain_home=home, repo=main).errors
    assert not (main / workspace / 'skills/one').is_symlink()
    assert (main / workspace / 'skills/mine').is_dir()


def _refresh_prune_unwire_skills(lifecycle, runtime, delivery_home):
    home, brainspace, main, worktree = lifecycle
    workspace = runtimes.find(runtime).workspace

    def declare(selection):
        (brainspace / '.brain/project.yaml').write_text(
            f'agents: [{runtime}]\nskills: {selection}\nbeads:\n  mode: none\n', encoding='utf-8')

    def linked(checkout):
        return sorted(p.name for p in (checkout / workspace / 'skills').iterdir() if p.is_symlink())

    for selection, expected in (('[two]', ['two']), ('[]', []), ('[one, two]', ['one', 'two'])):
        declare(selection)
        for checkout, sibling in ((main, worktree), (worktree, main)):
            before = linked(sibling)
            assert not workflows.refresh_projects(home, cwd=checkout, runtime=runtime).errors
            assert linked(checkout) == expected and linked(sibling) == before
            for name in expected:
                assert (checkout / workspace / 'skills' / name).resolve() == (home / 'skills' / name).resolve()
            assert (checkout / workspace / 'skills/mine/SKILL.md').read_text(encoding='utf-8') == 'mine'

    for checkout, sibling in ((worktree, main), (main, None)):
        assert not workflows.unwire_project(dotbrain_home=home, repo=checkout).errors
        assert linked(checkout) == []
        assert (checkout / workspace / 'skills/mine/SKILL.md').read_text(encoding='utf-8') == 'mine'
        if sibling is not None:
            assert linked(sibling) == ['one', 'two']
        assert assets.HOME_DELIVERY[runtime].state(delivery_home) == 'current'


def test_hermes_project_skills_lifecycle(lifecycle, monkeypatch, tmp_path):
    # Hermes reads project skills from <checkout>/.hermes/skills once the checkout is trusted;
    # dotbrain links only its selection there and leaves everything else in that directory alone.
    monkeypatch.setattr(workflows.beads, 'pull_beads_for_all', lambda *a, **k: beads.BootstrapResult())
    home, brainspace, main, worktree = lifecycle
    skill = home / 'skills' / 'one'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('# one\n', encoding='utf-8')
    (brainspace / '.brain' / 'project.yaml').write_text(
        'agents: [hermes]\nskills: [one]\nbeads:\n  mode: none\n', encoding='utf-8')
    user = tmp_path / 'user'
    hermes_home = user / '.hermes'
    runner = CliRunner()

    for checkout in (main, worktree):
        mine = checkout / '.hermes' / 'skills' / 'mine' / 'SKILL.md'
        mine.parent.mkdir(parents=True)
        mine.write_text('mine', encoding='utf-8')
        result = workflows.wire_project(dotbrain_home=home, repo=checkout)
        assert not result.errors, result.errors
        delivered = checkout / '.hermes' / 'skills' / 'one'
        assert delivered.is_symlink() and delivered.resolve() == skill.resolve()
        assert not (checkout / '.hermes' / 'agents').exists()
        assert not workflows.refresh_projects(home, cwd=checkout, runtime='hermes').errors
        for argv, code in ((['skills', 'link', '--runtime', 'hermes'], 0),
                           (['agents', 'link', '--runtime', 'hermes'], 1)):
            invoked = runner.invoke(app, [*argv, '--repo', str(checkout), '--home', str(home), '--json'])
            assert invoked.exit_code == code, (argv, invoked.output)

        def hermes_warnings():
            report = doctor.run_doctor(home, home=user, cwd=checkout)
            return {f.message for f in report.projects['custom']
                    if f.status == 'warn' and f.message.startswith('hermes:')}

        (hermes_home / 'config.yaml').unlink(missing_ok=True)
        assert hermes_warnings() >= {'hermes: project skills load only from a trusted checkout'}
        assets.link_global(home, 'skills', 'hermes', user_home=user)
        (hermes_home / 'config.yaml').write_text(
            f'plugins:\n  enabled: [dotbrain]\nskills:\n  trusted_project_dirs: [{json.dumps(str(checkout))}]\n',
            encoding='utf-8')
        assert hermes_warnings() == set()
    assert hermes.state(hermes_home) == 'current'

    # Update, then prune, the shared selection; each refresh touches only its own checkout.
    two = home / 'skills' / 'two'
    two.mkdir(parents=True)
    (two / 'SKILL.md').write_text('# two\n', encoding='utf-8')

    _refresh_prune_unwire_skills(lifecycle, 'hermes', hermes_home)


def test_pi_project_skills_lifecycle(lifecycle, monkeypatch, tmp_path):
    # Pi reads project skills from <checkout>/.pi/skills once the checkout is trusted; dotbrain
    # links only its selection there and leaves everything else in that directory alone.
    monkeypatch.setattr(workflows.beads, 'pull_beads_for_all', lambda *a, **k: beads.BootstrapResult())
    home, brainspace, main, worktree = lifecycle
    for name in ('one', 'two'):
        (home / 'skills' / name).mkdir(parents=True)
        (home / 'skills' / name / 'SKILL.md').write_text(f'# {name}\n', encoding='utf-8')
    user = tmp_path / 'user'
    agent_dir = user / '.pi' / 'agent'

    def declare(selection):
        (brainspace / '.brain' / 'project.yaml').write_text(
            f'agents: [pi]\nskills: {selection}\nbeads:\n  mode: none\n', encoding='utf-8')

    def linked(checkout):
        return sorted(p.name for p in (checkout / '.pi' / 'skills').iterdir() if p.is_symlink())

    def pi_warnings(checkout):
        report = doctor.run_doctor(home, home=user, cwd=checkout)
        return {f.message for f in report.projects['custom'] if f.status == 'warn' and f.message.startswith('pi:')}

    declare('[one]')
    for checkout in (main, worktree):
        mine = checkout / '.pi' / 'skills' / 'mine' / 'SKILL.md'
        mine.parent.mkdir(parents=True)
        mine.write_text('mine', encoding='utf-8')
        assert not workflows.wire_project(dotbrain_home=home, repo=checkout).errors
        assert linked(checkout) == ['one']
        assert not (checkout / '.pi' / 'agents').exists()
        undelivered = {'pi: dotbrain extension is not delivered'} if checkout is main else set()
        assert pi_warnings(checkout) == {'pi: project skills load only from a trusted checkout'} | undelivered
        assets.link_global(home, 'skills', 'pi', user_home=user)
        (agent_dir / 'trust.json').write_text(json.dumps({str(checkout): True}), encoding='utf-8')
        assert pi_warnings(checkout) == set()

    _refresh_prune_unwire_skills(lifecycle, 'pi', agent_dir)


@pytest.mark.parametrize('other_runtime', [False, True])
def test_cursor_project_lifecycle(lifecycle, monkeypatch, tmp_path, other_runtime):
    monkeypatch.setattr(workflows.beads, 'pull_beads_for_all', lambda *a, **k: beads.BootstrapResult())
    user = tmp_path / 'user'
    monkeypatch.setattr(Path, 'home', lambda: user)
    home, brainspace, main, worktree = lifecycle
    # User-level hooks are installed separately from checkout-local skill delivery.
    assert not cursor.reconcile_hooks(user).warnings
    for name in ('one', 'two'):
        source = home / 'skills' / name
        source.mkdir(parents=True)
        (source / 'SKILL.md').write_text(f'---\nname: {name}\n---\nBody\n', encoding='utf-8')
        (source / 'support.md').write_text('support', encoding='utf-8')

    def declare(selection):
        agents = '[cursor, codex]' if other_runtime else '[cursor]'
        (brainspace / '.brain/project.yaml').write_text(
            f'agents: {agents}\nskills: {selection}\nbeads:\n  mode: none\n', encoding='utf-8')

    def selected(checkout):
        return set(cursor.discovered(checkout)) & {'one', 'two'}

    declare('[one]')
    for checkout in (main, worktree):
        foreign = checkout / '.cursor/skills/mine'
        foreign.mkdir(parents=True)
        (foreign / 'SKILL.md').write_text('mine', encoding='utf-8')
        assert not workflows.wire_project(dotbrain_home=home, repo=checkout).errors
        assert selected(checkout) == {'one'}
        assert not (checkout / '.cursor/agents').exists()
        assert (checkout / '.cursor/skills/one').exists() is not other_runtime
        assert all(len(found) == 1 for found in cursor.discovered(checkout).values())
        report = doctor.run_doctor(home, home=user, cwd=checkout)
        assert not [f for f in report.projects['custom'] if f.status in ('error', 'warn')], report.projects['custom']

    for selection, expected in (('[two]', {'two'}), ('[]', set())):
        declare(selection)
        for checkout, sibling in ((main, worktree), (worktree, main)):
            before = selected(sibling)
            assert not workflows.refresh_projects(home, cwd=checkout).errors
            assert selected(checkout) == expected
            assert selected(sibling) == before
            assert (checkout / '.cursor/skills/mine/SKILL.md').read_text() == 'mine'

    declare('[one, two]')
    for checkout in (main, worktree):
        assert not workflows.refresh_projects(home, cwd=checkout).errors
    for checkout, sibling in ((worktree, main), (main, None)):
        assert not workflows.unwire_project(dotbrain_home=home, repo=checkout).errors
        assert selected(checkout) == set()
        assert cursor.discovered(checkout) == {'mine': {(checkout / '.cursor/skills/mine').resolve()}}
        if sibling:
            assert selected(sibling) == {'one', 'two'}
        assert cursor.state(home) == 'current'


def test_unwire_preserves_foreign_cursor_cache_links(lifecycle, monkeypatch, tmp_path):
    home, brainspace, main, worktree = lifecycle
    monkeypatch.setattr(Path, 'home', lambda: tmp_path / 'user')
    (brainspace / '.brain/project.yaml').write_text(
        'agents: [cursor]\nskills: []\nbeads:\n  mode: none\n', encoding='utf-8')
    foreign = cursor.plugin_dir(home) / 'mine'
    foreign.mkdir(parents=True)
    (foreign / 'SKILL.md').write_text('mine', encoding='utf-8')
    for checkout in (main, worktree):
        receiver = checkout / '.cursor/skills'
        receiver.mkdir(parents=True)
        (receiver / 'mine').symlink_to(foreign, target_is_directory=True)
        result = workflows.wire_project(dotbrain_home=home, repo=checkout)
        assert any('not created by dotbrain' in error for error in result.errors)
        assert '/.cursor/skills/mine' not in adopter_repos.git_exclude_file(checkout).read_text()
        assert (receiver / 'mine').is_symlink()
    for checkout in (worktree, main):
        receiver = checkout / '.cursor/skills'
        assert not workflows.unwire_project(dotbrain_home=home, repo=checkout).errors
        assert (receiver / 'mine').is_symlink()
        assert (receiver / 'mine/SKILL.md').read_text() == 'mine'
    assert not cursor.owned(home)


def test_doctor_reports_undelivered_hermes_plugin_for_a_declaring_project(lifecycle, monkeypatch, tmp_path):
    home, brainspace, main, _ = lifecycle
    (brainspace / '.brain' / 'project.yaml').write_text('agents: [hermes]\nskills: []\nbeads:\n  mode: none\n',
                                                         encoding='utf-8')
    user = tmp_path / 'user'
    report = doctor.run_doctor(home, home=user, cwd=main)
    assert 'hermes: dotbrain plugin is not delivered' in {f.message for f in report.projects['custom']}
    foreign = hermes.plugin_dir(user / '.hermes')
    foreign.mkdir(parents=True)
    report = doctor.run_doctor(home, home=user, cwd=main)
    assert f'hermes: {foreign} is not dotbrain\'s plugin copy' in {f.message for f in report.projects['custom']}


def test_opencode_project_skills_lifecycle(lifecycle, monkeypatch, tmp_path):
    # OpenCode reads project skills from <checkout>/.opencode/skills; dotbrain links only its
    # selection there and leaves everything else in that directory alone.
    monkeypatch.setattr(workflows.beads, 'pull_beads_for_all', lambda *a, **k: beads.BootstrapResult())
    home, brainspace, main, worktree = lifecycle
    for name in ('one', 'two'):
        (home / 'skills' / name).mkdir(parents=True)
        (home / 'skills' / name / 'SKILL.md').write_text(f'# {name}\n', encoding='utf-8')

    def declare(selection):
        (brainspace / '.brain' / 'project.yaml').write_text(
            f'agents: [opencode]\nskills: {selection}\nbeads:\n  mode: none\n', encoding='utf-8')

    def linked(checkout):
        return sorted(p.name for p in (checkout / '.opencode' / 'skills').iterdir() if p.is_symlink())

    def clean(checkout):
        return git(checkout, 'status', '--porcelain', '--untracked-files=all').stdout == ''

    def opencode_files(checkout):
        # What OpenCode writes into every .opencode/ directory it scans.
        directory = checkout / '.opencode'
        (directory / '.gitignore').write_text('node_modules\npackage.json\npackage-lock.json\nbun.lock\n.gitignore',
                                              encoding='utf-8')
        (directory / 'package.json').write_text('{}', encoding='utf-8')
        (directory / 'node_modules' / 'x').mkdir(parents=True)
        (directory / 'node_modules' / 'x' / 'index.js').write_text('', encoding='utf-8')

    declare('[one]')
    user = tmp_path / 'user'
    runner = CliRunner()
    for checkout in (main, worktree):
        mine = checkout / '.opencode' / 'skills' / 'mine' / 'SKILL.md'
        mine.parent.mkdir(parents=True)
        mine.write_text('mine', encoding='utf-8')
        result = workflows.wire_project(dotbrain_home=home, repo=checkout)
        assert not result.errors, result.errors
        assert linked(checkout) == ['one']
        assert not (checkout / '.opencode' / 'agents').exists()
        for argv, code in ((['skills', 'link', '--runtime', 'opencode'], 0),
                           (['agents', 'link', '--runtime', 'opencode'], 1)):
            invoked = runner.invoke(app, [*argv, '--repo', str(checkout), '--home', str(home), '--json'])
            assert invoked.exit_code == code, (argv, invoked.output)
        (checkout / '.opencode' / 'skills' / 'mine').rename(tmp_path / f'aside-{checkout.name}')
        opencode_files(checkout)
        # Dotbrain's links are excluded one by one; OpenCode's own files ignore themselves.
        assert clean(checkout)
        (tmp_path / f'aside-{checkout.name}').rename(checkout / '.opencode' / 'skills' / 'mine')

        findings = doctor.run_doctor(home, home=user, cwd=checkout).projects['custom']
        delivered = (user / '.config' / 'opencode').exists()
        assert ('opencode: dotbrain plugin is not delivered' in {f.message for f in findings}) is not delivered
        assets.link_global(home, 'skills', 'opencode', user_home=user)
        findings = doctor.run_doctor(home, home=user, cwd=checkout).projects['custom']
        assert not [f.message for f in findings if f.status != 'ok' and f.message.startswith('opencode:')]

    # Update, then prune, the shared selection; each refresh touches only its own checkout.
    for selection, expected in (('[two]', ['two']), ('[]', [])):
        declare(selection)
        before = {checkout: linked(checkout) for checkout in (main, worktree)}
        for checkout, sibling in ((main, worktree), (worktree, main)):
            assert not workflows.refresh_projects(home, cwd=checkout, runtime='opencode').errors
            assert linked(checkout) == expected
            assert (checkout / '.opencode' / 'skills' / 'mine' / 'SKILL.md').read_text(encoding='utf-8') == 'mine'
            if checkout is main:
                assert linked(sibling) == before[sibling]

    # Removal: deliver a selection to both checkouts, then unwire one at a time.
    declare('[one, two]')
    for checkout in (main, worktree):
        assert not workflows.refresh_projects(home, cwd=checkout, runtime='opencode').errors
    for checkout, sibling in ((worktree, main), (main, None)):
        assert not workflows.unwire_project(dotbrain_home=home, repo=checkout).errors
        assert linked(checkout) == []
        assert (checkout / '.opencode' / 'skills' / 'mine' / 'SKILL.md').read_text(encoding='utf-8') == 'mine'
        assert (checkout / '.opencode' / 'package.json').is_file()
        if sibling is not None:
            assert linked(sibling) == ['one', 'two']
        # Project removal never touches the machine-wide delivery.
        assert opencode.state(user / '.config' / 'opencode') == 'current'
