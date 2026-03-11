from unittest.mock import patch


def test_base_task_correlation_id_empty_without_headers():
    from iil_commons.tasks.base import BaseTask

    task = BaseTask()
    mock_request = type("R", (), {"headers": None, "id": "t1", "retries": 0})()
    with patch.object(type(task), "request", new=mock_request):
        assert task._get_correlation_id() == ""


def test_base_task_correlation_id_from_headers():
    from iil_commons.tasks.base import BaseTask

    task = BaseTask()
    mock_request = type(
        "R", (), {"headers": {"X-Correlation-ID": "abc-123"}, "id": "t1", "retries": 0}
    )()
    with patch.object(type(task), "request", new=mock_request):
        assert task._get_correlation_id() == "abc-123"


def test_base_task_is_abstract():
    from iil_commons.tasks.base import BaseTask

    assert BaseTask.abstract is True
