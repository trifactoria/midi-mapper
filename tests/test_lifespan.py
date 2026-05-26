def test_app_uses_lifespan_without_legacy_event_handlers(app_module):
    assert app_module.app.router.lifespan_context is not None
    assert app_module.app.router.on_startup == []
    assert app_module.app.router.on_shutdown == []
