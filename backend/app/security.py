import hashlib,hmac,json,time
from datetime import datetime,timedelta,timezone
from urllib.parse import parse_qsl
from fastapi import Header,HTTPException
from jose import JWTError,jwt
from passlib.context import CryptContext
from .config import get_settings
settings=get_settings(); pwd=CryptContext(schemes=["pbkdf2_sha256"],deprecated="auto")
def hash_password(v:str)->str:
    if not v: raise ValueError("Password cannot be empty")
    return pwd.hash(v)
def verify_password(v:str,h:str)->bool:
    try:return bool(v and h and pwd.verify(v,h))
    except Exception:return False
def create_token(subject:str,role:str,minutes:int=1440)->str:
    return jwt.encode({"sub":subject,"role":role,"exp":datetime.now(timezone.utc)+timedelta(minutes=minutes)},settings.jwt_secret,algorithm="HS256")
def decode_token(token:str)->dict:
    try:return jwt.decode(token,settings.jwt_secret,algorithms=["HS256"])
    except JWTError as e:raise HTTPException(401,"Invalid token") from e
def validate_init_data(init_data:str,max_age:int=86400)->dict:
    if settings.dev_auth and not init_data:return {"id":settings.dev_telegram_id,"first_name":"Dev","username":"dev"}
    try:values=dict(parse_qsl(init_data,strict_parsing=True))
    except ValueError as e:raise HTTPException(401,"Invalid Telegram init data") from e
    received=values.pop("hash",None)
    if not received:raise HTTPException(401,"Missing Telegram hash")
    try:auth_date=int(values.get("auth_date","0"))
    except ValueError as e:raise HTTPException(401,"Invalid auth_date") from e
    if abs(int(time.time())-auth_date)>max_age:raise HTTPException(401,"Telegram auth data expired")
    data_check="\n".join(f"{k}={v}" for k,v in sorted(values.items()))
    secret=hmac.new(b"WebAppData",settings.bot_token.encode(),hashlib.sha256).digest()
    calculated=hmac.new(secret,data_check.encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated,received):raise HTTPException(401,"Invalid Telegram signature")
    try:return json.loads(values["user"])
    except Exception as e:raise HTTPException(401,"Missing Telegram user") from e
def bearer_token(authorization:str|None=Header(default=None))->str:
    if not authorization or not authorization.lower().startswith("bearer "):raise HTTPException(401,"Missing bearer token")
    return authorization.split(" ",1)[1].strip()
