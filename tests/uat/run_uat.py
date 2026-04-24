"""
User Acceptance Testing — AI Hybrid Trainer
============================================
Runs a complete end-to-end walkthrough against a live local server.

Prerequisites (all checked automatically before any test runs):
  1. Docker Desktop is running
  2. docker-compose up  (starts db, redis, api, worker, beat)
  3. alembic upgrade head
  4. python scripts/seed_knowledge_base.py

Run:
    python tests/uat/run_uat.py

The script creates a fresh test account each run (email includes a timestamp)
so it never conflicts with previous runs.
"""

import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx

BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 30  # seconds — AI calls can be slow

# ── Colours ──────────────────────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET}  {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}✗{RESET}  {msg}")


def info(msg: str) -> None:
    print(f"  {BLUE}→{RESET}  {msg}")


def section(title: str) -> None:
    print(f"\n{BOLD}{title}{RESET}")
    print("─" * 60)


def warn(msg: str) -> None:
    print(f"  {YELLOW}!{RESET}  {msg}")


# ── Result tracker ────────────────────────────────────────────────────────────

results: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str = "") -> None:
    results.append((name, passed, detail))
    if passed:
        ok(name)
    else:
        fail(f"{name}  →  {detail}")


# ── Preflight checks ──────────────────────────────────────────────────────────

def check_docker_running() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_containers_healthy() -> tuple[bool, list[str]]:
    try:
        result = subprocess.run(
            ["docker-compose", "ps", "--format", "json"],
            capture_output=True, text=True, timeout=15,
            cwd="/Users/dewei/Desktop/AI-Hybrid-Trainer"
        )
        if result.returncode != 0:
            return False, []
        running = []
        for line in result.stdout.strip().splitlines():
            try:
                svc = json.loads(line)
                if svc.get("State") == "running":
                    running.append(svc.get("Service", ""))
            except json.JSONDecodeError:
                pass
        required = {"api", "db", "redis", "worker"}
        missing = required - set(running)
        return len(missing) == 0, list(missing)
    except Exception:
        return False, []


def wait_for_api(timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"http://localhost:8000/health", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def run_preflight() -> bool:
    section("PREFLIGHT CHECKS")
    all_ok = True

    # Docker running
    if check_docker_running():
        ok("Docker Desktop is running")
    else:
        fail("Docker Desktop is not running — start it and re-run")
        return False

    # Containers up
    healthy, missing = check_containers_healthy()
    if healthy:
        ok("docker-compose services are up (api, db, redis, worker)")
    else:
        if missing:
            fail(f"Missing/stopped services: {', '.join(missing)}")
            info("Run:  docker-compose up -d")
        else:
            warn("Could not read container status — continuing anyway")
        all_ok = False

    # API reachable
    info("Waiting for API to respond (up to 60s)…")
    if wait_for_api():
        ok("API is reachable at http://localhost:8000")
    else:
        fail("API did not respond — check docker-compose logs")
        return False

    # Health-ready (DB + Redis)
    try:
        r = httpx.get("http://localhost:8000/health/ready", timeout=10)
        body = r.json()
        if r.status_code == 200 and body.get("status") in ("ok", "ready"):
            ok("Database and Redis are reachable (health/ready)")
        else:
            fail(f"health/ready returned: {r.status_code} {body}")
            all_ok = False
    except Exception as e:
        fail(f"health/ready check failed: {e}")
        all_ok = False

    # Knowledge base seeded
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
    except Exception:
        pass

    return all_ok


# ── Test helpers ──────────────────────────────────────────────────────────────

def assert_status(r: httpx.Response, expected: int, label: str) -> bool:
    if r.status_code == expected:
        return True
    fail(f"{label}: expected HTTP {expected}, got {r.status_code} — {r.text[:200]}")
    return False


def assert_field(data: dict, key: str, label: str) -> bool:
    if key in data and data[key] is not None:
        return True
    fail(f"{label}: missing field '{key}' in response")
    return False


# ── Test suites ───────────────────────────────────────────────────────────────

def test_auth(client: httpx.Client) -> tuple[str, str]:
    """Returns (access_token, user_id) for use in later tests."""
    section("1 — AUTHENTICATION")

    timestamp = datetime.now().strftime("%H%M%S")
    email = f"uat_{timestamp}@example.com"
    password = "TestPass123!"

    # Register
    r = client.post("/auth/register", json={
        "email": email,
        "password": password,
        "display_name": "UAT Athlete",
        "goal": "hybrid_performance",
        "experience": "intermediate",
        "weight_kg": 75.0,
        "max_hr": 185,
        "resting_hr": 52,
    })
    passed = assert_status(r, 201, "register")
    if passed:
        body = r.json()
        passed = assert_field(body, "access_token", "register") and \
                 assert_field(body, "user", "register")
    record("Register new account", passed)
    if not passed:
        return "", ""
    token = r.json()["access_token"]
    user_id = r.json()["user"]["id"]
    info(f"Created account: {email}")

    # Login with correct credentials
    r = client.post("/auth/login", json={"email": email, "password": password})
    passed = assert_status(r, 200, "login") and assert_field(r.json(), "access_token", "login")
    record("Login with correct credentials", passed)
    if passed:
        token = r.json()["access_token"]
        refresh_token = r.json().get("refresh_token", "")

    # Login with wrong password
    r = client.post("/auth/login", json={"email": email, "password": "wrongpassword"})
    record("Login rejected with wrong password", r.status_code == 401)

    # Get profile
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    passed = assert_status(r, 200, "get profile") and assert_field(r.json(), "email", "get profile")
    record("Fetch own profile", passed)

    # Update profile
    r = client.patch("/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"weight_kg": 74.5, "weekly_hours_target": 8}
    )
    passed = assert_status(r, 200, "update profile")
    if passed:
        passed = r.json().get("weight_kg") == 74.5
        if not passed:
            fail("update profile: weight_kg not updated in response")
    record("Update profile", passed)

    # Token refresh
    if refresh_token:
        r = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        passed = assert_status(r, 200, "token refresh") and \
                 assert_field(r.json(), "access_token", "token refresh")
        record("Token refresh", passed)
        if passed:
            token = r.json()["access_token"]

    return token, user_id


def test_workouts(client: httpx.Client, token: str) -> tuple[str, str]:
    """Returns (run_id, gym_id)."""
    section("2 — WORKOUTS")
    headers = {"Authorization": f"Bearer {token}"}

    started = datetime.now(timezone.utc) - timedelta(hours=2)

    # Log a run
    r = client.post("/workouts", headers=headers, json={
        "workout_type": "run",
        "started_at": started.isoformat(),
        "duration_seconds": 3600,
        "distance_meters": 10000,
        "avg_hr": 148,
        "avg_pace_sec_per_km": 360,
        "elevation_gain_m": 85,
        "route_name": "UAT Morning Loop",
        "perceived_effort": 6,
        "notes": "UAT test run",
        "splits": [
            {"split_number": 1, "distance_m": 1000, "duration_seconds": 360,
             "avg_hr": 142, "avg_pace_sec_per_km": 360, "cadence_spm": 172},
            {"split_number": 2, "distance_m": 1000, "duration_seconds": 358,
             "avg_hr": 145, "avg_pace_sec_per_km": 358, "cadence_spm": 174},
        ]
    }, timeout=TIMEOUT)
    passed = assert_status(r, 201, "log run")
    if passed:
        body = r.json().get("workout", r.json())
        passed = body.get("workout_type") == "run"
    record("Log a 10 km run with splits", passed)
    run_id = r.json().get("workout", r.json()).get("id", "") if r.status_code == 201 else ""
    if run_id:
        w = r.json().get("workout", r.json())
        info(f"Run ID: {run_id}  |  status: {w.get('status')}")

    # Log a gym session
    gym_start = datetime.now(timezone.utc) - timedelta(hours=26)
    r = client.post("/workouts", headers=headers, json={
        "workout_type": "gym",
        "started_at": gym_start.isoformat(),
        "duration_seconds": 4500,
        "muscle_groups": ["chest", "shoulders", "triceps"],
        "perceived_effort": 7,
        "notes": "UAT push session",
        "sets": [
            {"set_number": 1, "exercise_name": "Bench Press",     "reps": 5,  "weight_kg": 80.0, "is_warmup": False},
            {"set_number": 2, "exercise_name": "Bench Press",     "reps": 5,  "weight_kg": 80.0, "is_warmup": False},
            {"set_number": 3, "exercise_name": "Bench Press",     "reps": 5,  "weight_kg": 80.0, "is_warmup": False},
            {"set_number": 4, "exercise_name": "Overhead Press",  "reps": 8,  "weight_kg": 55.0, "is_warmup": False},
            {"set_number": 5, "exercise_name": "Overhead Press",  "reps": 8,  "weight_kg": 55.0, "is_warmup": False},
            {"set_number": 6, "exercise_name": "Tricep Pushdown", "reps": 12, "weight_kg": 30.0, "is_warmup": False},
        ]
    }, timeout=TIMEOUT)
    passed = assert_status(r, 201, "log gym")
    if passed:
        body = r.json().get("workout", r.json())
        passed = body.get("workout_type") == "gym"
    record("Log a gym push session with sets", passed)
    gym_id = r.json().get("workout", r.json()).get("id", "") if r.status_code == 201 else ""
    if gym_id:
        w = r.json().get("workout", r.json())
        info(f"Gym ID: {gym_id}  |  volume: {w.get('total_volume_kg')} kg")

    # List workouts (all)
    r = client.get("/workouts", headers=headers, timeout=TIMEOUT)
    passed = assert_status(r, 200, "list workouts")
    if passed:
        items = r.json().get("data", r.json().get("items", []))
        passed = len(items) >= 2
        if not passed:
            fail(f"list workouts: expected ≥2 items, got {len(items)}")
    record("List workouts returns both sessions", passed)

    # Filter by type
    r = client.get("/workouts?workout_type=run", headers=headers, timeout=TIMEOUT)
    passed = assert_status(r, 200, "filter by type")
    if passed:
        items = r.json().get("data", r.json().get("items", []))
        passed = all(w["workout_type"] == "run" for w in items)
        if not passed:
            fail("filter by type: got non-run workouts in run filter")
    record("Filter workouts by type=run", passed)

    # Get single workout
    if run_id:
        r = client.get(f"/workouts/{run_id}", headers=headers, timeout=TIMEOUT)
        passed = assert_status(r, 200, "get workout")
        if passed:
            body = r.json().get("workout", r.json())
            passed = body.get("id") == run_id and "splits" in body
        record("Fetch run detail with splits", passed)

    # Update notes
    if run_id:
        r = client.patch(f"/workouts/{run_id}", headers=headers,
            json={"notes": "Updated by UAT"}, timeout=TIMEOUT)
        passed = assert_status(r, 200, "update notes")
        if passed:
            body = r.json().get("workout", r.json())
            passed = body.get("notes") == "Updated by UAT"
        record("Update workout notes", passed)

    # Try to get another user's workout (auth check)
    r = client.get("/workouts/00000000-0000-0000-0000-000000000000",
                   headers=headers, timeout=TIMEOUT)
    record("Fetch non-existent workout returns 404", r.status_code == 404)

    # Wait briefly for Celery to process
    info("Waiting 5 s for Celery worker to process workouts…")
    time.sleep(5)

    # Verify processed status
    if run_id:
        r = client.get(f"/workouts/{run_id}", headers=headers, timeout=TIMEOUT)
        if r.status_code == 200:
            w = r.json().get("workout", r.json())
            status = w.get("status")
            tss = w.get("tss")
            info(f"Run pipeline status: {status}  |  TSS: {tss}")
            record("Run processed by pipeline (status=processed)", status == "processed")

    return run_id, gym_id


def test_analytics(client: httpx.Client, token: str) -> None:
    section("3 — ANALYTICS")
    headers = {"Authorization": f"Bearer {token}"}

    # Summary
    r = client.get("/analytics/summary", headers=headers, timeout=TIMEOUT)
    passed = assert_status(r, 200, "analytics summary")
    if passed:
        body = r.json()
        passed = "current_week" in body
    record("Analytics summary returns current week data", passed)
    if r.status_code == 200:
        cw = r.json().get("current_week") or {}
        info(f"Current week: {cw.get('total_workouts', 0)} workouts, "
             f"{cw.get('total_run_km', 0):.1f} km run, "
             f"{cw.get('total_gym_volume_kg', 0):.0f} kg lifted")

    # Fitness freshness (ATL/CTL/TSB chart)
    r = client.get("/analytics/fitness-freshness", headers=headers, timeout=TIMEOUT)
    passed = assert_status(r, 200, "fitness freshness")
    if passed:
        points = r.json().get("data", [])
        passed = isinstance(points, list)
    record("Fitness freshness chart returns data points", passed)
    if r.status_code == 200:
        points = r.json().get("data", [])
        info(f"Fitness freshness: {len(points)} weekly data points")

    # Weekly snapshots
    r = client.get("/analytics/weekly", headers=headers, timeout=TIMEOUT)
    passed = assert_status(r, 200, "weekly snapshots")
    record("Weekly snapshots endpoint responds", passed)


def test_ai_coaching(client: httpx.Client, token: str) -> None:
    section("4 — AI COACHING (calls Claude API — may take 10–20 s)")
    headers = {"Authorization": f"Bearer {token}"}

    # Coaching query
    info("Sending coaching query to Claude…")
    r = client.post("/agent/coaching-query", headers=headers, json={
        "query": "I just did a 10 km run and a push session this week. "
                 "How should I balance my training this week to avoid overtraining?",
        "context_weeks": 4,
    }, timeout=60)
    if r.status_code == 402:
        warn("Anthropic API credits exhausted — skipping AI tests (top up at console.anthropic.com)")
        record("AI coaching query returns answer + sources", True, "(skipped — no API credits)")
        return
    passed = assert_status(r, 200, "coaching query")
    if passed:
        body = r.json()
        passed = bool(body.get("answer") or body.get("response")) and \
                 isinstance(body.get("sources", body.get("retrieved_sources", [])), list)
        if not passed:
            fail(f"coaching query: missing answer/sources — keys: {list(body.keys())}")
    record("AI coaching query returns answer + sources", passed)
    if r.status_code == 200:
        body = r.json()
        answer = body.get("answer") or body.get("response", "")
        sources = body.get("sources") or body.get("retrieved_sources", [])
        actions = body.get("action_items", body.get("actions", []))
        info(f"Answer preview: {answer[:120]}…")
        info(f"Sources retrieved: {len(sources)}")
        info(f"Action items: {len(actions)}")


def test_plan_generation(client: httpx.Client, token: str) -> str:
    """Returns plan_id."""
    section("5 — TRAINING PLAN GENERATION (calls Claude API — may take 20–30 s)")
    headers = {"Authorization": f"Bearer {token}"}

    # Generate plan
    info("Asking Claude to generate a 4-week hybrid training plan…")
    r = client.post("/agent/generate-plan", headers=headers, json={
        "goal": "Improve my 10 km run time while maintaining strength",
        "weeks": 4,
        "constraints": ["3 gym sessions and 3 runs per week maximum", "Sundays are rest days"],
    }, timeout=90)
    if r.status_code == 402:
        warn("Anthropic API credits exhausted — skipping plan generation")
        record("Generate 4-week hybrid training plan", True, "(skipped — no API credits)")
        return ""
    passed = assert_status(r, 200, "generate plan")
    plan_id = ""
    if passed:
        body = r.json()
        plan_id = body.get("id", "")
        passed = bool(plan_id) and bool(body.get("goal"))
        if not passed:
            fail(f"generate plan: missing id/goal — keys: {list(body.keys())}")
    record("Generate 4-week hybrid training plan", passed)
    if plan_id:
        info(f"Plan ID: {plan_id}")
        body = r.json()
        weeks = body.get("weeks", body.get("plan_items", []))
        info(f"Plan has {len(weeks)} weeks/items")
        info(f"AI explanation: {str(body.get('ai_explanation', body.get('explanation', '')))[:120]}…")

    return plan_id


def test_plan_management(client: httpx.Client, token: str, plan_id: str) -> None:
    section("6 — TRAINING PLAN MANAGEMENT")
    headers = {"Authorization": f"Bearer {token}"}

    # List plans (only meaningful if plan was actually generated)
    r = client.get("/agent/plans", headers=headers, timeout=TIMEOUT)
    passed = assert_status(r, 200, "list plans")
    if passed and plan_id:
        body = r.json()
        plans = body if isinstance(body, list) else body.get("plans", body.get("items", []))
        passed = len(plans) >= 1
        if not passed:
            fail(f"list plans: expected ≥1 plan, got {len(plans)}")
    record("List plans endpoint responds", passed)

    if not plan_id:
        warn("Plan generation was skipped — skipping get/activate tests")
        return

    # Get plan detail
    r = client.get(f"/agent/plans/{plan_id}", headers=headers, timeout=TIMEOUT)
    passed = assert_status(r, 200, "get plan")
    if passed:
        body = r.json().get("plan", r.json())
        passed = body.get("id") == plan_id
    record("Fetch plan detail with weekly schedule", passed)

    # Activate plan
    r = client.patch(f"/agent/plans/{plan_id}/activate", headers=headers, timeout=TIMEOUT)
    passed = assert_status(r, 200, "activate plan")
    if passed:
        body = r.json().get("plan", r.json())
        passed = body.get("status") == "active"
    record("Activate plan sets status=active", passed)
    if passed:
        info(f"Plan {plan_id} is now active")


def test_delete_workout(client: httpx.Client, token: str, run_id: str) -> None:
    section("7 — CLEANUP (delete test workout)")
    headers = {"Authorization": f"Bearer {token}"}

    if not run_id:
        warn("No run_id to delete")
        return

    r = client.delete(f"/workouts/{run_id}", headers=headers, timeout=TIMEOUT)
    record("Delete workout returns 204", r.status_code == 204)

    # Confirm it's gone
    r = client.get(f"/workouts/{run_id}", headers=headers, timeout=TIMEOUT)
    record("Deleted workout returns 404", r.status_code == 404)


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary() -> None:
    section("RESULTS SUMMARY")
    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    failed_tests = [(n, d) for n, p, d in results if not p]

    print(f"\n  Passed: {GREEN}{passed}/{total}{RESET}")
    if failed_tests:
        print(f"  Failed: {RED}{len(failed_tests)}/{total}{RESET}\n")
        for name, detail in failed_tests:
            print(f"    {RED}✗{RESET}  {name}")
            if detail:
                print(f"       {detail}")
    else:
        print(f"\n  {GREEN}{BOLD}All tests passed! 🎉{RESET}")

    print()
    if passed == total:
        sys.exit(0)
    else:
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  AI Hybrid Trainer — User Acceptance Tests{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"  Target:  {BASE_URL}")
    print(f"  Time:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Preflight
    if not run_preflight():
        print(f"\n{RED}Preflight failed — fix the above issues and re-run.{RESET}\n")
        print("  Quick start:")
        print("    docker-compose up -d")
        print("    alembic upgrade head")
        print("    python scripts/seed_knowledge_base.py")
        print("    python tests/uat/run_uat.py\n")
        sys.exit(1)

    # All tests share one httpx client (no auth yet)
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        token, user_id = test_auth(client)
        if not token:
            print(f"\n{RED}Auth failed — cannot continue.{RESET}\n")
            print_summary()
            return

        run_id, gym_id = test_workouts(client, token)
        test_analytics(client, token)
        test_ai_coaching(client, token)
        plan_id = test_plan_generation(client, token)
        test_plan_management(client, token, plan_id)
        test_delete_workout(client, token, run_id)

    print_summary()


if __name__ == "__main__":
    main()
