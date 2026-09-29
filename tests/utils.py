import uuid
import jwt
from dataclasses import dataclass
from app.core.config import settings

@dataclass
class TestUser:
    user_id: uuid.UUID

async def create_test_user(db_session=None) -> TestUser:
    return TestUser(user_id=uuid.uuid4())

async def get_user_token_headers(user: TestUser, db_session=None) -> dict:
    payload = {
        "sub": str(user.user_id),
        "aud": "authenticated"
    }
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}
