# GATES: 18 - Hybrid Retrieval Service

- [ ] `pgvector` extension is enabled in Postgres.
  CHECK: powershell -c "venv\Scripts\python -c \"import asyncio; from sqlalchemy import text; from app.core.database import engine; async def main(): async with engine.connect() as conn: res = await conn.execute(text('SELECT extname FROM pg_extension WHERE extname = ''vector''')); print(res.scalar()); asyncio.run(main())\""
  EXPECT: vector
  EVIDENCE: pending
- [ ] `document_blocks` table has `embedding` column of type `vector`.
  CHECK: powershell -c "venv\Scripts\python -c \"import asyncio; from sqlalchemy import text; from app.core.database import engine; async def main(): async with engine.connect() as conn: res = await conn.execute(text('SELECT data_type FROM information_schema.columns WHERE table_name = ''document_blocks'' AND column_name = ''embedding''')); print(res.scalar()); asyncio.run(main())\""
  EXPECT: USER-DEFINED
  EVIDENCE: pending
- [ ] `document_blocks` table has `search_vector` column of type `tsvector`.
  CHECK: powershell -c "venv\Scripts\python -c \"import asyncio; from sqlalchemy import text; from app.core.database import engine; async def main(): async with engine.connect() as conn: res = await conn.execute(text('SELECT data_type FROM information_schema.columns WHERE table_name = ''document_blocks'' AND column_name = ''search_vector''')); print(res.scalar()); asyncio.run(main())\""
  EXPECT: tsvector
  EVIDENCE: pending
- [ ] `HybridRetrievalService` is implemented.
  CHECK: powershell -c "Test-Path app/services/hybrid_retrieval.py"
  EXPECT: True
  EVIDENCE: pending
- [ ] Unit tests for `HybridRetrievalService` pass.
  CHECK: venv\Scripts\python -m pytest tests/test_hybrid_retrieval.py
  EXPECT: pass
  EVIDENCE: pending
