from fastapi import APIRouter, HTTPException, Depends, status
from supabase import Client
from database.supabase_client import get_supabase, get_supabase_admin
from models.schemas import SignupRequest, LoginRequest, AuthResponse, UserProfile, MessageResponse
from dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest):
    """
    Register a new facility account.
    Creates a Supabase Auth user and stores extra profile info in the `profiles` table.
    """
    admin = get_supabase_admin()

    # 1. Create auth user
    try:
        auth_resp = admin.auth.sign_up({
            "email": payload.email,
            "password": payload.password,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not auth_resp.user:
        raise HTTPException(status_code=400, detail="Registration failed. Please try again.")

    user_id = auth_resp.user.id

    # 2. Insert profile row
    profile_data = {
        "id": user_id,
        "email": payload.email,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "facility_name": payload.facility_name,
        "country": payload.country,
        "account_type": payload.account_type.value,
    }

    try:
        admin.table("profiles").insert(profile_data).execute()
    except Exception as e:
        # Auth user created but profile failed — clean up
        admin.auth.admin.delete_user(user_id)
        raise HTTPException(status_code=500, detail="Failed to create profile. Please try again.")

    # 3. Sign in to get access token
    try:
        sign_in = admin.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password,
        })
    except Exception:
        raise HTTPException(status_code=500, detail="Account created. Please sign in.")

    return AuthResponse(
        access_token=sign_in.session.access_token,
        user_id=user_id,
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        facility_name=payload.facility_name,
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest):
    """
    Sign in with email & password. Returns a JWT access token.
    """
    admin = get_supabase_admin()

    try:
        sign_in = admin.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password,
        })
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not sign_in.session:
        raise HTTPException(status_code=401, detail="Login failed.")

    user_id = sign_in.user.id

    # Fetch profile
    try:
        profile_resp = admin.table("profiles").select("*").eq("id", user_id).single().execute()
        profile = profile_resp.data
    except Exception:
        profile = {}

    return AuthResponse(
        access_token=sign_in.session.access_token,
        user_id=user_id,
        email=sign_in.user.email,
        first_name=profile.get("first_name", ""),
        last_name=profile.get("last_name", ""),
        facility_name=profile.get("facility_name", ""),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(auth: dict = Depends(get_current_user)):
    """
    Invalidate the current session token.
    """
    supabase = get_supabase_admin()
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=UserProfile)
async def get_profile(auth: dict = Depends(get_current_user)):
    """
    Return the currently authenticated user's profile.
    """
    user_id = auth["user"].id
    admin = get_supabase_admin()

    try:
        resp = admin.table("profiles").select("*").eq("id", user_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Profile not found.")

    p = resp.data
    return UserProfile(
        id=user_id,
        email=p.get("email", auth["user"].email),
        first_name=p.get("first_name", ""),
        last_name=p.get("last_name", ""),
        facility_name=p.get("facility_name", ""),
        country=p.get("country", "Ghana"),
        account_type=p.get("account_type", "hospital"),
        created_at=p.get("created_at"),
    )
