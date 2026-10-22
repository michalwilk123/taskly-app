import pytest

from app.features.todos.schemas import TodoCreate


def test_list_returns_tasks_from_repository(client, repository_mock, todo):
    repository_mock.list.return_value = [todo]
    response = client.get("/api/todos")
    assert response.status_code == 200
    assert response.json() == [todo.model_dump(mode="json")]
    repository_mock.list.assert_called_once_with()


def test_create_trims_input_and_returns_created_task(client, repository_mock, todo):
    repository_mock.create.return_value = todo
    response = client.post("/api/todos", json={"title": "  Plan the sprint  ", "priority": "high"})
    assert response.status_code == 201
    assert response.json() == todo.model_dump(mode="json")
    repository_mock.create.assert_called_once_with(
        TodoCreate(title="Plan the sprint", priority="high")
    )


@pytest.mark.parametrize("payload", [
    {"title": "   "},
    {"title": "x" * 121},
    {"title": "Task", "priority": "urgent"},
    {"title": "Task", "due_date": "2026-02-30"},
])
def test_invalid_create_never_calls_repository(client, repository_mock, payload):
    assert client.post("/api/todos", json=payload).status_code == 422
    repository_mock.create.assert_not_called()


@pytest.mark.parametrize("states,expected", [
    ([], {"total": 0, "completed": 0, "active": 0}),
    ([True, False, False], {"total": 3, "completed": 1, "active": 2}),
    ([True, True], {"total": 2, "completed": 2, "active": 0}),
])
def test_stats_counts_all_task_states(client, repository_mock, todo, states, expected):
    repository_mock.list.return_value = [todo.model_copy(update={"completed": state}) for state in states]
    response = client.get("/api/todos/stats")
    assert response.status_code == 200
    assert response.json() == expected
    repository_mock.list.assert_called_once_with()
