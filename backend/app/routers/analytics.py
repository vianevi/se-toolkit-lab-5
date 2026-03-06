from fastapi import APIRouter, Depends, Query
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.item import ItemRecord
from app.models.learner import Learner
from app.models.interaction import InteractionLog

router = APIRouter()


def _normalize_lab_pattern(lab: str) -> str:
    """Normalize lab identifier for matching against titles.
    
    Converts 'lab-04' to 'lab 04' pattern for matching.
    """
    # Replace hyphens with spaces for matching
    return lab.replace("-", " ")


@router.get("/scores")
async def get_scores_histogram(
    lab: str = Query(..., description="Lab identifier, e.g. lab-04"),
    session: AsyncSession = Depends(get_session)
):
    """Returns distribution of scores in four buckets."""
    # Find lab by title pattern
    lab_pattern = _normalize_lab_pattern(lab)
    lab_result = await session.exec(
        select(ItemRecord).where(
            ItemRecord.type == "lab",
            ItemRecord.title.ilike(f"%{lab_pattern}%")
        )
    )
    lab_record = lab_result.first()

    if not lab_record:
        return [{"bucket": b, "count": 0} for b in ["0-25", "26-50", "51-75", "76-100"]]

    lab_id = lab_record.id

    # Find all tasks under this lab
    tasks_result = await session.exec(
        select(ItemRecord.id).where(
            ItemRecord.parent_id == lab_id,
            ItemRecord.type == "task"
        )
    )
    task_ids = list(tasks_result)

    if not task_ids:
        return [{"bucket": b, "count": 0} for b in ["0-25", "26-50", "51-75", "76-100"]]

    # Get all interactions for these tasks with non-null scores
    interactions_result = await session.exec(
        select(InteractionLog.score).where(
            InteractionLog.item_id.in_(task_ids),
            InteractionLog.score.isnot(None)
        )
    )
    scores = list(interactions_result)

    # Count scores in each bucket
    buckets = {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
    for score in scores:
        if score <= 25:
            buckets["0-25"] += 1
        elif score <= 50:
            buckets["26-50"] += 1
        elif score <= 75:
            buckets["51-75"] += 1
        else:
            buckets["76-100"] += 1

    return [{"bucket": b, "count": buckets[b]} for b in ["0-25", "26-50", "51-75", "76-100"]]


@router.get("/pass-rates")
async def get_pass_rates(
    lab: str = Query(..., description="Lab identifier, e.g. lab-04"),
    session: AsyncSession = Depends(get_session)
):
    """Returns per-task statistics."""
    # Find lab by title pattern
    lab_pattern = _normalize_lab_pattern(lab)
    lab_result = await session.exec(
        select(ItemRecord).where(
            ItemRecord.type == "lab",
            ItemRecord.title.ilike(f"%{lab_pattern}%")
        )
    )
    lab_record = lab_result.first()

    if not lab_record:
        return []

    lab_id = lab_record.id

    # Get all tasks under this lab
    tasks_result = await session.exec(
        select(ItemRecord).where(
            ItemRecord.parent_id == lab_id,
            ItemRecord.type == "task"
        )
    )
    tasks = tasks_result.all()

    result = []
    for task in tasks:
        # Get interactions for this task with non-null scores
        interactions_result = await session.exec(
            select(InteractionLog.score).where(
                InteractionLog.item_id == task.id,
                InteractionLog.score.isnot(None)
            )
        )
        scores = list(interactions_result)

        attempts = len(scores)
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        result.append({
            "task": task.title,
            "avg_score": avg_score,
            "attempts": attempts
        })

    return result


@router.get("/timeline")
async def get_timeline(
    lab: str = Query(..., description="Lab identifier, e.g. lab-04"),
    session: AsyncSession = Depends(get_session)
):
    """Returns submissions per day."""
    # Find lab by title pattern
    lab_pattern = _normalize_lab_pattern(lab)
    lab_result = await session.exec(
        select(ItemRecord).where(
            ItemRecord.type == "lab",
            ItemRecord.title.ilike(f"%{lab_pattern}%")
        )
    )
    lab_record = lab_result.first()

    if not lab_record:
        return []

    lab_id = lab_record.id

    # Find all tasks under this lab
    tasks_result = await session.exec(
        select(ItemRecord.id).where(
            ItemRecord.parent_id == lab_id,
            ItemRecord.type == "task"
        )
    )
    task_ids = list(tasks_result)

    if not task_ids:
        return []

    # Get all interactions for these tasks
    interactions_result = await session.exec(
        select(InteractionLog.created_at).where(
            InteractionLog.item_id.in_(task_ids)
        )
    )
    created_ats = list(interactions_result)

    # Group by date
    date_counts: dict[str, int] = {}
    for created_at in created_ats:
        date_str = created_at.strftime("%Y-%m-%d")
        date_counts[date_str] = date_counts.get(date_str, 0) + 1

    # Sort by date and return
    sorted_dates = sorted(date_counts.keys())
    return [{"date": d, "submissions": date_counts[d]} for d in sorted_dates]


@router.get("/groups")
async def get_groups(
    lab: str = Query(..., description="Lab identifier, e.g. lab-04"),
    session: AsyncSession = Depends(get_session)
):
    """Returns per-group performance."""
    # Find lab by title pattern
    lab_pattern = _normalize_lab_pattern(lab)
    lab_result = await session.exec(
        select(ItemRecord).where(
            ItemRecord.type == "lab",
            ItemRecord.title.ilike(f"%{lab_pattern}%")
        )
    )
    lab_record = lab_result.first()

    if not lab_record:
        return []

    lab_id = lab_record.id

    # Find all tasks under this lab
    tasks_result = await session.exec(
        select(ItemRecord.id).where(
            ItemRecord.parent_id == lab_id,
            ItemRecord.type == "task"
        )
    )
    task_ids = list(tasks_result)

    if not task_ids:
        return []

    # Get all interactions with scores for these tasks, joined with learner info
    interactions_result = await session.exec(
        select(InteractionLog.score, Learner.student_group, Learner.id).join(
            Learner, InteractionLog.learner_id == Learner.id
        ).where(
            InteractionLog.item_id.in_(task_ids),
            InteractionLog.score.isnot(None)
        )
    )
    rows = interactions_result.all()

    # Group by student_group
    group_data: dict[str, dict] = {}
    for score, group, learner_id in rows:
        if group not in group_data:
            group_data[group] = {"scores": [], "learner_ids": set()}
        group_data[group]["scores"].append(score)
        group_data[group]["learner_ids"].add(learner_id)

    result = []
    for group, data in group_data.items():
        avg_score = round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else 0.0
        result.append({
            "group": group,
            "avg_score": avg_score,
            "students": len(data["learner_ids"])
        })

    # Sort by group name
    result.sort(key=lambda x: x["group"])
    return result
