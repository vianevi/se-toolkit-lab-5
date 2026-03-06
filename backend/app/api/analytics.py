from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text
from app.database import get_session

# Создаем роутер для аналитических эндпоинтов
router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/scores")
async def get_scores_histogram(
    lab: str = Query(..., description="Lab identifier, e.g. lab-04"),
    session: AsyncSession = Depends(get_session)
):
    """Returns distribution of scores in four buckets."""
    # Find lab
    lab_result = await session.execute(
        text("SELECT id FROM item WHERE title LIKE :lab_pattern AND type = 'lab'"),
        {"lab_pattern": f"%{lab}%"}
    )
    lab_row = lab_result.first()
    
    if not lab_row:
        return [{"bucket": b, "count": 0} for b in ["0-25", "26-50", "51-75", "76-100"]]
    
    lab_id = lab_row[0]
    
    # Find tasks
    tasks_result = await session.execute(
        text("SELECT id FROM item WHERE parent_id = :lab_id AND type = 'task'"),
        {"lab_id": lab_id}
    )
    task_ids = [row[0] for row in tasks_result.all()]
    
    if not task_ids:
        return [{"bucket": b, "count": 0} for b in ["0-25", "26-50", "51-75", "76-100"]]
    
    # Get stats
    query = text("""
        SELECT 
            CASE 
                WHEN score <= 25 THEN '0-25'
                WHEN score <= 50 THEN '26-50'
                WHEN score <= 75 THEN '51-75'
                ELSE '76-100'
            END as bucket,
            COUNT(*) as count
        FROM interactionlog
        WHERE item_id = ANY(:task_ids)
            AND score IS NOT NULL
        GROUP BY bucket
    """)
    
    result = await session.execute(query, {"task_ids": task_ids})
    counts = {row[0]: row[1] for row in result.all()}
    
    buckets = ["0-25", "26-50", "51-75", "76-100"]
    return [{"bucket": b, "count": counts.get(b, 0)} for b in buckets]

@router.get("/pass-rates")
async def get_pass_rates(
    lab: str = Query(..., description="Lab identifier, e.g. lab-04"),
    session: AsyncSession = Depends(get_session)
):
    """Returns per-task statistics."""
    # Find lab
    lab_result = await session.execute(
        text("SELECT id FROM item WHERE title LIKE :lab_pattern AND type = 'lab'"),
        {"lab_pattern": f"%{lab}%"}
    )
    lab_row = lab_result.first()
    
    if not lab_row:
        return []
    
    lab_id = lab_row[0]
    
    # Get task stats
    query = text("""
        SELECT 
            i.title as task,
            ROUND(COALESCE(AVG(il.score), 0)::numeric, 1) as avg_score,
            COUNT(il.id) as attempts
        FROM item i
        LEFT JOIN interactionlog il ON i.id = il.item_id AND il.score IS NOT NULL
        WHERE i.parent_id = :lab_id
            AND i.type = 'task'
        GROUP BY i.id, i.title
        ORDER BY i.title
    """)
    
    result = await session.execute(query, {"lab_id": lab_id})
    
    return [
        {"task": row[0], "avg_score": float(row[1]) if row[1] else 0, "attempts": row[2]}
        for row in result.all()
    ]

@router.get("/timeline")
async def get_timeline(
    lab: str = Query(..., description="Lab identifier, e.g. lab-04"),
    session: AsyncSession = Depends(get_session)
):
    """Returns submissions per day."""
    # Find lab
    lab_result = await session.execute(
        text("SELECT id FROM item WHERE title LIKE :lab_pattern AND type = 'lab'"),
        {"lab_pattern": f"%{lab}%"}
    )
    lab_row = lab_result.first()
    
    if not lab_row:
        return []
    
    lab_id = lab_row[0]
    
    # Find tasks
    tasks_result = await session.execute(
        text("SELECT id FROM item WHERE parent_id = :lab_id AND type = 'task'"),
        {"lab_id": lab_id}
    )
    task_ids = [row[0] for row in tasks_result.all()]
    
    if not task_ids:
        return []
    
    # Timeline
    query = text("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as submissions
        FROM interactionlog
        WHERE item_id = ANY(:task_ids)
        GROUP BY DATE(created_at)
        ORDER BY date ASC
    """)
    
    result = await session.execute(query, {"task_ids": task_ids})
    
    return [
        {"date": str(row[0]), "submissions": row[1]}
        for row in result.all()
    ]

@router.get("/groups")
async def get_groups(
    lab: str = Query(..., description="Lab identifier, e.g. lab-04"),
    session: AsyncSession = Depends(get_session)
):
    """Returns per-group performance."""
    # Find lab
    lab_result = await session.execute(
        text("SELECT id FROM item WHERE title LIKE :lab_pattern AND type = 'lab'"),
        {"lab_pattern": f"%{lab}%"}
    )
    lab_row = lab_result.first()
    
    if not lab_row:
        return []
    
    lab_id = lab_row[0]
    
    # Find tasks
    tasks_result = await session.execute(
        text("SELECT id FROM item WHERE parent_id = :lab_id AND type = 'task'"),
        {"lab_id": lab_id}
    )
    task_ids = [row[0] for row in tasks_result.all()]
    
    if not task_ids:
        return []
    
    # Group stats
    query = text("""
        SELECT 
            COALESCE(l.student_group, 'Unknown') as group,
            ROUND(COALESCE(AVG(il.score), 0)::numeric, 1) as avg_score,
            COUNT(DISTINCT l.id) as students
        FROM interactionlog il
        JOIN learner l ON il.learner_id = l.id
        WHERE il.item_id = ANY(:task_ids)
            AND il.score IS NOT NULL
        GROUP BY l.student_group
        ORDER BY l.student_group
    """)
    
    result = await session.execute(query, {"task_ids": task_ids})
    
    return [
        {"group": row[0], "avg_score": float(row[1]), "students": row[2]}
        for row in result.all()
    ]
