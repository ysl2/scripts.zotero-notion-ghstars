import pytest


FIXED_URL_EXPORT_TIMESTAMP = "20260326113045"


@pytest.fixture(autouse=True)
def fixed_url_export_timestamp(monkeypatch):
    try:
        import src.url_to_csv.filenames as filenames
    except ModuleNotFoundError:
        return

    monkeypatch.setattr(filenames, "current_run_timestamp", lambda: FIXED_URL_EXPORT_TIMESTAMP)
