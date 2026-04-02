from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionType
from app.schemas.transaction import TransactionCreate, TransactionUpdate


def create_transaction(db: Session, payload: TransactionCreate, created_by: int) -> Transaction:
    tx = Transaction(**payload.model_dump(), created_by=created_by)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def get_transaction(db: Session, tx_id: int) -> Transaction:
    tx = db.get(Transaction, tx_id)
    if tx is None or tx.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    return tx


def list_transactions(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    tx_type: Optional[TransactionType] = None,
    category: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> tuple[int, list[Transaction]]:
    """Return (total_count, paginated_items). Excludes soft-deleted records."""
    query = db.query(Transaction).filter(Transaction.is_deleted == False)  # noqa: E712

    if tx_type:
        query = query.filter(Transaction.type == tx_type)
    if category:
        query = query.filter(Transaction.category == category.strip().lower())
    if date_from:
        query = query.filter(Transaction.date >= date_from)
    if date_to:
        query = query.filter(Transaction.date <= date_to)

    total = query.count()
    items = (
        query.order_by(Transaction.date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return total, items


def update_transaction(db: Session, tx_id: int, payload: TransactionUpdate) -> Transaction:
    tx = get_transaction(db, tx_id)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tx, field, value)
    db.commit()
    db.refresh(tx)
    return tx


def soft_delete_transaction(db: Session, tx_id: int) -> None:
    """
    Soft delete: marks the record as deleted instead of removing it from the DB.
    This preserves data integrity and audit trails.
    """
    tx = get_transaction(db, tx_id)
    tx.is_deleted = True
    db.commit()
