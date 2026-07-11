from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from config import SECRET_KEY, ALGORITHM
from database.mysql_db import execute_query

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def create_token(data: dict):
    from datetime import datetime, timedelta
    from config import TOKEN_EXPIRE
    expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = execute_query(
            "SELECT * FROM users WHERE id=%s", (user_id,), fetch=True
        )
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user[0]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def hr_only(user=Depends(get_current_user)):
    if user["role"] != "hr":
        raise HTTPException(status_code=403, detail="HR only")
    return user

def candidate_only(user=Depends(get_current_user)):
    if user["role"] != "candidate":
        raise HTTPException(status_code=403, detail="Candidates only")
    return user