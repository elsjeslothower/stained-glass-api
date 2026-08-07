"""Auth endpoints: login, logout, and the "am I logged in" check."""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app import schemas
from app.auth import authenticate, require_auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.AuthUser)
def login(payload: schemas.LoginRequest, request: Request):
    if not authenticate(payload.username, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    request.session["authenticated"] = True
    request.session["username"] = payload.username
    return {"username": payload.username}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request):
    request.session.clear()


@router.get("/me", response_model=schemas.AuthUser, dependencies=[Depends(require_auth)])
def me(request: Request):
    return {"username": request.session.get("username")}
