from src.shared.runtime import load_notion_config


def load_config_from_env(env: dict[str, str]) -> dict[str, str | int]:
    return load_notion_config(env)
