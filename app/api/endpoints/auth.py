from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import create_access_token, get_current_user, verify_password
from app.core.config import get_settings

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class VerifyResponse(BaseModel):
    username: str
    valid: bool

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    settings = get_settings()
    
    if req.username != settings.admin_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
        
    if not verify_password(req.password, settings.admin_password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
        
    access_token = create_access_token(data={"sub": req.username})
    return TokenResponse(access_token=access_token, token_type="bearer")

@router.get("/verify", response_model=VerifyResponse)
async def verify(username: str = Depends(get_current_user)):
    return VerifyResponse(username=username, valid=True)
