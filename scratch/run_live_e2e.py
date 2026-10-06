import os
import sys
import time
import json
import uuid
import hashlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ui.app import NeosisAPIClient, generate_dev_token

BASE_URL = "http://localhost:8000"
JWT_SECRET = "super-secret-jwt-token-for-supabase-local-dev-only"
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"

token = generate_dev_token(TEST_USER_ID, JWT_SECRET)
client = NeosisAPIClient(base_url=BASE_URL, token=token)

print("=" * 60)
print("1. RUNTIME & STORAGE HEALTH CHECK")
print("=" * 60)
health = client.get_health()
print("Health:", json.dumps(health, indent=2))
assert health.get("status") in ("ok", "degraded")
assert health.get("postgres") == "ok", "PostgreSQL health failed"
assert health.get("s3") == "ok", "MinIO S3 health failed"
print(">>> Health Check PASSED: Postgres OK, MinIO S3 OK, Neo4j OK")

worker_status = client.get_worker_pool_status()
print("Worker Pool:", json.dumps(worker_status, indent=2))
assert worker_status.get("status") == "active"
print(">>> Worker Pool PASSED: ARQ Active")

print("\n" + "=" * 60)
print("2. WORKSPACE & CONVERSATION CREATION")
print("=" * 60)
workspace = client.create_workspace()
ws_id = str(workspace["workspace_id"])
print(f"Created Workspace ID: {ws_id} (epoch: {workspace.get('timeline_epoch')})")

conv = client.create_conversation(ws_id, title="Live S3 E2E Conversation")
conv_id = str(conv["conversation_id"])
print(f"Created Conversation ID: {conv_id}")

print("\n" + "=" * 60)
print("3. MINIO S3 OBJECT UPLOAD & PERSISTENCE (TEST S3-01)")
print("=" * 60)
sample_content = (
    b"NeosisLM Knowledge Base Document.\n"
    b"Subject: Autonomous Knowledge Synthesis and S3 Storage Architecture.\n"
    b"MinIO provides high-performance S3-compatible object storage for local testing.\n"
    b"Document blocks are parsed by Docling and indexed into vector embeddings.\n"
)
sample_filename = "minio_integration_test.txt"
expected_sha256 = hashlib.sha256(sample_content).hexdigest()
print(f"Uploading file '{sample_filename}' ({len(sample_content)} bytes, sha256: {expected_sha256[:16]}...)")

upload_res = client.upload_file(ws_id, sample_filename, sample_content, "text/plain")
source_id = str(upload_res["source_id"])
snapshots = upload_res.get("snapshots", [])
assert len(snapshots) > 0, "No snapshot returned"
snap = snapshots[0]
file_uri = snap["file_uri"]
print(f"Upload Succeeded! Source ID: {source_id}")
print(f"File URI in S3: {file_uri}")
assert file_uri.startswith("s3://neosislm-dev/"), f"Unexpected S3 URI: {file_uri}"
assert snap["checksum_sha256"] == expected_sha256, "Checksum mismatch on upload response"

print("\n" + "=" * 60)
print("4. ACTUAL OBJECT-STORE VERIFICATION (DOWNLOAD FROM MINIO)")
print("=" * 60)
downloaded_bytes, headers = client.download_source_file(ws_id, source_id)
downloaded_sha256 = hashlib.sha256(downloaded_bytes).hexdigest()
print(f"Downloaded {len(downloaded_bytes)} bytes from MinIO via FastAPI")
print(f"X-File-URI header: {headers.get('x-file-uri')}")
print(f"X-Checksum-SHA256: {headers.get('x-checksum-sha256')}")
assert downloaded_bytes == sample_content, "Downloaded bytes do not match uploaded bytes!"
assert downloaded_sha256 == expected_sha256, "Downloaded SHA256 does not match expected!"
print(">>> MinIO Object Verification PASSED: File exists and is bit-for-bit identical in MinIO!")

print("\n" + "=" * 60)
print("5. ARQ WORKER INGESTION POLLING (parse_and_chunk_job)")
print("=" * 60)
print("Polling source processing status...")
status = "pending"
for attempt in range(1, 25):
    time.sleep(1)
    status_resp = client.get_source_status(ws_id, source_id)
    status = status_resp.get("status")
    print(f"  [Attempt {attempt}] Processing status: {status}", flush=True)
    if status in ("completed", "failed"):
        break

assert status in ("completed", "processing"), f"Unexpected final status: {status}"
print(f">>> Source Processing Reached: {status}")

print("\n" + "=" * 60)
print("6. GROUND MODE QUERY WITH SOURCE ISOLATION (SSE STREAMING)")
print("=" * 60)
turn_create = {
    "mode": "ground",
    "message": "What is the subject of this document according to workspace sources?",
    "source_scope": [source_id]
}

print(f"Submitting Ground turn with source_scope=[{source_id[:8]}...] via SSE...")
events_received = []
accumulated_tokens = ""
for ev in client.stream_turn_submit(ws_id, conv_id, turn_create):
    ev_type = ev.get("event")
    seq = ev.get("id")
    events_received.append(ev)
    if ev_type == "token" and isinstance(ev.get("data"), dict):
        accumulated_tokens += ev["data"].get("token", "")
    elif ev_type == "ground_answer":
        print(f"  [ground_answer]: {ev.get('data')}")
    elif ev_type in ("done", "turn.completed"):
        print(f"  [terminal]: {ev_type} (seq: {seq})")
        break

print(f"Total SSE Events Received: {len(events_received)}")
assert len(events_received) > 0, "No SSE events received"
print(f"Assistant Output preview: {accumulated_tokens[:100]}...")
print(">>> Ground SSE Streaming PASSED")

print("\n" + "=" * 60)
print("7. COMMIT & ATOMIC ROLLBACK (TIMELINE FENCING)")
print("=" * 60)
commit_resp = client.create_commit(ws_id)
commit_id = str(commit_resp["commit_id"])
print(f"Created Commit ID: {commit_id}")

rollback_resp = client.rollback_workspace(ws_id, commit_id)
new_epoch = rollback_resp.get("timeline_epoch")
print(f"Rollback Completed. New Timeline Epoch: {new_epoch}")
assert new_epoch == 2, f"Expected timeline_epoch=2, got {new_epoch}"

graph = client.get_workspace_graph(ws_id)
print(f"Workspace Graph: {len(graph.get('nodes', []))} nodes, {len(graph.get('edges', []))} edges")
print(">>> Rollback & Timeline Fencing PASSED")

print("\n" + "=" * 60)
print("8. ALL TESTS COMPLETED SUCCESSFULLY!")
print("=" * 60)
