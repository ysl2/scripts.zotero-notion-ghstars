def test_runtime_modules_are_available_under_src_layout():
    import src.app  # noqa: F401
    import src.csv_update.runner  # noqa: F401
    import src.notion_sync.runner  # noqa: F401
    import src.shared.runtime  # noqa: F401
    import src.url_to_csv.sources  # noqa: F401


def test_root_main_exposes_src_app_main():
    import main
    import src.app

    assert main.main is src.app.main
