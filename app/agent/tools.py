"""
Tool implementations called by the coach agent during its tool_use loop.
Each tool returns a JSON-serialisable dict.
"""

from datetime import date, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Search the training science knowledge base and the athlete's workout history "
                "for relevant coaching information. Use this to find evidence-based principles "
                "on periodization, recovery, HR zones, strength training, and nutrition."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "source_filter": {
                        "type": "string",
                        "enum": ["all", "training_science", "workout_history", "user_profile"],
                        "description": "Restrict results to a specific source type",
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Number of results to return",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_stats",
            "description": (
                "Retrieve computed fitness analytics for the athlete: CTL (chronic training load), "
                "ATL (acute load), TSB (form), weekly volume averages, and personal bests."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "weeks_back": {
                        "type": "integer",
                        "default": 8,
                        "minimum": 1,
                        "maximum": 52,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_workouts",
            "description": "Retrieve the athlete's detailed workout log for a recent period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_back": {"type": "integer", "default": 28, "maximum": 90},
                    "workout_type": {
                        "type": "string",
                        "enum": ["all", "run", "gym"],
                        "default": "all",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_training_plan",
            "description": (
                "Persist a structured training plan to the database. Call this ONLY after "
                "fully designing the plan. The plan will be saved and returned to the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string"},
                    "duration_weeks": {"type": "integer", "minimum": 1, "maximum": 16},
                    "explanation": {
                        "type": "string",
                        "description": "Natural language summary of the plan rationale",
                    },
                    "weeks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "week_number": {"type": "integer"},
                                "theme": {"type": "string"},
                                "target_tss": {"type": "number"},
                                "sessions": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "day_of_week": {"type": "integer", "minimum": 1, "maximum": 7},
                                            "session_type": {"type": "string"},
                                            "title": {"type": "string"},
                                            "description": {"type": "string"},
                                            "duration_min": {"type": "integer"},
                                            "target_distance_km": {"type": "number"},
                                            "target_pace_min_per_km": {"type": "number"},
                                            "target_hr_zone": {"type": "integer"},
                                            "target_rpe": {"type": "integer"},
                                            "exercises": {"type": "array"},
                                        },
                                        "required": ["day_of_week", "session_type", "title"],
                                    },
                                },
                            },
                            "required": ["week_number", "theme", "sessions"],
                        },
                    },
                },
                "required": ["goal", "weeks", "explanation"],
            },
        },
    },
]


async def execute_tool(
    tool_name: str,
    tool_input: dict,
    user_id: str,
    db: AsyncSession,
    plan_request=None,
) -> dict:
    if tool_name == "search_knowledge_base":
        return await _search_knowledge_base(tool_input, user_id, db)
    elif tool_name == "get_user_stats":
        return await _get_user_stats(tool_input, user_id, db)
    elif tool_name == "get_recent_workouts":
        return await _get_recent_workouts(tool_input, user_id, db)
    elif tool_name == "create_training_plan":
        return await _create_training_plan(tool_input, user_id, db, plan_request)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


async def _search_knowledge_base(inputs: dict, user_id: str, db: AsyncSession) -> dict:
    from app.rag.retriever import hybrid_search

    source = inputs.get("source_filter", "all")
    chunks = await hybrid_search(
        query=inputs["query"],
        db=db,
        user_id=user_id,
        top_k=inputs.get("top_k", 5),
        source_filter=None if source == "all" else source,
    )
    return {
        "results": [
            {
                "title": c.title,
                "source_type": c.source_type,
                "content": c.content,
                "relevance": round(c.rrf_score * 1000, 4),
            }
            for c in chunks
        ],
        "count": len(chunks),
    }


async def _get_user_stats(inputs: dict, user_id: str, db: AsyncSession) -> dict:
    from app.models.analytics import AnalyticsSnapshot
    from app.models.user import User

    weeks_back = inputs.get("weeks_back", 8)
    cutoff = date.today() - timedelta(weeks=weeks_back)

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()

    snaps_res = await db.execute(
        select(AnalyticsSnapshot)
        .where(
            AnalyticsSnapshot.user_id == user_id,
            AnalyticsSnapshot.week_start_date >= cutoff,
        )
        .order_by(AnalyticsSnapshot.week_start_date.desc())
    )
    snaps = snaps_res.scalars().all()

    latest = snaps[0] if snaps else None
    avg_run_km = (
        sum(float(s.total_run_km or 0) for s in snaps) / len(snaps) if snaps else 0
    )
    avg_gym = (
        sum(int(s.gym_workouts or 0) for s in snaps) / len(snaps) if snaps else 0
    )

    return {
        "profile": {
            "max_hr": user.max_hr if user else None,
            "resting_hr": user.resting_hr if user else None,
            "vo2max": float(user.vo2max_estimate) if user and user.vo2max_estimate else None,
            "weight_kg": float(user.weight_kg) if user and user.weight_kg else None,
            "primary_goal": user.primary_goal if user else None,
            "experience_level": user.experience_level if user else None,
        },
        "fitness": {
            "ctl": float(latest.chronic_load) if latest and latest.chronic_load else None,
            "atl": float(latest.acute_load) if latest and latest.acute_load else None,
            "tsb": float(latest.training_stress_balance) if latest and latest.training_stress_balance else None,
            "weekly_tss": float(latest.weekly_tss) if latest and latest.weekly_tss else None,
        },
        "volume_averages": {
            "avg_run_km_per_week": round(avg_run_km, 1),
            "avg_gym_sessions_per_week": round(avg_gym, 1),
        },
        "weeks_analysed": len(snaps),
    }


async def _get_recent_workouts(inputs: dict, user_id: str, db: AsyncSession) -> dict:
    from app.models.workout import Workout

    days_back = inputs.get("days_back", 28)
    workout_type = inputs.get("workout_type", "all")
    cutoff = date.today() - timedelta(days=days_back)

    query = select(Workout).where(
        Workout.user_id == user_id,
        Workout.started_at >= cutoff,
        Workout.status == "processed",
    ).order_by(Workout.started_at.desc())

    if workout_type != "all":
        query = query.where(Workout.workout_type == workout_type)

    result = await db.execute(query)
    workouts = result.scalars().all()

    return {
        "workouts": [
            {
                "date": w.started_at.date().isoformat(),
                "type": w.workout_type,
                "duration_min": (w.duration_seconds or 0) // 60,
                "distance_km": round(float(w.distance_meters or 0) / 1000, 2) if w.distance_meters else None,
                "avg_pace_sec_per_km": float(w.avg_pace_sec_per_km) if w.avg_pace_sec_per_km else None,
                "avg_hr": w.avg_hr,
                "tss": float(w.tss) if w.tss else None,
                "pace_zone": w.pace_zone,
                "rpe": w.perceived_effort,
                "volume_kg": float(w.total_volume_kg) if w.total_volume_kg else None,
            }
            for w in workouts
        ],
        "count": len(workouts),
        "period_days": days_back,
    }


async def _create_training_plan(
    inputs: dict,
    user_id: str,
    db: AsyncSession,
    plan_request=None,
) -> dict:
    from app.config import settings
    from app.models.training_plan import TrainingPlan, TrainingPlanItem

    plan = TrainingPlan(
        user_id=user_id,
        goal=inputs["goal"],
        duration_weeks=inputs.get("duration_weeks", len(inputs["weeks"])),
        status="draft",
        model_used=settings.openrouter_model,
        prompt_version="v1.0",
        ai_explanation=inputs.get("explanation"),
        raw_llm_output=inputs,
        start_date=plan_request.start_date if plan_request else None,
    )
    db.add(plan)
    await db.flush()

    for week in inputs["weeks"]:
        for session in week["sessions"]:
            item = TrainingPlanItem(
                plan_id=plan.id,
                week_number=week["week_number"],
                day_of_week=session["day_of_week"],
                session_type=session["session_type"],
                title=session["title"],
                description=session.get("description"),
                duration_min=session.get("duration_min"),
                target_distance_km=session.get("target_distance_km"),
                target_pace_min_per_km=session.get("target_pace_min_per_km"),
                target_hr_zone=session.get("target_hr_zone"),
                target_rpe=session.get("target_rpe"),
                exercises=session.get("exercises", []),
            )
            db.add(item)

    await db.flush()
    await db.commit()
    logger.info("training_plan_created", plan_id=str(plan.id), goal=plan.goal)
    return {"plan_id": str(plan.id), "status": "created", "weeks": len(inputs["weeks"])}
