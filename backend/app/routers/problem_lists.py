"""题单路由：创建、浏览、收录/移除题目、排序。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import get_current_user, get_optional_user
from .models import Problem, ProblemList, ProblemListItem, User
from .schemas import ListItemsIn, ListReorderIn, ProblemListDetail, ProblemListIn, ProblemListSummary
from .serializers import to_summary

router = APIRouter(prefix="/problem-lists", tags=["题单"])


def _get_list(db: Session, list_id: int) -> ProblemList:
    plist = db.get(ProblemList, list_id)
    if plist is None:
        raise HTTPException(status_code=404, detail="题单不存在")
    return plist


def _assert_can_view(plist: ProblemList, user: User | None) -> None:
    if plist.is_public:
        return
    if user is None or (user.role != "admin" and user.id != plist.creator_id):
        raise HTTPException(status_code=403, detail="私有题单仅创建者可见")


def _assert_owner(plist: ProblemList, user: User) -> None:
    if user.role != "admin" and plist.creator_id != user.id:
        raise HTTPException(status_code=403, detail="只有创建者可以修改题单")


def _summary(db: Session, plist: ProblemList, user: User | None) -> ProblemListSummary:
    count = db.scalar(
        select(func.count()).select_from(ProblemListItem).where(ProblemListItem.list_id == plist.id)
    ) or 0
    creator_name = plist.creator.username if plist.creator else None
    return ProblemListSummary(
        id=plist.id,
        title=plist.title,
        description=plist.description,
        creator_id=plist.creator_id,
        creator_name=creator_name,
        is_public=plist.is_public,
        problem_count=count,
        created_at=plist.created_at,
    )


def _detail(db: Session, plist: ProblemList) -> ProblemListDetail:
    rows = db.execute(
        select(Problem, ProblemListItem.order_no)
        .join(ProblemListItem, ProblemListItem.problem_id == Problem.id)
        .where(ProblemListItem.list_id == plist.id, Problem.status == "approved")
        .order_by(ProblemListItem.order_no)
    ).all()
    tags_cache: dict = {}
    problems = [to_summary(db, p, tags_cache) for p, _ in rows]
    base = _summary(db, plist, None)
    return ProblemListDetail(**base.model_dump(), problems=problems)


@router.get("", response_model=list[ProblemListSummary])
def list_problem_lists(
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
    scope: str = Query("visible", description="visible=公开+我的 / public / mine"),
    limit: int = Query(50, ge=1, le=100),
):
    stmt = select(ProblemList)
    if scope == "public":
        stmt = stmt.where(ProblemList.is_public.is_(True))
    elif scope == "mine":
        if user is None:
            raise HTTPException(status_code=401, detail="请先登录")
        stmt = stmt.where(ProblemList.creator_id == user.id)
    else:
        if user is None:
            stmt = stmt.where(ProblemList.is_public.is_(True))
        else:
            stmt = stmt.where(or_(ProblemList.is_public.is_(True), ProblemList.creator_id == user.id))
    rows = db.scalars(stmt.order_by(ProblemList.created_at.desc()).limit(limit)).all()
    return [_summary(db, p, user) for p in rows]


@router.post("", response_model=ProblemListDetail, status_code=status.HTTP_201_CREATED)
def create_problem_list(
    payload: ProblemListIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plist = ProblemList(
        title=payload.title.strip(),
        description=payload.description or "",
        creator_id=user.id,
        is_public=payload.is_public,
    )
    db.add(plist)
    db.flush()
    _replace_items(db, plist, payload.problem_ids)
    db.commit()
    db.refresh(plist)
    return _detail(db, plist)


def _replace_items(db: Session, plist: ProblemList, problem_ids: list[int]) -> None:
    approved = set(
        db.scalars(
            select(Problem.id).where(Problem.id.in_(problem_ids), Problem.status == "approved")
        ).all()
    ) if problem_ids else set()
    ordered: list[int] = []
    for pid in problem_ids:
        if pid in approved and pid not in ordered:
            ordered.append(pid)
    for old in list(plist.items):
        db.delete(old)
    db.flush()
    plist.items = []
    for idx, pid in enumerate(ordered, start=1):
        plist.items.append(ProblemListItem(list_id=plist.id, problem_id=pid, order_no=idx))


@router.get("/{list_id}", response_model=ProblemListDetail)
def get_problem_list(
    list_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    plist = _get_list(db, list_id)
    _assert_can_view(plist, user)
    return _detail(db, plist)


@router.put("/{list_id}", response_model=ProblemListDetail)
def update_problem_list(
    list_id: int,
    payload: ProblemListIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plist = _get_list(db, list_id)
    _assert_owner(plist, user)
    plist.title = payload.title.strip()
    plist.description = payload.description or ""
    plist.is_public = payload.is_public
    if payload.problem_ids:
        _replace_items(db, plist, payload.problem_ids)
    db.commit()
    db.refresh(plist)
    return _detail(db, plist)


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_problem_list(
    list_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plist = _get_list(db, list_id)
    _assert_owner(plist, user)
    db.delete(plist)
    db.commit()


@router.post("/{list_id}/items", response_model=ProblemListDetail)
def add_item(
    list_id: int,
    payload: ListItemsIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plist = _get_list(db, list_id)
    _assert_owner(plist, user)
    problem = db.get(Problem, payload.problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    if problem.status != "approved":
        raise HTTPException(status_code=400, detail="只能收录已通过审核的题目")
    exists = db.scalar(
        select(ProblemListItem).where(
            ProblemListItem.list_id == plist.id, ProblemListItem.problem_id == problem.id
        )
    )
    if exists:
        raise HTTPException(status_code=409, detail="该题目已在题单中")
    next_order = (
        db.scalar(
            select(func.coalesce(func.max(ProblemListItem.order_no), 0)).where(
                ProblemListItem.list_id == plist.id
            )
        )
        or 0
    ) + 1
    db.add(ProblemListItem(list_id=plist.id, problem_id=problem.id, order_no=next_order))
    db.commit()
    db.refresh(plist)
    return _detail(db, plist)


@router.delete("/{list_id}/items/{problem_id}", response_model=ProblemListDetail)
def remove_item(
    list_id: int,
    problem_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plist = _get_list(db, list_id)
    _assert_owner(plist, user)
    item = db.scalar(
        select(ProblemListItem).where(
            ProblemListItem.list_id == list_id, ProblemListItem.problem_id == problem_id
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="题单中没有这道题")
    db.delete(item)
    db.commit()
    db.refresh(plist)
    return _detail(db, plist)


@router.put("/{list_id}/reorder", response_model=ProblemListDetail)
def reorder_items(
    list_id: int,
    payload: ListReorderIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plist = _get_list(db, list_id)
    _assert_owner(plist, user)
    items = {
        item.problem_id: item
        for item in db.scalars(
            select(ProblemListItem).where(ProblemListItem.list_id == list_id)
        ).all()
    }
    for idx, pid in enumerate(payload.problem_ids, start=1):
        if pid in items:
            items[pid].order_no = idx
    db.commit()
    db.refresh(plist)
    return _detail(db, plist)
