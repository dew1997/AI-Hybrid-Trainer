COACHING_SYSTEM_PROMPT = """You are an expert hybrid fitness coach with deep knowledge in running \
physiology, strength training periodization, and data-driven performance analysis.

Your coaching style is:
- Evidence-based: reference the athlete's actual metrics when available
- Specific: give concrete paces (min/km), weights (kg), durations — not vague advice
- Honest: if data is insufficient, say so clearly
- Concise: athletes want actionable insights, not essays

You have access to the athlete's training data and coaching science articles retrieved \
from the knowledge base. Always cite specific numbers from the data."""


COACHING_QUERY_TEMPLATE = """## Athlete Profile
- Name: {display_name}
- Goal: {primary_goal}
- Experience: {experience_level}
- Weight: {weight_kg}kg | Max HR: {max_hr}bpm | VO2max est: {vo2max}

## Current Fitness State (last {context_weeks} weeks)
- Chronic Training Load (CTL): {ctl} TSS/day  [long-term fitness baseline]
- Acute Training Load (ATL): {atl} TSS/day    [7-day fatigue indicator]
- Training Stress Balance (TSB): {tsb}        [positive = fresh, negative = fatigued]
- Weekly run volume: {run_km}km avg
- Weekly gym sessions: {gym_sessions} avg

## Recent Training Summary
{workout_history_summary}

## Retrieved Coaching Knowledge
{rag_context}

## Athlete's Question
{user_query}

## Instructions
Answer the question directly with reference to the athlete's specific metrics above.
End with 2-3 bullet-point "Action Items" formatted as:
- **Action**: [specific, measurable instruction]"""


PLAN_GENERATION_TEMPLATE = """## Athlete Profile
- Name: {display_name}
- Goal: {primary_goal}
- Experience: {experience_level}
- Weight: {weight_kg}kg | Max HR: {max_hr}bpm | VO2max est: {vo2max}
- Threshold pace: {threshold_pace} min/km

## Current Fitness State
- CTL: {ctl} | ATL: {atl} | TSB: {tsb}
- Recent weekly run volume: {run_km}km
- Recent gym frequency: {gym_sessions} sessions/week

## Training Plan Request
Goal: {goal}
Duration: {weeks} weeks
Weekly time available: {weekly_hours} hours
Constraints: {constraints}

## Retrieved Periodization Knowledge
{rag_context}

## Instructions
Design a {weeks}-week training plan that:
1. Respects the athlete's current CTL (don't increase volume >10% per week)
2. Follows 80/20 rule: 70-80% of running at Z1/Z2 (easy/aerobic)
3. Includes progressive overload with a deload week every 3-4 weeks
4. Integrates gym and running without excessive overlap on hard days
5. Respects the stated constraints

Use the create_training_plan tool to save the plan. The plan must include an explanation \
field summarising the rationale and key focus of each week."""
