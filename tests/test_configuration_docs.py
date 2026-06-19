import re
from pathlib import Path

import yaml

from dotbrain import config


def _extract_yaml_block(doc: str, heading: str) -> str:
    pattern = rf"## `{re.escape(heading)}`\n.*?```yaml\n(.*?)\n```"
    match = re.search(pattern, doc, re.DOTALL)
    assert match, f"missing YAML example for {heading}"
    return match.group(1)


def test_configuration_doc_examples_match_runtime_config(tmp_path: Path):
    doc = Path("docs/configuration.md").read_text()
    dotbrain_root = tmp_path / "dotbrain"
    project_root = dotbrain_root / "projects" / "demo"
    project_root.mkdir(parents=True)

    config_yaml = _extract_yaml_block(doc, "config.yaml")
    project_yaml = _extract_yaml_block(doc, "project.yaml")

    (dotbrain_root / "config.yaml").write_text(config_yaml + "\n")
    (project_root / "project.yaml").write_text(project_yaml + "\n")

    global_doc = yaml.safe_load(config_yaml)
    project_doc = yaml.safe_load(project_yaml)

    loaded_global = config.load_config(dotbrain_root)
    assert loaded_global.version == global_doc["version"]
    assert loaded_global.beads_server.host == global_doc["beads"]["server"]["host"]
    assert loaded_global.beads_server.port == global_doc["beads"]["server"]["port"]
    assert loaded_global.beads_server.user == global_doc["beads"]["server"]["user"]
    assert loaded_global.beads_server.ssh_host == global_doc["beads"]["server"]["ssh_host"]

    loaded_project = config.load_project_config(dotbrain_root, "demo")
    assert loaded_project.mode == project_doc["beads"]["mode"]
    assert loaded_project.remote == project_doc["beads"]["remote"]
    assert loaded_project.database == project_doc["beads"]["database"]

    assert config.load_project_agents(dotbrain_root, "demo") == tuple(project_doc["agents"])
    assert config.load_project_skills(dotbrain_root, "demo") == tuple(project_doc["skills"])
