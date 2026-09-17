import jwt
from uuid import uuid4
import datetime

# Must match settings.SUPABASE_JWT_SECRET
SECRET = "super-secret-jwt-token-for-supabase-local-dev-only"

user_id = str(uuid4())
payload = {
    "sub": user_id,
    "aud": "authenticated",
    "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
}

token = jwt.encode(payload, SECRET, algorithm="HS256")

print(f"Generated Test User ID: {user_id}")
print(f"Generated JWT Token:\n{token}\n")
print("To test the API manually:")
print("1. Start Docker services: docker-compose up -d")
print("2. Run database migrations: alembic upgrade head")
print("3. Start the API server: uvicorn app.main:app --reload")
print("4. Start the background worker (in another terminal): python -m arq app.workers.settings.WorkerSettings")
print("5. Open http://localhost:8000/docs in your browser.")
print("6. Click 'Authorize' and paste the token above to authenticate.")
