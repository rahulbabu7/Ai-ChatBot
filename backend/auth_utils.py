import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Header, Depends

# JWT settings
SECRET_KEY = "your_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

def create_jwt(client_id: str) -> str:
    """Create a JWT token for the given client_id"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"client_id": client_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_jwt(token: str) -> str:
    """Verify JWT token and return client_id"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["client_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_client_from_header(x_token: str = Header(None)) -> str:
    """FastAPI dependency to extract client_id from JWT token in header"""
    if not x_token:
        raise HTTPException(status_code=401, detail="Missing token")
    return verify_jwt(x_token)