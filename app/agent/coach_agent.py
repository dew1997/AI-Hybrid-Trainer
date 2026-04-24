"""
Multi-turn Claude agent for coaching queries and training plan generation.
Uses Anthropic's native tool_use API — no LangChain or framework overhead.
"""

import json

import structlog
from anthropic import APIStatusError, AsyncAnthropic, BadRequestError
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools import TOOL_DEFINITIONS, execute_tool
from app.config import settings
from app.core.exceptions import AgentMaxTurnsError
from app.models.user import User
from app.rag.prompts import (
    COACHING_QUERY_TEMPLATE,
    COACHING_SYSTEM_PROMPT,
    PLAN_GENERATION_TEMPLATE,
)
from app.rag.retriever import build_rag_context, hybrid_search
from app.schemas.agent import (
    CoachingQueryRequest,
    CoachingQueryResponse,
    GeneratePlanRequest,
    RetrievedSource,
)

logger = structlog.get_logger(__name__)
_anthropic: AsyncAnthropic | None = None

MAX_AGENT_TURNS = 6


def _get_client() -> AsyncAnthropic:
    global _anthropic
    if _anthropic is None:
        _anthropic = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic


async def _run_agent_loop(
    user_message: str,
    user: User,
    db: AsyncSession,
    plan_request=None,
) -> tuple[str, list[dict], dict]:
    """
    Core multi-turn agent loop.
    Returns: (final_answer, tool_calls_log, token_usage)
    """
    client = _get_client()
    messages = [{"role": "user", "content": user_message}]
    tool_calls_log: list[dict] = []
    total_input_tokens = 0
    total_output_tokens = 0

    for turn in range(MAX_AGENT_TURNS):
        try:
            response = await client.messages.create(
                model=settings.anthropic_model,
                max_tokens=2048,
                system=COACHING_SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,  # type: ignore[arg-type]
                messages=messages,  # type: ignore[arg-type]
            )
        except BadRequestError as e:
            msg = str(e)
            if "credit balance is too low" in msg or "billing" in msg.lower():
                raise HTTPException(
                    status_code=402,
                    detail="Anthropic API credits exhausted. Please top up at console.anthropic.com.",
                )
            raise HTTPException(status_code=400, detail=f"AI request invalid: {msg}")
        except APIStatusError as e:
            raise HTTPException(status_code=503, detail=f"AI service unavailable: {e.status_code}")

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        if response.stop_reason == "end_turn":
            text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            return text, tool_calls_log, {
                "input": total_input_tokens,
                "output": total_output_tokens,
            }

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(
                        "agent_tool_call",
                        tool=block.name,
                        turn=turn + 1,
                        user_id=str(user.id),
                    )
                    result = await execute_tool(
                        tool_name=block.name,
                        tool_input=block.input,  # type: ignore[arg-type]
                        user_id=str(user.id),
                        db=db,
                        plan_request=plan_request,
                    )
                    tool_calls_log.append({
                        "tool": block.name,
                        "input": block.input,
                        "result_keys": list(result.keys()) if isinstance(result, dict) else [],
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    })

            messages.append({"role": "assistant", "content": response.content})  # type: ignore[dict-item]
            messages.append({"role": "user", "content": tool_results})  # type: ignore[dict-item]
            continue

        # Unexpected stop reason
        break

    raise AgentMaxTurnsError(MAX_AGENT_TURNS)


async def run_coaching_query(
    request: CoachingQueryRequest,
    user: User,
    db: AsyncSession,
) -> CoachingQueryResponse:
    # Pre-fetch user stats and RAG context to populate the prompt
    from app.agent.tools import _get_recent_workouts, _get_user_stats

    stats = await _get_user_stats({"weeks_back": request.context_weeks}, str(user.id), db)
    recent = await _get_recent_workouts(
        {"days_back": request.context_weeks * 7, "workout_type": "all"}, str(user.id), db
    )

    rag_chunks = await hybrid_search(
        query=request.query, db=db, user_id=str(user.id), top_k=6
    )
    rag_context = build_rag_context(rag_chunks)

    fitness = stats.get("fitness", {})
    vol = stats.get("volume_averages", {})
    profile = stats.get("profile", {})

    workout_summary = _summarise_workouts(recent.get("workouts", []))

    user_message = COACHING_QUERY_TEMPLATE.format(
        display_name=user.display_name or "Athlete",
        primary_goal=profile.get("primary_goal") or "general fitness",
        experience_level=profile.get("experience_level") or "intermediate",
        weight_kg=profile.get("weight_kg") or "unknown",
        max_hr=profile.get("max_hr") or "unknown",
        vo2max=profile.get("vo2max") or "unknown",
        context_weeks=request.context_weeks,
        ctl=fitness.get("ctl") or "not enough data",
        atl=fitness.get("atl") or "not enough data",
        tsb=fitness.get("tsb") or "not enough data",
        run_km=vol.get("avg_run_km_per_week", 0),
        gym_sessions=vol.get("avg_gym_sessions_per_week", 0),
        workout_history_summary=workout_summary,
        rag_context=rag_context,
        user_query=request.query,
    )

    answer, tool_calls, usage = await _run_agent_loop(user_message, user, db)

    action_items = _extract_action_items(answer)
    sources = [
        RetrievedSource(title=c.title or c.source_type, relevance=round(c.rrf_score * 100, 1))
        for c in rag_chunks[:3]
    ]

    logger.info(
        "coaching_query_complete",
        user_id=str(user.id),
        input_tokens=usage["input"],
        output_tokens=usage["output"],
        tool_calls=len(tool_calls),
    )

    return CoachingQueryResponse(
        answer=answer,
        reasoning=None,
        sources=sources,
        suggested_actions=action_items,
        token_usage=usage,
    )


async def run_generate_plan(
    request: GeneratePlanRequest,
    user: User,
    db: AsyncSession,
) -> dict:
    from app.agent.tools import _get_recent_workouts, _get_user_stats

    stats = await _get_user_stats({"weeks_back": 8}, str(user.id), db)
    await _get_recent_workouts({"days_back": 56, "workout_type": "all"}, str(user.id), db)

    rag_chunks = await hybrid_search(
        query=f"training plan periodization {request.goal}",
        db=db,
        user_id=str(user.id),
        top_k=6,
    )
    rag_context = build_rag_context(rag_chunks)

    fitness = stats.get("fitness", {})
    vol = stats.get("volume_averages", {})
    profile = stats.get("profile", {})

    from app.pipeline.metrics import get_threshold_pace_from_profile
    threshold = get_threshold_pace_from_profile(user)
    threshold_str = f"{int(threshold // 60)}:{int(threshold % 60):02d}" if threshold else "unknown"

    user_message = PLAN_GENERATION_TEMPLATE.format(
        display_name=user.display_name or "Athlete",
        primary_goal=profile.get("primary_goal") or "general fitness",
        experience_level=profile.get("experience_level") or "intermediate",
        weight_kg=profile.get("weight_kg") or "unknown",
        max_hr=profile.get("max_hr") or "unknown",
        vo2max=profile.get("vo2max") or "unknown",
        threshold_pace=threshold_str,
        ctl=fitness.get("ctl") or "not enough data",
        atl=fitness.get("atl") or "not enough data",
        tsb=fitness.get("tsb") or "not enough data",
        run_km=vol.get("avg_run_km_per_week", 0),
        gym_sessions=vol.get("avg_gym_sessions_per_week", 0),
        goal=request.goal,
        weeks=request.weeks,
        weekly_hours=request.weekly_hours or "flexible",
        constraints=", ".join(request.constraints) or "none",
        rag_context=rag_context,
    )

    _, tool_calls, usage = await _run_agent_loop(user_message, user, db, plan_request=request)

    plan_calls = [tc for tc in tool_calls if tc["tool"] == "create_training_plan"]
    if not plan_calls:
        raise ValueError("Agent did not call create_training_plan — no plan was saved")

    from sqlalchemy import select

    from app.models.training_plan import TrainingPlan
    result = await db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.user_id == user.id)
        .order_by(TrainingPlan.created_at.desc())
    )
    plan = result.scalars().first()

    if not plan:
        raise ValueError("Could not retrieve saved plan from database")

    plan.generation_metadata = {"token_usage": usage, "rag_sources": len(rag_chunks)}
    await db.flush()

    return {
        "id": str(plan.id),
        "goal": plan.goal,
        "duration_weeks": plan.duration_weeks,
        "status": plan.status,
        "ai_explanation": plan.ai_explanation,
        "weeks": plan_calls[0]["input"].get("weeks", []),
        "token_usage": usage,
    }


def _summarise_workouts(workouts: list[dict]) -> str:
    if not workouts:
        return "No recent workouts recorded."
    lines = []
    for w in workouts[:10]:
        if w["type"] == "run":
            lines.append(
                f"- {w['date']} Run: {w.get('distance_km', '?')}km, "
                f"pace {_fmt_pace(w.get('avg_pace_sec_per_km'))}, "
                f"HR {w.get('avg_hr', '?')}bpm, TSS {w.get('tss', '?')}, "
                f"zone {w.get('pace_zone', '?')}"
            )
        else:
            lines.append(
                f"- {w['date']} {w['type'].capitalize()}: {w.get('duration_min', '?')}min, "
                f"volume {w.get('volume_kg', '?')}kg, RPE {w.get('rpe', '?')}"
            )
    return "\n".join(lines)


def _fmt_pace(pace_sec: float | None) -> str:
    if not pace_sec:
        return "?"
    return f"{int(pace_sec // 60)}:{int(pace_sec % 60):02d}/km"


def _extract_action_items(text: str) -> list[str]:
    """Pull out bullet-point action items from the agent's response."""
    lines = text.split("\n")
    actions = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- **Action"):
            actions.append(stripped.lstrip("- ").strip())
        elif stripped.startswith("**Action"):
            actions.append(stripped.strip())
    return actions[:3]
