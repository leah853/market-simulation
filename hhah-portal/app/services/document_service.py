"""Document queries — Care Coordination Documents hub.

Two tabs:
  - signature_required = "Docs needing Phy Signatures"
  - other              = "Other Care Coordination Docs"
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document import Comment, Document
from app.models.flag import Flag
from app.models.patient import Patient
from app.models.practitioner import Practitioner

Tab = Literal["signature_required", "other"]


@dataclass(slots=True)
class DocumentRow:
    document: Document
    patient: Optional[Patient]
    practitioner: Optional[Practitioner]
    flag_count: int


def list_documents(
    db: Session,
    *,
    org_id: UUID,
    tab: Tab,
    patient_id: Optional[UUID] = None,
    practitioner_id: Optional[UUID] = None,
    flagged_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[DocumentRow]:
    stmt = select(Document).where(
        Document.org_id == org_id,
        Document.deleted_at.is_(None),
        Document.signature_required.is_(tab == "signature_required"),
    )
    if patient_id:
        stmt = stmt.where(Document.patient_id == patient_id)
    if practitioner_id:
        stmt = stmt.where(Document.owner_practitioner_id == practitioner_id)
    stmt = stmt.order_by(Document.created_at.desc()).limit(limit).offset(offset)

    docs = list(db.scalars(stmt))
    rows: list[DocumentRow] = []
    for d in docs:
        flag_count = db.scalar(
            select(func.count(Flag.id)).where(
                Flag.org_id == org_id,
                Flag.subject_type.in_(["f2f", "plan_of_care_485", "order"]),
                Flag.subject_id == d.id,
                Flag.status.in_(["open", "acknowledged", "escalated"]),
                Flag.deleted_at.is_(None),
            )
        ) or 0
        if flagged_only and flag_count == 0:
            continue
        pt = db.get(Patient, d.patient_id) if d.patient_id else None
        pr = db.get(Practitioner, d.owner_practitioner_id) if d.owner_practitioner_id else None
        rows.append(DocumentRow(document=d, patient=pt, practitioner=pr, flag_count=flag_count))
    return rows


def get_document(db: Session, *, org_id: UUID, document_id: UUID) -> Optional[Document]:
    return db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.org_id == org_id,
            Document.deleted_at.is_(None),
        )
    )


def list_comments(db: Session, *, document_id: UUID) -> list[Comment]:
    return list(db.scalars(
        select(Comment)
        .where(
            Comment.subject_type == "document",
            Comment.subject_id == document_id,
            Comment.deleted_at.is_(None),
        )
        .order_by(Comment.created_at.asc())
    ))


def add_comment(
    db: Session,
    *,
    org_id: UUID,
    user_id: UUID,
    document_id: UUID,
    body: str,
) -> Comment:
    c = Comment(
        org_id=org_id,
        subject_type="document",
        subject_id=document_id,
        author_user_id=user_id,
        body=body,
    )
    db.add(c)
    db.flush()
    return c


def tab_counts(db: Session, *, org_id: UUID) -> dict[str, int]:
    sig = db.scalar(
        select(func.count(Document.id)).where(
            Document.org_id == org_id,
            Document.signature_required.is_(True),
            Document.deleted_at.is_(None),
        )
    ) or 0
    other = db.scalar(
        select(func.count(Document.id)).where(
            Document.org_id == org_id,
            Document.signature_required.is_(False),
            Document.deleted_at.is_(None),
        )
    ) or 0
    return {"signature_required": sig, "other": other}
