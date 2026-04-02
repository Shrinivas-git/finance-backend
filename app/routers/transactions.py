from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rbac import get_current_user, require_admin
from app.models.transaction import TransactionType
from app.models.user import User
from app.schemas.transaction import (
    PaginatedTransactions,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.services import transaction_service

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post(
    "/",
    response_model=TransactionResponse,
    status_code=201,
    summary="Create a transaction [Admin only]",
)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return transaction_service.create_transaction(db, payload, created_by=current_user.id)


@router.get(
    "/",
    response_model=PaginatedTransactions,
    summary="List transactions with filters [All roles]",
)
def list_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    type: Optional[TransactionType] = Query(None, description="Filter by income or expense"),
    category: Optional[str] = Query(None, description="Filter by category name"),
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),  # any authenticated user
):
    total, items = transaction_service.list_transactions(
        db, page=page, page_size=page_size,
        tx_type=type, category=category,
        date_from=date_from, date_to=date_to,
    )
    return PaginatedTransactions(total=total, page=page, page_size=page_size, items=items)


@router.get(
    "/{tx_id}",
    response_model=TransactionResponse,
    summary="Get a single transaction [All roles]",
)
def get_transaction(
    tx_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return transaction_service.get_transaction(db, tx_id)


@router.patch(
    "/{tx_id}",
    response_model=TransactionResponse,
    summary="Update a transaction [Admin only]",
    dependencies=[Depends(require_admin)],
)
def update_transaction(tx_id: int, payload: TransactionUpdate, db: Session = Depends(get_db)):
    return transaction_service.update_transaction(db, tx_id, payload)


@router.delete(
    "/{tx_id}",
    status_code=204,
    summary="Soft-delete a transaction [Admin only]",
    dependencies=[Depends(require_admin)],
)
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    transaction_service.soft_delete_transaction(db, tx_id)
