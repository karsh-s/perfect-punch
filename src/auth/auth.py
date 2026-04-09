import requests
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

TENANT_SUBDOMAIN = "perfectpunch"
CLIENT_ID = "d56c0e7f-056f-4607-b385-4c4e6ce58489"  # from Azure App Registration

JWKS_URL = f"https://{TENANT_SUBDOMAIN}.ciamlogin.com/{TENANT_SUBDOMAIN}.onmicrosoft.com/discovery/v2.0/keys"
ISSUER   = f"https://{TENANT_SUBDOMAIN}.ciamlogin.com/{TENANT_SUBDOMAIN}.onmicrosoft.com/v2.0"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        logger.info(f"🔍 Token received: {token[:50]}...")
        jwks = requests.get(JWKS_URL).json()
        payload = jwt.decode(
            token, jwks,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=ISSUER
        )
        logger.info(f"✅ User authenticated: {payload.get('oid')}")
        return payload
    except JWTError as e:
        logger.error(f"❌ JWT Error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
