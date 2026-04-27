"""
Seed 8 weeks of realistic gym + run workouts for demo@aihybridtrainer.com.

Inserts directly into PostgreSQL (bypasses Celery), then runs pipeline metrics
synchronously so analytics snapshots are populated immediately.

Run:
    python scripts/seed_demo_workouts.py
"""

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta

import structlog

# ── helpers ──────────────────────────────────────────────────────────────────

log = structlog.get_logger()


def d(days_ago: int, hour: int = 7) -> datetime:
    """Return a UTC datetime N days in the past at the given hour."""
    return datetime.now(UTC).replace(hour=hour, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)


# ── Gym session definitions ───────────────────────────────────────────────────
# Each entry: (exercise_name, sets, reps, weight_kg, rpe)
# weight 0.0 = bodyweight

LEGS_A = [
    ("Back Squat",               3, 5,  70.0,  7),
    ("Romanian Deadlift",        2, 9,  40.0,  7),
    ("Cable Pull Through",       2, 11, 13.75, 6),
    ("Dumbbell Walking Lunge",   2, 20, 10.0,  7),
    ("Leg Extension",            2, 15, 40.0,  8),
    ("Seated Leg Curl",          2, 15, 30.0,  8),
    ("Standing Calf Raise",      3, 10, 60.0,  7),
]

PUSH_A = [
    ("Barbell Bench Press",          3, 4,  55.0, 7),
    ("DB Seated Shoulder Press",     3, 9,  20.0, 7),
    ("Weighted Dip",                 2, 8,   0.0, 7),
    ("Low-to-High Cable Flye",       2, 13,  6.25,8),
    ("DB Skull Crusher",             3, 12,  8.0, 8),
    ("DB Lateral Raise",             3, 15,  8.0, 8),
    ("Ab Wheel Rollout",             3,  6,  0.0, 7),
]

PULL_A = [
    ("1-Arm Lat Pull-In",        2, 17,  5.0,  5),
    ("Pull-Up",                  4,  7,  0.0,  7),
    ("Pendlay Row",              3,  9, 30.0,  7),
    ("Machine High Row",         3, 11, 30.0,  8),
    ("Seated Face Pull",         3, 20, 12.5,  8),
    ("Reverse Grip EZ Bar Curl", 3, 20, 12.5,  9),
    ("Supinated EZ Bar Curl",    3, 15, 12.5,  9),
    ("DB Preacher Curl",         3, 12,  8.0,  7),
]

LEGS_B = [
    ("Deadlift",                     4, 4,  80.0, 7),
    ("Front Squat",                  3, 7,  40.0, 6),
    ("Single-Leg Leg Press",         2, 11, 47.5, 7),
    ("Single-Leg Leg Extension",     3, 15, 22.5, 7),
    ("Swiss Ball SL Leg Curl",       3, 12, 15.0, 7),
    ("Seated Calf Raise",            3, 15, 70.0, 7),
]

PUSH_B = [
    ("Close-Grip Bench Press",       3, 6,  60.0, 7),
    ("Overhead Press",               3, 5,  40.0, 8),
    ("DB Incline Press",             3, 11, 20.0, 7),
    ("Pec Deck",                     2, 15, 30.0, 7),
    ("Cable Lateral Raise",          3,  8,  5.0, 8),
    ("Cable Triceps Kickback",       3, 20,  3.75,8),
    ("Bicycle Crunch",               3, 12,  0.0, 7),
]

PULL_B = [
    ("Neutral-Grip Pulldown",        3, 11, 22.5, 8),
    ("Cable Seated Elbows-Out Row",  3, 10, 13.75,8),
    ("Cable Seated Row",             3, 10, 13.75,8),
    ("Straight-Arm Cable Pullover",  3, 15, 12.5, 7),
    ("Snatch-Grip Barbell Shrug",    3, 15, 40.0, 8),
    ("Cable Reverse Flye",           3, 20,  3.75,8),
    ("Single-Arm Cable Curl",        3, 12,  6.25,7),
    ("Hammer Curl",                  3,  8, 10.0, 7),
]

# Progressive overload multiplier per week (week 1 = 1.0, week 8 = ~1.12)
def load_scale(week: int) -> float:
    return 1.0 + (week - 1) * 0.017


# ── Run definitions ───────────────────────────────────────────────────────────
# (distance_m, pace_sec_per_km, avg_hr, elevation_m, tag)
RUNS = [
    (5000,  390, 138, 35, "easy"),    # 5km easy ~6:30/km
    (8000,  370, 145, 60, "moderate"),# 8km moderate ~6:10/km
    (10000, 365, 148, 80, "long"),    # 10km long ~6:05/km
    (6000,  355, 150, 45, "tempo"),   # 6km tempo ~5:55/km
    (5000,  400, 133, 20, "recovery"),# 5km recovery ~6:40/km
    (12000, 375, 147, 95, "long"),    # 12km long run
    (8000,  340, 155, 55, "tempo"),   # 8km faster tempo
]


# ── DB workout insertion ──────────────────────────────────────────────────────

async def run():
    import os
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://trainer:trainer@localhost:5433/trainer")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
    os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    os.environ.setdefault("SECRET_KEY", "dev-secret-not-for-prod")
    os.environ.setdefault("OPENROUTER_API_KEY", "placeholder")

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.models.user import User
    from app.models.workout import RunSplit, Workout, WorkoutSet
    from app.pipeline.metrics import (
        compute_gym_tss,
        compute_gym_volume,
        compute_pace_zone,
        compute_run_tss,
        get_threshold_pace_from_profile,
    )

    engine = create_async_engine(
        "postgresql+asyncpg://trainer:trainer@localhost:5433/trainer",
        echo=False,
    )
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        # ── find demo user ────────────────────────────────────────────────────
        result = await db.execute(
            select(User).where(User.email == "demo@aihybridtrainer.com")
        )
        user = result.scalar_one_or_none()
        if not user:
            print("ERROR: demo@aihybridtrainer.com not found. Register first.")
            return

        user_id = user.id
        print(f"Seeding for user {user_id} ({user.email})")

        # ── check existing workouts ───────────────────────────────────────────
        from sqlalchemy import func
        count_result = await db.execute(
            select(func.count(Workout.id)).where(Workout.user_id == user_id)
        )
        existing = count_result.scalar()
        if existing and existing > 5:
            print(f"User already has {existing} workouts — skipping to avoid duplicates.")
            print("Delete existing workouts from the DB first if you want to re-seed.")
            return

        total_workouts = 0
        # ── 8 weeks of PPL (6 sessions/week) + 2-3 runs/week ─────────────────
        # Layout: week starts Monday. Days: Mon Legs-A, Tue Push-A, Wed Pull-A,
        #         Thu run, Fri Legs-B, Sat Push-B + run, Sun Pull-B
        today = date.today()
        # anchor to the Monday 8 weeks ago
        weeks_ago_monday = today - timedelta(days=today.weekday() + 7 * 8)

        run_index = 0

        for week in range(1, 9):
            scale = load_scale(week)
            week_monday = weeks_ago_monday + timedelta(weeks=week - 1)

            def dt(day_offset: int, hour: int = 7) -> datetime:
                d_ = week_monday + timedelta(days=day_offset)
                return datetime(d_.year, d_.month, d_.day, hour, 0, 0, tzinfo=UTC)

            # ── Gym sessions ──────────────────────────────────────────────────
            gym_days = [
                (0,  LEGS_A, ["quads", "hamstrings", "glutes", "calves"], "Legs A"),
                (1,  PUSH_A, ["chest", "shoulders", "triceps"],            "Push A"),
                (2,  PULL_A, ["back", "biceps"],                           "Pull A"),
                (4,  LEGS_B, ["quads", "hamstrings", "glutes", "calves"],  "Legs B"),
                (5,  PUSH_B, ["chest", "shoulders", "triceps"],            "Push B"),
                (6,  PULL_B, ["back", "biceps"],                           "Pull B"),
            ]

            for day_offset, exercises, muscle_groups, template in gym_days:
                duration_sec = 4800 + (len(exercises) - 6) * 300  # ~80-90 min
                wo = Workout(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    workout_type="gym",
                    status="pending",
                    started_at=dt(day_offset, hour=7),
                    duration_seconds=duration_sec,
                    muscle_groups=muscle_groups,
                    workout_template=template,
                    perceived_effort=7,
                    source="manual",
                    raw_payload={},
                )
                db.add(wo)
                await db.flush()

                set_num = 1
                for ex_name, num_sets, reps, base_weight, rpe in exercises:
                    weight = round(base_weight * scale, 2) if base_weight > 0 else 0.0
                    for _ in range(num_sets):
                        s = WorkoutSet(
                            id=uuid.uuid4(),
                            workout_id=wo.id,
                            set_number=set_num,
                            exercise_name=ex_name,
                            reps=reps,
                            weight_kg=weight if weight > 0 else None,
                            is_warmup=False,
                        )
                        db.add(s)
                        set_num += 1

                await db.flush()

                # compute metrics
                from sqlalchemy.orm import selectinload
                sets_result = await db.execute(
                    select(WorkoutSet).where(WorkoutSet.workout_id == wo.id)
                )
                wo_sets = sets_result.scalars().all()
                wo.total_volume_kg = compute_gym_volume(wo_sets)
                wo.tss = compute_gym_tss(duration_sec, 7)
                wo.status = "processed"
                total_workouts += 1

            # ── Run sessions (Thu + Sat) ───────────────────────────────────────
            run_days_offsets = [3, 5]  # Thu, Sat
            for day_offset in run_days_offsets:
                r_def = RUNS[run_index % len(RUNS)]
                run_index += 1
                dist_m, pace_sec, avg_hr, elev, tag = r_def
                duration_sec = int(dist_m / 1000 * pace_sec)

                run_wo = Workout(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    workout_type="run",
                    status="pending",
                    started_at=dt(day_offset, hour=6),
                    duration_seconds=duration_sec,
                    distance_meters=dist_m,
                    avg_pace_sec_per_km=float(pace_sec),
                    avg_hr=avg_hr,
                    elevation_gain_m=elev,
                    perceived_effort=6 if tag in ("easy", "recovery") else 7,
                    source="manual",
                    raw_payload={},
                )
                db.add(run_wo)
                await db.flush()

                # splits
                km_count = dist_m // 1000
                for km in range(1, km_count + 1):
                    split_pace = pace_sec + (km - km_count // 2) * 2  # slight variation
                    spl = RunSplit(
                        id=uuid.uuid4(),
                        workout_id=run_wo.id,
                        split_number=km,
                        distance_m=1000,
                        duration_seconds=split_pace,
                        avg_hr=avg_hr + (km - 1) * 1,
                        avg_pace_sec_per_km=float(split_pace),
                    )
                    db.add(spl)

                await db.flush()

                # compute run metrics
                if user.max_hr and user.resting_hr:
                    run_wo.tss = compute_run_tss(duration_sec, avg_hr, user.max_hr, user.resting_hr)
                threshold = get_threshold_pace_from_profile(user)
                if threshold:
                    run_wo.pace_zone = compute_pace_zone(float(pace_sec), threshold)
                run_wo.status = "processed"
                total_workouts += 1

        await db.commit()
        print(f"✓ Inserted {total_workouts} processed workouts (8 weeks × 6 gym + 2 runs)")

        # ── rebuild analytics snapshots ───────────────────────────────────────
        print("Rebuilding analytics snapshots…")
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        from app.models.analytics import AnalyticsSnapshot

        # get all processed workouts
        all_wo = (await db.execute(
            select(Workout)
            .where(Workout.user_id == user_id, Workout.status == "processed")
            .order_by(Workout.started_at)
        )).scalars().all()

        # group by week_start
        from collections import defaultdict
        weeks: dict[date, list] = defaultdict(list)
        for w in all_wo:
            wd = w.started_at.date()
            ws = wd - timedelta(days=wd.weekday())
            weeks[ws].append(w)

        for ws, wos in sorted(weeks.items()):
            runs_  = [w for w in wos if w.workout_type == "run"]
            gyms_  = [w for w in wos if w.workout_type == "gym"]
            total_tss = sum(float(w.tss) for w in wos if w.tss)
            total_run_km = sum(float(w.distance_meters or 0) / 1000 for w in runs_)
            total_gym_vol = sum(float(w.total_volume_kg or 0) for w in gyms_)
            total_dur = sum((w.duration_seconds or 0) for w in wos) // 60
            paces = [float(w.avg_pace_sec_per_km) for w in runs_ if w.avg_pace_sec_per_km]
            avg_pace = sum(paces) / len(paces) if paces else None

            stmt = pg_insert(AnalyticsSnapshot).values(
                user_id=user_id,
                week_start_date=ws,
                total_workouts=len(wos),
                run_workouts=len(runs_),
                gym_workouts=len(gyms_),
                total_run_km=total_run_km,
                total_gym_volume_kg=total_gym_vol,
                total_duration_min=total_dur,
                weekly_tss=total_tss,
                avg_pace_sec_per_km=avg_pace,
            ).on_conflict_do_update(
                index_elements=["user_id", "week_start_date"],
                set_={
                    "total_workouts": len(wos),
                    "run_workouts": len(runs_),
                    "gym_workouts": len(gyms_),
                    "total_run_km": total_run_km,
                    "total_gym_volume_kg": total_gym_vol,
                    "total_duration_min": total_dur,
                    "weekly_tss": total_tss,
                    "avg_pace_sec_per_km": avg_pace,
                },
            )
            await db.execute(stmt)

        await db.commit()
        print(f"✓ Built {len(weeks)} weekly analytics snapshots")

        # ── compute rolling ATL/CTL/TSB ───────────────────────────────────────
        snaps = (await db.execute(
            select(AnalyticsSnapshot)
            .where(AnalyticsSnapshot.user_id == user_id)
            .order_by(AnalyticsSnapshot.week_start_date.asc())
        )).scalars().all()

        k_atl = 2 / (7 + 1)
        k_ctl = 2 / (42 + 1)
        daily = [float(s.weekly_tss or 0) / 7 for s in snaps]
        atl = ctl = daily[0] if daily else 0.0
        for i, tss in enumerate(daily):
            if i == 0:
                snaps[i].acute_load = round(atl, 2)
                snaps[i].chronic_load = round(ctl, 2)
                snaps[i].training_stress_balance = round(ctl - atl, 2)
            else:
                atl = tss * k_atl + atl * (1 - k_atl)
                ctl = tss * k_ctl + ctl * (1 - k_ctl)
                snaps[i].acute_load = round(atl, 2)
                snaps[i].chronic_load = round(ctl, 2)
                snaps[i].training_stress_balance = round(ctl - atl, 2)

        await db.commit()
        print(f"✓ ATL/CTL/TSB computed. Final: ATL={atl:.1f} CTL={ctl:.1f} TSB={ctl-atl:.1f}")
        print("\nDone! demo@aihybridtrainer.com now has 8 weeks of workout history.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
