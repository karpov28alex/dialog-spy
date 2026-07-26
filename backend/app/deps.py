from fastapi import Depends,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from .db import get_db
from .models import User,Admin
from .security import bearer_token,decode_token
async def current_user(token:str=Depends(bearer_token),db:AsyncSession=Depends(get_db))->User:
    p=decode_token(token)
    if p.get("role")!="user":raise HTTPException(403,"User token required")
    u=await db.get(User,int(p["sub"]))
    if not u:raise HTTPException(401,"User not found")
    return u
async def current_admin(token:str=Depends(bearer_token),db:AsyncSession=Depends(get_db))->Admin:
    p=decode_token(token)
    if p.get("role")!="admin":raise HTTPException(403,"Admin token required")
    a=await db.get(Admin,int(p["sub"]))
    if not a or not a.is_active:raise HTTPException(401,"Admin not found")
    return a
