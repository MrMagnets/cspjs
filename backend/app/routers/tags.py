"""标签路由：公开读取，管理员维护。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import ProblemTag, Tag, User
from ..schemas import TagIn, TagOut

router = APIRouter(prefix="/tags", tags=["标签"])


@router.get("", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db)):
    rows = db.scalars(select(Tag).order_by(Tag.category, Tag.id)).all()
    return [TagOut.model_validate(t) for t in rows]


@router.post("", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: TagIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """管理员建标签；普通用户也可补充知识点标签（用于投稿时标记考点）。"""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="标签名不能为空")
    exists = db.scalar(select(Tag).where(Tag.name == name))
    if exists:
        return TagOut.model_validate(exists)
    if user.role != "admin" and payload.category != "知识点":
        raise HTTPException(status_code=403, detail="只有管理员可以创建来源类标签")
    tag = Tag(name=name, category=payload.category or "知识点")
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagOut.model_validate(tag)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="标签不存在")
    for link in db.scalars(select(ProblemTag).where(ProblemTag.tag_id == tag_id)).all():
        db.delete(link)
    db.delete(tag)
    db.commit()
