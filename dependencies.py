from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database.supabase_client import get_supabase
from supabase import Client

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    supabase: Client = Depends(get_supabase),
) -> dict:
    """
    Validates the JWT sent in the Authorization: Bearer <token> header.
    Uses Supabase's built-in token verification — no separate JWT secret needed.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        response = supabase.auth.get_user(token)
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token. Please sign in again.",
            )
        return {"user": response.user, "token": token}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    supabase: Client = Depends(get_supabase),
) -> dict | None:
    """Same as get_current_user but returns None instead of raising for public routes."""
    if not credentials:
        return None
    try:
        response = supabase.auth.get_user(credentials.credentials)
        if response and response.user:
            return {"user": response.user, "token": credentials.credentials}
    except Exception:
        pass
    return None
