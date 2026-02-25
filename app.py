from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uuid
import json
import hashlib
import traceback
from src.graph import create_graph
from src.state import State

app = FastAPI(title="SunBun Solar Assistant API")

# Add CORS middleware for Aegra UI compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store sessions in memory
sessions: Dict[str, State] = {}

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "SunBun Solar Assistant API is running.",
        "endpoints": ["/info", "/threads", "/threads/search"]
    }

@app.get("/debug/sessions")
async def debug_sessions():
    return {"session_count": len(sessions), "ids": list(sessions.keys())}

# Global graph instance
graph = create_graph()

def get_initial_state(task_id: str) -> State:
    return {
        "session_id": task_id,
        "contact": {"email": None, "phone": None},
        "support_type": None,
        "auth_verified": False,
        "auth_step": "identifier",
        "in_db": None,
        "customer_id": None,
        "customer_name": None,
        "location": None,
        "site_id": None,
        "has_proposals": None,
        "issue_flag": None,
        "issue_text": None,
        "action_text": None,
        "metrics": [],
        "ticket_id": None,
        "service_resolution_status": None,
        "sales_profile": None,
        "proposals": [],
        "chosen_proposal_id": None,
        "sales_step": None,
        "representative_available": None,
        "messages": [],
        "lookup_retries": 0,
        "lookup_retry_choice": None,
        "auth_otp_retries": 0
    }

# --- LANGGRAPH API COMPATIBILITY ---

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"DEBUG: {request.method} {request.url}")
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response

def get_thread_object(tid: str):
    return {
        "thread_id": tid,
        "id": tid,
        "created_at": "2026-02-22T00:00:00Z",
        "updated_at": "2026-02-22T00:00:00Z",
        "status": "idle",
        "metadata": {},
        "values": sessions.get(tid, {})
    }

@app.get("/info")
@app.get("/v1/info")
async def get_info():
    return {
        "graphs": {
            "agent": {
                "graph_id": "agent",
                "description": "SunBun Solar Assistant",
                "metadata": {}
            }
        }
    }

@app.get("/threads")
@app.get("/v1/threads")
@app.post("/threads/search")
@app.post("/v1/threads/search")
async def search_threads():
    return [get_thread_object(tid) for tid in sessions.keys()]

@app.post("/threads")
@app.post("/v1/threads")
async def create_thread():
    thread_id = str(uuid.uuid4())
    state = get_initial_state(thread_id)
    try:
        new_state = graph.invoke(state)
        sessions[thread_id] = new_state
    except:
        sessions[thread_id] = state
    return get_thread_object(thread_id)

@app.get("/threads/{thread_id}")
@app.get("/v1/threads/{thread_id}")
async def get_thread(thread_id: str):
    if thread_id not in sessions:
        state = get_initial_state(thread_id)
        try:
            sessions[thread_id] = graph.invoke(state)
        except:
            sessions[thread_id] = state
    return get_thread_object(thread_id)

@app.get("/threads/{thread_id}/state")
@app.get("/v1/threads/{thread_id}/state")
@app.post("/threads/{thread_id}/state")
@app.post("/v1/threads/{thread_id}/state")
async def get_thread_state(thread_id: str):
    if thread_id not in sessions:
        state = get_initial_state(thread_id)
        try:
            sessions[thread_id] = graph.invoke(state)
        except:
            sessions[thread_id] = state
            
    state = sessions[thread_id]
    formatted_state = state.copy()
    formatted_state["messages"] = [format_message(m, i) for i, m in enumerate(state.get("messages", []))]
    return {
        "values": formatted_state, 
        "next": [], 
        "checkpoint": {"thread_id": thread_id, "checkpoint_id": "latest"},
        "metadata": {}
    }

@app.get("/threads/{thread_id}/history")
@app.get("/v1/threads/{thread_id}/history")
@app.post("/threads/{thread_id}/history")
@app.post("/v1/threads/{thread_id}/history")
async def get_thread_history(thread_id: str):
    if thread_id not in sessions:
        state = get_initial_state(thread_id)
        try:
            sessions[thread_id] = graph.invoke(state)
        except:
            sessions[thread_id] = state
    formatted_state = state.copy()
    formatted_state["messages"] = [format_message(m, i) for i, m in enumerate(state.get("messages", []))]
    return [{
        "values": formatted_state, 
        "next": [], 
        "checkpoint": {"thread_id": thread_id, "checkpoint_id": "latest"},
        "metadata": {}
    }]

def format_message(m, idx=0):
    """Ensure message is a dict with type, content, and STABLE id."""
    try:
        if isinstance(m, str):
            content = m or " "
            # Default to AI for strings unless they look like human input handled by nodes
            mid = f"msg-{hashlib.md5((content + str(idx)).encode()).hexdigest()[:12]}"
            return {"type": "ai", "content": content, "id": mid}
        
        if isinstance(m, dict):
            content = m.get("content") or m.get("text") or " "
            mtype = m.get("type") or m.get("role") or "ai"
            msg_id = m.get("id") or f"{mtype}-{hashlib.md5((content + str(idx)).encode()).hexdigest()[:12]}"
            
            msg_obj = {"type": mtype, "content": content, "id": msg_id}
            # Standard buttons/options for Aegra
            options = m.get("buttons") or (m.get("additional_kwargs") or {}).get("options")
            if options:
                msg_obj["additional_kwargs"] = {"options": options}
            return msg_obj
    except Exception:
        return {"type": "ai", "content": str(m), "id": f"err-{uuid.uuid4().hex[:8]}"}
    return m

@app.post("/threads/{thread_id}/runs/stream")
@app.post("/v1/threads/{thread_id}/runs/stream")
async def run_stream(thread_id: str, request: Request):
    if thread_id not in sessions:
        sessions[thread_id] = get_initial_state(thread_id)
    
    try:
        body = await request.json()
    except:
        body = {}
        
    state = sessions[thread_id]
    run_id = str(uuid.uuid4())
    
    # Process inputs
    input_data = body.get("input", {})
    if input_data:
        msgs = input_data.get("messages", [])
        for m in msgs:
            # Extract content
            content = (m.get("content") or m.get("text") or str(m)) if isinstance(m, dict) else str(m)
            
            # Map choice buttons to state
            if "Sales Support" in content: state["support_type"] = "sales"
            elif "Service Support" in content: state["support_type"] = "service"
            
            # Add to local state (human)
            human_msg = {"type": "human", "content": content, "id": f"h-{uuid.uuid4().hex[:8]}"}
            if "messages" not in state: state["messages"] = []
            state["messages"].append(human_msg)
        
        for k, v in input_data.items():
            if k != "messages": state[k] = v

    async def event_generator():
        try:
            print(f"DEBUG: Starting SSE for {thread_id}")
            yield f"event: metadata\ndata: {json.dumps({'run_id': run_id, 'thread_id': thread_id})}\n\n"
            
            # Initial "pulse" (shows user input immediately)
            pulse_state = state.copy()
            pulse_state["messages"] = [format_message(m, i) for i, m in enumerate(state.get("messages", []))]
            yield f"event: values\ndata: {json.dumps(pulse_state)}\n\n"
            
            # Graph run
            for update in graph.stream(state, stream_mode="values"):
                # update is the current state snapshot
                formatted_msgs = [format_message(m, i) for i, m in enumerate(update.get("messages", []))]
                update["messages"] = formatted_msgs
                
                # Persistence
                sessions[thread_id] = update
                
                yield f"event: values\ndata: {json.dumps(update)}\n\n"
            
            yield f"event: end\ndata: {json.dumps({'run_id': run_id})}\n\n"
            print(f"DEBUG: Stream finished for {thread_id}")
        except Exception as e:
            traceback.print_exc()
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Dummies for UI
@app.get("/v1/threads/{thread_id}/runs")
async def list_runs(thread_id: str): return []
@app.get("/v1/threads/{thread_id}/checkpoints")
async def list_checkpoints(thread_id: str): return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2024)
