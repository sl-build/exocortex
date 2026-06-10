"""Tests for brain.state module."""

import json
import time

import pytest

from brain.state import (
    TTL,
    create_plan,
    delete_plan,
    is_valid,
    load_plan,
    mark_blocked,
    mark_done,
    save_plan,
)


@pytest.fixture
def mock_state_dir(tmp_path, monkeypatch):
    import brain.state as state_mod

    state_dir = tmp_path / "brain" / "state"
    plan_file = state_dir / "plan.json"
    monkeypatch.setattr(state_mod, "STATE_DIR", state_dir)
    monkeypatch.setattr(state_mod, "PLAN_FILE", plan_file)
    return state_dir


class TestCreatePlan:
    def test_create_plan_sets_first_step_in_progress(self):
        plan = create_plan("do stuff", ["step 1", "step 2", "step 3"])
        assert plan.prompt == "do stuff"
        assert len(plan.steps) == 3
        assert plan.steps[0].status == "in_progress"
        assert plan.steps[1].status == "pending"
        assert plan.steps[2].status == "pending"
        assert plan.current_step == 0

    def test_create_plan_still_has_expiry_in_future(self, mock_state_dir):
        plan = create_plan("prompt", ["s1"])
        assert plan.expires_at > time.time()
        assert plan.expires_at <= time.time() + TTL + 1

    def test_single_step_plan(self):
        plan = create_plan("one", ["only step"])
        assert len(plan.steps) == 1
        assert plan.steps[0].status == "in_progress"
        assert plan.current_step == 0


class TestSaveAndLoad:
    def test_save_and_load_roundtrip(self, mock_state_dir):
        plan = create_plan("build thing", ["design", "implement", "test"])
        save_plan(plan)

        loaded = load_plan()
        assert loaded is not None
        assert loaded.prompt == "build thing"
        assert len(loaded.steps) == 3
        assert loaded.steps[0].title == "design"
        assert loaded.steps[0].status == "in_progress"
        assert loaded.current_step == 0

    def test_load_nonexistent_returns_none(self, mock_state_dir):
        assert load_plan() is None

    def test_load_corrupt_json_returns_none(self, mock_state_dir):
        import brain.state as state_mod

        state_mod.STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_mod.PLAN_FILE.write_text("not json at all {{{", encoding="utf-8")
        assert load_plan() is None

    def test_load_missing_keys_returns_none(self, mock_state_dir):
        import brain.state as state_mod

        state_mod.STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_mod.PLAN_FILE.write_text('{"prompt": "x"}', encoding="utf-8")
        assert load_plan() is None

    def test_atomic_save_does_not_corrupt(self, mock_state_dir):
        plan = create_plan("atomic", ["step1", "step2"])
        save_plan(plan)
        raw = mock_state_dir / "plan.json"
        content = raw.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["prompt"] == "atomic"
        assert len(data["steps"]) == 2


class TestMarkDone:
    def test_mark_done_advances_to_next_step(self, mock_state_dir):
        plan = create_plan("task", ["step A", "step B", "step C"])
        save_plan(plan)

        updated = mark_done()
        assert updated is not None
        assert updated.steps[0].status == "done"
        assert updated.steps[1].status == "in_progress"
        assert updated.steps[2].status == "pending"
        assert updated.current_step == 1

    def test_mark_done_on_last_step_completes(self, mock_state_dir):
        plan = create_plan("done", ["final step"])
        save_plan(plan)

        updated = mark_done()
        assert updated is not None
        assert updated.steps[0].status == "done"
        assert updated.current_step == 1
        assert updated.current_step >= len(updated.steps)

    def test_mark_done_on_complete_plan_noops(self, mock_state_dir):
        plan = create_plan("done already", ["only"])
        save_plan(plan)
        mark_done()  # complete
        updated = mark_done()  # noop
        assert updated is not None
        assert updated.current_step == 1

    def test_mark_done_nonexistent_returns_none(self, mock_state_dir):
        assert mark_done() is None

    def test_mark_done_refreshes_ttl(self, mock_state_dir):
        plan = create_plan("ttl test", ["step 1", "step 2"])
        save_plan(plan)

        # Manually age the plan to near-expiry
        import brain.state as state_mod

        old_expires = time.time() + 1
        state_mod.PLAN_FILE.write_text(
            json.dumps(
                {
                    "prompt": "ttl test",
                    "steps": [
                        {"title": "step 1", "status": "in_progress"},
                        {"title": "step 2", "status": "pending"},
                    ],
                    "current_step": 0,
                    "created_at": time.time() - 200,
                    "expires_at": old_expires,
                }
            ),
            encoding="utf-8",
        )

        updated = mark_done()
        assert updated is not None
        assert updated.expires_at > old_expires + TTL - 5  # refreshed


class TestMarkBlocked:
    def test_mark_blocked_does_not_advance(self, mock_state_dir):
        plan = create_plan("stuck", ["step 1", "step 2"])
        save_plan(plan)

        updated = mark_blocked("reason")
        assert updated is not None
        assert updated.steps[0].status == "blocked"
        assert "BLOCKED" in updated.steps[0].title
        assert updated.current_step == 0  # did not advance

    def test_mark_blocked_refreshes_ttl(self, mock_state_dir):
        plan = create_plan("stuck ttl", ["step"])
        save_plan(plan)
        import brain.state as state_mod

        state_mod.PLAN_FILE.write_text(
            json.dumps(
                {
                    "prompt": "stuck ttl",
                    "steps": [{"title": "step", "status": "in_progress"}],
                    "current_step": 0,
                    "created_at": time.time() - 200,
                    "expires_at": time.time() + 1,
                }
            ),
            encoding="utf-8",
        )

        updated = mark_blocked("reason")
        assert updated is not None
        assert updated.expires_at > time.time() + TTL - 5


class TestIsValid:
    def test_valid_when_in_progress_and_not_expired(self, mock_state_dir):
        plan = create_plan("valid", ["step"])
        save_plan(plan)
        assert is_valid(load_plan()) is True

    def test_invalid_when_expired(self, mock_state_dir):
        plan = create_plan("old", ["step"])
        save_plan(plan)
        import brain.state as state_mod

        state_mod.PLAN_FILE.write_text(
            json.dumps(
                {
                    "prompt": "old",
                    "steps": [{"title": "step", "status": "in_progress"}],
                    "current_step": 0,
                    "created_at": time.time() - 500,
                    "expires_at": time.time() - 1,
                }
            ),
            encoding="utf-8",
        )
        assert is_valid(load_plan()) is False

    def test_invalid_when_all_steps_done(self, mock_state_dir):
        import brain.state as state_mod

        state_mod.STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_mod.PLAN_FILE.write_text(
            json.dumps(
                {
                    "prompt": "done plan",
                    "steps": [{"title": "only", "status": "done"}],
                    "current_step": 1,
                    "created_at": time.time(),
                    "expires_at": time.time() + TTL,
                }
            ),
            encoding="utf-8",
        )
        assert is_valid(load_plan()) is False


class TestDeletePlan:
    def test_delete_removes_file(self, mock_state_dir):
        plan = create_plan("del", ["s1"])
        save_plan(plan)
        assert load_plan() is not None
        delete_plan()
        assert load_plan() is None

    def test_delete_nonexistent_does_not_crash(self, mock_state_dir):
        delete_plan()  # should not raise
