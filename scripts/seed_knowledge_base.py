"""
Seed the RAG knowledge base with training science articles.
Run once after initial DB setup:
    python scripts/seed_knowledge_base.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

ARTICLES = [
    {
        "title": "Aerobic Base Building and Zone 2 Training",
        "content": """Zone 2 training refers to exercise performed at low to moderate intensity,
typically 60-70% of maximum heart rate or roughly conversational pace. This zone
primarily uses the aerobic energy system and burns fat as the primary fuel source.

Research consistently shows that elite endurance athletes spend 70-80% of their
total training volume in Zone 1-2. This approach, known as polarized training,
allows high volume without excessive fatigue accumulation.

Benefits of Zone 2 training include: increased mitochondrial density, improved
fat oxidation capacity, enhanced cardiac stroke volume, and improved lactate
clearance. These adaptations form the aerobic base that supports all higher-intensity work.

A common mistake among recreational runners is training too hard on easy days
(the grey zone) — too fast to be truly restorative, too slow to provide high-intensity
stimulus. This leads to chronic fatigue without optimal adaptation.""",
    },
    {
        "title": "Training Stress Score and Performance Management",
        "content": """Training Stress Score (TSS) is a composite metric that accounts for
both the duration and intensity of a training session. A one-hour ride at functional
threshold power (FTP) produces exactly 100 TSS.

The Performance Management Chart (PMC) uses TSS to model fitness and fatigue:
- Chronic Training Load (CTL): 42-day exponential moving average of daily TSS.
  Represents long-term fitness. Higher CTL means greater aerobic capacity.
- Acute Training Load (ATL): 7-day EMA. Represents short-term fatigue.
- Training Stress Balance (TSB): CTL minus ATL. Positive TSB means the athlete
  is fresh (potentially undertrained). Negative TSB means the athlete is fatigued
  (potentially overtrained if sustained).

Optimal race performance typically occurs with TSB between 0 and +25.
TSB below -20 for extended periods signals overtraining risk.

Progression guideline: increase weekly TSS by no more than 10% per week to
minimize injury risk. Follow a 3-week build + 1-week recovery pattern.""",
    },
    {
        "title": "Progressive Overload in Strength Training",
        "content": """Progressive overload is the gradual increase of stress placed on the body
during training. Without progressive overload, training stimuli become insufficient
to drive further adaptation.

Methods of progressive overload:
1. Increase load (weight): Most straightforward — add 2.5-5kg when completing all
   reps with good form
2. Increase volume (sets × reps): Add a set once load progression stalls
3. Increase density: Same volume in less time (shorter rest periods)
4. Improve technique: More efficient movement = more effective stimulus

Linear progression (adding weight each session) works well for beginners.
Intermediate and advanced athletes benefit from weekly or block periodization.

Accumulation phase (weeks 1-3): Higher volume, moderate intensity (70-80% 1RM),
building work capacity. Intensification phase (weeks 4-6): Lower volume, higher
intensity (85-95% 1RM), peaking strength. Deload (week 7): Reduce volume by 40-50%
to recover and supercompensate.""",
    },
    {
        "title": "Recovery and Adaptation in Hybrid Athletes",
        "content": """Hybrid training — combining endurance and strength work — requires careful
attention to recovery because the two modalities create different types of fatigue.

The interference effect (also called the concurrent training effect) occurs when
endurance training inhibits strength adaptations. Mechanisms include: AMPK-mTOR
pathway competition, central nervous system fatigue, and glycogen depletion.

Practical guidelines to minimise interference:
- Separate strength and endurance sessions by at least 6-8 hours
- Avoid heavy lower-body strength work before long runs in the same day
- Prioritise the most important modality in the morning slot
- Keep easy runs truly easy to preserve recovery capacity for strength sessions

Sleep is the most powerful recovery tool available. 7-9 hours allows full hormonal
recovery (growth hormone release peaks in slow-wave sleep). Sleep deprivation reduces
power output by up to 11% and increases perceived effort.

Heart Rate Variability (HRV) is a validated marker of autonomic recovery status.
A meaningful drop below baseline HRV suggests incomplete recovery and warrants
reduced training intensity.""",
    },
    {
        "title": "Nutrition for Hybrid Athletes",
        "content": """Hybrid athletes require careful nutrition periodisation to support both
endurance and strength adaptations.

Protein: 1.6-2.2g per kg body weight per day is optimal for muscle protein synthesis.
Distribute intake across 3-4 meals with 30-40g per meal. Leucine threshold (~3g per
meal) is required to maximally stimulate MPS.

Carbohydrates: Primary fuel for high-intensity exercise. Recommended intake scales
with training volume: light day 3-5g/kg, moderate day 5-7g/kg, heavy day 7-10g/kg.
Carbohydrate timing matters — consume 30-60g/hour during runs over 75 minutes.

Fuelling long runs: Start fuelling at 45-60 minutes into a run. Delay leads to
premature glycogen depletion. Practice race nutrition in training to train the gut.

Post-workout nutrition window: Consume protein + carbohydrate within 30-60 minutes
after training to maximise glycogen resynthesis and MPS. This window is especially
important after double-session days.""",
    },
    {
        "title": "Overtraining Recognition and Prevention",
        "content": """Overtraining syndrome (OTS) is a serious condition resulting from excessive
training load without adequate recovery. It can take weeks to months to recover from.

Warning signs (in order of severity):
- Performance plateau or decline despite continued training
- Persistent muscle soreness lasting >72 hours
- Elevated resting heart rate (>5bpm above baseline for 3+ consecutive days)
- Decreased HRV below baseline for 5+ days
- Mood disturbances, increased irritability, loss of motivation
- Sleep disruption despite physical fatigue
- Frequent illness (suppressed immune function)

Functional overreaching (FOR): Short-term performance decrement that resolves with
1-2 weeks of reduced load. This is a normal and desirable part of training periodisation.

Non-functional overreaching (NFOR): Performance decrement requiring weeks to months
of recovery. Distinguish from FOR by duration of recovery needed.

Prevention: Follow periodised training plans, include deload weeks, monitor load
metrics (TSB), track HRV, and prioritise sleep. If TSB drops below -25 for more than
7 consecutive days without a planned peak, reduce load immediately.""",
    },
    {
        "title": "Running Pace Zones and Lactate Threshold Training",
        "content": """Running training zones are defined relative to the lactate threshold (LT) —
the intensity at which blood lactate begins to accumulate faster than it can be cleared.

5-Zone Model:
Zone 1 (Recovery): <70% LT pace. Very easy, active recovery. Promotes blood flow
  and metabolic waste clearance without adding meaningful stress.
Zone 2 (Aerobic): 70-83% LT pace. The aerobic base zone. Should comprise 70-80%
  of all running volume. Builds mitochondrial density.
Zone 3 (Tempo/Threshold): 83-97% LT pace. Lactate threshold training. Raises LT.
  High stimulus but significant fatigue cost. Limit to 10-15% of weekly volume.
Zone 4 (VO2max): 97-105% LT pace. Develops VO2max. Very demanding. 1-2 sessions
  per week maximum during build phase.
Zone 5 (Sprint/Anaerobic): >105% LT pace. Neuromuscular power development.
  Short repetitions only.

Lactate threshold test: Run a 30-minute time trial at maximum sustainable effort.
Average HR in final 20 minutes approximates threshold HR.""",
    },
]


async def seed():
    from app.db.session import AsyncSessionLocal
    from app.rag.chunker import chunk_training_article
    from app.rag.indexer import index_chunks

    print("Connecting to database...")
    async with AsyncSessionLocal() as db:
        total = 0
        for article in ARTICLES:
            chunks = chunk_training_article(
                content=article["content"],
                title=article["title"],
            )
            indexed = await index_chunks(chunks, db, user_id=None, source_type="training_science")
            print(f"  '{article['title']}': {indexed} new chunks indexed")
            total += indexed

        print(f"\nDone. {total} total chunks indexed into knowledge base.")


if __name__ == "__main__":
    asyncio.run(seed())
