"""Brain CLI v3 — Plan state persistence in ~/.brain/state/plan.json."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

STATE_DIR = Path.home() / ".brain" / "state"
PLAN_FILE = STATE_DIR / "plan.json"
TTL = 300.0


@dataclass
class PlanStep:
    title: str
    status: str  # pending | in_progress | done | blocked


@dataclass
class Plan:
    prompt: str
    steps: list[PlanStep]
    current_step: int
    created_at: float
    expires_at: float


def create_plan(prompt: str, step_titles: list[str]) -> Plan:
    now = time.time()
    steps = []
    for i, title in enumerate(step_titles):
        status = "in_progress" if i == 0 else "pending"
        steps.append(PlanStep(title=title, status=status))
    return Plan(
        prompt=prompt,
        steps=steps,
        current_step=0,
        created_at=now,
        expires_at=now + TTL,
    )


def load_plan() -> Plan | None:
    if not PLAN_FILE.exists():
        return None
    try:
        data = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
        steps = [PlanStep(**s) for s in data["steps"]]
        return Plan(
            prompt=data["prompt"],
            steps=steps,
            current_step=data["current_step"],
            created_at=data["created_at"],
            expires_at=data["expires_at"],
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def save_plan(plan: Plan) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "prompt": plan.prompt,
        "steps": [asdict(s) for s in plan.steps],
        "current_step": plan.current_step,
        "created_at": plan.created_at,
        "expires_at": plan.expires_at,
    }
    tmp = PLAN_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, PLAN_FILE)


def is_valid(plan: Plan) -> bool:
    if time.time() >= plan.expires_at:
        return False
    return any(s.status == "in_progress" for s in plan.steps)


def mark_done() -> Plan | None:
    plan = load_plan()
    if plan is None:
        return None
    if plan.current_step >= len(plan.steps):
        return plan
    plan.steps[plan.current_step].status = "done"
    plan.current_step += 1
    if plan.current_step < len(plan.steps):
        plan.steps[plan.current_step].status = "in_progress"
    plan.expires_at = time.time() + TTL
    save_plan(plan)
    return plan


def mark_blocked(reason: str) -> Plan | None:
    plan = load_plan()
    if plan is None:
        return None
    if plan.current_step >= len(plan.steps):
        return plan
    step = plan.steps[plan.current_step]
    step.status = "blocked"
    step.title = f"{step.title} [BLOCKED: {reason}]" if reason else f"{step.title} [BLOCKED]"
    plan.expires_at = time.time() + TTL
    save_plan(plan)
    return plan


def delete_plan() -> None:
    if PLAN_FILE.exists():
        PLAN_FILE.unlink()
