from contextlib import asynccontextmanager
from dataclasses import dataclass
import inspect

from src.shared.http import build_timeout
from src.shared.repo_cache import RepoCacheStore
from src.shared.settings import HF_EXACT_NO_REPO_RECHECK_DAYS, REPO_CACHE_DB_PATH


@dataclass(frozen=True)
class RuntimeClients:
    session: object
    repo_cache: RepoCacheStore
    discovery_client: object
    github_client: object


def load_runtime_config(env: dict[str, str]) -> dict[str, str | int]:
    return {
        "github_token": (env.get("GITHUB_TOKEN") or "").strip(),
        "huggingface_token": (env.get("HUGGINGFACE_TOKEN") or "").strip(),
        "hf_exact_no_repo_recheck_days": _parse_positive_int(
            env.get("HF_EXACT_NO_REPO_RECHECK_DAYS"),
            default=HF_EXACT_NO_REPO_RECHECK_DAYS,
        ),
    }


def load_notion_config(env: dict[str, str]) -> dict[str, str | int]:
    config = load_runtime_config(env)
    notion_token = (env.get("NOTION_TOKEN") or "").strip()
    database_id = (env.get("DATABASE_ID") or "").strip()

    missing = []
    if not notion_token:
        missing.append("NOTION_TOKEN")
    if not database_id:
        missing.append("DATABASE_ID")

    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required environment variables: {joined}")

    return {
        **config,
        "notion_token": notion_token,
        "database_id": database_id,
    }


def build_client(factory, session, **kwargs):
    parameters = inspect.signature(factory).parameters.values()
    if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters):
        accepted_kwargs = kwargs
    else:
        accepted_names = {parameter.name for parameter in parameters}
        accepted_kwargs = {key: value for key, value in kwargs.items() if key in accepted_names}

    return factory(session, **accepted_kwargs)


@asynccontextmanager
async def open_runtime_clients(
    config: dict[str, str | int],
    *,
    session_factory,
    discovery_client_cls,
    github_client_cls,
    concurrent_limit: int,
    request_delay: float,
    github_min_interval: float | None = None,
):
    repo_cache = RepoCacheStore(REPO_CACHE_DB_PATH)

    try:
        async with session_factory(timeout=build_timeout()) as session:
            discovery_client = build_client(
                discovery_client_cls,
                session,
                huggingface_token=config["huggingface_token"],
                repo_cache=repo_cache,
                hf_exact_no_repo_recheck_days=config["hf_exact_no_repo_recheck_days"],
                max_concurrent=concurrent_limit,
                min_interval=request_delay,
            )
            github_client = build_client(
                github_client_cls,
                session,
                github_token=config["github_token"],
                max_concurrent=concurrent_limit,
                min_interval=github_min_interval if github_min_interval is not None else request_delay,
            )
            yield RuntimeClients(
                session=session,
                repo_cache=repo_cache,
                discovery_client=discovery_client,
                github_client=github_client,
            )
    finally:
        repo_cache.close()


def _parse_positive_int(raw_value, *, default: int) -> int:
    text = str(raw_value or "").strip()
    if not text:
        return default

    try:
        value = int(text)
    except ValueError:
        return default

    if value <= 0:
        return default
    return value
