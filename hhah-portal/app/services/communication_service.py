"""Communication threads and messages."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.models.communication import CommunicationMessage, CommunicationThread


def list_threads(
    db: Session,
    *,
    org_id: UUID,
    user_id: UUID,
    unread_only: bool = False,
    limit: int = 50,
) -> list[CommunicationThread]:
    stmt = select(CommunicationThread).where(
        CommunicationThread.org_id == org_id,
        CommunicationThread.deleted_at.is_(None),
    ).order_by(CommunicationThread.last_message_at.desc().nullslast()).limit(limit)
    return list(db.scalars(stmt))


def get_thread(db: Session, *, org_id: UUID, thread_id: UUID) -> Optional[CommunicationThread]:
    return db.scalar(
        select(CommunicationThread).where(
            CommunicationThread.id == thread_id,
            CommunicationThread.org_id == org_id,
            CommunicationThread.deleted_at.is_(None),
        )
    )


def list_messages(db: Session, *, thread_id: UUID) -> list[CommunicationMessage]:
    return list(db.scalars(
        select(CommunicationMessage)
        .where(
            CommunicationMessage.thread_id == thread_id,
            CommunicationMessage.deleted_at.is_(None),
        )
        .order_by(CommunicationMessage.sent_at.asc())
    ))


def create_thread(
    db: Session,
    *,
    org_id: UUID,
    user_id: UUID,
    subject: str,
    body: str,
    linked_patient_ids: Optional[list[UUID]] = None,
    linked_document_ids: Optional[list[UUID]] = None,
) -> CommunicationThread:
    now = datetime.now(timezone.utc)
    th = CommunicationThread(
        org_id=org_id,
        subject=subject,
        counterparty="us",
        status="open",
        linked_patient_ids=linked_patient_ids or None,
        linked_document_ids=linked_document_ids or None,
        last_message_at=now,
        last_message_preview=body[:240],
    )
    db.add(th)
    db.flush()

    msg = CommunicationMessage(
        org_id=org_id,
        thread_id=th.id,
        sender_user_id=user_id,
        direction="outbound",
        body=body,
        sent_at=now,
    )
    db.add(msg)
    db.flush()

    write_audit(db, org_id=org_id, actor_user_id=user_id,
                action_type="thread.created", subject_type="thread", subject_id=th.id,
                subject_label=subject)
    return th


def reply(
    db: Session,
    *,
    org_id: UUID,
    user_id: UUID,
    thread_id: UUID,
    body: str,
) -> CommunicationMessage:
    th = get_thread(db, org_id=org_id, thread_id=thread_id)
    if not th:
        raise LookupError("thread not found")
    now = datetime.now(timezone.utc)
    msg = CommunicationMessage(
        org_id=org_id, thread_id=thread_id, sender_user_id=user_id,
        direction="outbound", body=body, sent_at=now,
    )
    db.add(msg)
    th.last_message_at = now
    th.last_message_preview = body[:240]
    write_audit(db, org_id=org_id, actor_user_id=user_id,
                action_type="thread.replied", subject_type="thread", subject_id=thread_id)
    return msg
