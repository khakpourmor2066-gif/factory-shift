from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.access.dependencies import get_current_user
from app.modules.auth_tokens.schema import ApiTokenCreate, ApiTokenCreated, ApiTokenRead
from app.modules.auth_tokens.service import create_api_token, list_api_tokens, revoke_api_token
from app.modules.users.model import User


router = APIRouter(prefix="/auth/tokens", tags=["authentication"])


@router.post("", response_model=ApiTokenCreated)
def create_token_endpoint(
    token_in: ApiTokenCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        token, raw_token = create_api_token(
            db,
            user_id=current_user.id,
            name=token_in.name,
            expires_at=token_in.expires_at,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    token_data = ApiTokenRead.model_validate(token, from_attributes=True)
    return ApiTokenCreated(
        **token_data.model_dump(),
        token=raw_token,
    )


@router.get("", response_model=list[ApiTokenRead])
def list_tokens_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_api_tokens(db, current_user.id)


@router.delete("/{token_id}", response_model=ApiTokenRead)
def revoke_token_endpoint(
    token_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return revoke_api_token(db, current_user.id, token_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
