import os

from app.core.config import get_settings


def test_celery_config_uses_redis_env():
    # Default compose uses redis:6379 via service name; host override via env uses localhost
    os.environ.pop("CELERY_BROKER_URL", None)
    os.environ.pop("CELERY_RESULT_BACKEND", None)
    get_settings.cache_clear()
    from app.worker.celery_app import celery_app
    import app.worker.tasks  # noqa: F401 — ensure registration

    settings = get_settings()
    assert "redis" in celery_app.conf.broker_url
    assert "redis" in celery_app.conf.result_backend
    # ensure include tasks registered
    assert "ping" in celery_app.tasks

    # direct call without broker (eager not needed, just ensure task returns pong synchronously via apply)
    from app.worker.tasks import add, ping

    assert ping.apply().get() == "pong"
    assert add.apply(args=(2, 3)).get() == 5


def test_celery_tasks_registered():
    from app.worker.celery_app import celery_app
    import app.worker.tasks  # noqa: F401

    # tasks should be known to celery
    assert celery_app.tasks.get("ping") is not None
    assert celery_app.tasks.get("add") is not None
