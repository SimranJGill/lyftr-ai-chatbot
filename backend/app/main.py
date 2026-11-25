import json
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from .config import settings
from .database import init_db, SessionLocal, engine
from .schemas import ChatRequest
from .services.litellm_service import generate, AllProvidersUnavailable

app = FastAPI(title="Lyftr AI Chat API", version="1.0.0",
              description="A resilient multi-turn LLM chat service with key failover and caching.")
app.add_middleware(
    CORSMiddleware, allow_origins=settings.origins or ["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

@app.on_event("startup")
def startup():
    init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def now():
    return datetime.now(timezone.utc).isoformat()

@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "keys_configured": len(settings.keys), "cache_enabled": True}
    except Exception as exc:
        print(f"[DATABASE HEALTH] {type(exc).__name__}: {exc}", flush=True)
        raise HTTPException(status_code=503, detail="database unavailable")

@app.post("/chat")
def chat(payload: ChatRequest, db: Session = Depends(get_db),
         x_simulate_failure: str | None = Header(default=None, alias="X-Simulate-Failure")):
    if len(payload.message) > 4000:
        raise HTTPException(status_code=422, detail="message must be 4000 characters or fewer")
    session = db.execute(text("SELECT session_id, system_prompt FROM sessions WHERE session_id=:sid"),
                         {"sid": payload.session_id}).mappings().first()
    if not session:
        db.execute(text("INSERT INTO sessions(session_id, system_prompt, created_at) VALUES(:sid,:prompt,:created)"),
                   {"sid": payload.session_id, "prompt": payload.system_prompt, "created": now()})
        db.commit()
        session_prompt = payload.system_prompt or settings.default_system_prompt
    else:
        session_prompt = payload.system_prompt or session["system_prompt"] or settings.default_system_prompt

    history = db.execute(text("""
        SELECT role, content FROM messages WHERE session_id=:sid ORDER BY id ASC
    """), {"sid": payload.session_id}).mappings().all()
    messages = [{"role": "system", "content": session_prompt}]
    messages.extend({"role": row["role"], "content": row["content"]} for row in history)
    messages.append({"role": "user", "content": payload.message})

    try:
        result = generate(messages, x_simulate_failure)
    except AllProvidersUnavailable:
        raise HTTPException(status_code=503, detail="all providers unavailable")

    # Persist only after a successful provider/cache response. Failed requests never enter history.
    db.execute(text("""
        INSERT INTO messages(session_id, role, content, metadata, created_at)
        VALUES(:sid, 'user', :content, NULL, :created)
    """), {"sid": payload.session_id, "content": payload.message, "created": now()})
    metadata = {k: result[k] for k in (
        "resolution_source", "model", "latency_ms", "input_tokens",
        "output_tokens", "key_id", "fallback_attempts"
    )}
    db.execute(text("""
        INSERT INTO messages(session_id, role, content, metadata, created_at)
        VALUES(:sid, 'assistant', :content, :metadata, :created)
    """), {"sid": payload.session_id, "content": result["reply"],
           "metadata": json.dumps(metadata), "created": now()})
    db.commit()
    return {"session_id": payload.session_id, "reply": result["reply"], "metadata": metadata}

@app.get("/sessions/{session_id}/messages")
def get_messages(session_id: str, db: Session = Depends(get_db)):
    exists = db.execute(text("SELECT 1 FROM sessions WHERE session_id=:sid"), {"sid": session_id}).first()
    if not exists:
        raise HTTPException(status_code=404, detail="session not found")
    rows = db.execute(text("""
        SELECT role, content, metadata FROM messages
        WHERE session_id=:sid ORDER BY id ASC
    """), {"sid": session_id}).mappings().all()
    messages = []
    for row in rows:
        item = {"role": row["role"], "content": row["content"]}
        if row["metadata"]:
            item["metadata"] = json.loads(row["metadata"])
        messages.append(item)
    return {"session_id": session_id, "messages": messages}
