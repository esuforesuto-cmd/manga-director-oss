from pathlib import Path

import pytest

from manga_director.cli.config import load_config, write_default_config
from manga_director.domain.exceptions import ConfigurationError


def test_config_yaml_exposes_the_required_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """default_image_generator: mock
default_llm_provider: mock
default_prompt_template: image_prompt.md
optimizer_enabled: false
validation_enabled: false
prompt_directory: prompts
log_level: DEBUG
repository:
  driver: local_file
  root: storage
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.default_image_generator == "mock"
    assert config.default_llm_provider == "mock"
    assert config.default_prompt_template == "image_prompt.md"
    assert config.optimizer_enabled is False
    assert config.validation_enabled is False
    assert config.prompt_directory == Path("prompts")
    assert config.log_level == "DEBUG"
    assert config.repository.driver == "local_file"
    assert config.repository.root == Path("storage")


def test_default_config_is_created_for_init(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"

    config = write_default_config(path)

    assert path.exists()
    assert load_config(path) == config


def test_invalid_config_returns_a_domain_error(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("repository: [not, an, object]", encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_config(path)
