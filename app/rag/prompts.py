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
- Background goal: {primary_goal}
- Experience: {experience_level}
- Weight: {weight_kg}kg | Max HR: {max_hr}bpm | VO2max est: {vo2max}
- Threshold pace: {threshold_pace} min/km

## Current Fitness State (last 8 weeks)
- Chronic Training Load (CTL): {ctl}
- Acute Training Load (ATL): {atl}
- Training Stress Balance (TSB): {tsb}
- Avg weekly run volume: {run_km}km
- Avg gym sessions/week: {gym_sessions}

## Recent Training History
{workout_history_summary}

## Training Plan Request
Race goal: {goal}
Duration: {weeks} weeks
Training days per week: {training_days_per_week}

## Retrieved Periodization Knowledge
{rag_context}

## Instructions
Design a {weeks}-week training plan tailored to this athlete's actual fitness data above.
1. Schedule exactly {training_days_per_week} training sessions per week (rest days for the others)
2. Start from the athlete's current CTL — don't increase weekly volume >10% per week
3. Follow the 80/20 rule: 70-80% of running sessions at Z1/Z2 (easy/aerobic)
4. Include progressive overload with a deload week every 3-4 weeks
5. For race-goal-specific sessions: target the appropriate race pace derived from the athlete's threshold pace and VO2max

CRITICAL OUTPUT CONSTRAINT: The entire plan must fit in one tool call.
- Each session "title" ≤ 6 words (e.g. "Easy 8km zone 2")
- Each session "description" ≤ 12 words (e.g. "Zone 2, conversational pace, HR 130-145.")
- Do NOT write paragraphs. One short phrase per field.
- The "explanation" field ≤ 60 words total for the whole plan.

Use the create_training_plan tool to save the plan."""
