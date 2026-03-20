import os
import json
import uuid
import asyncio
from typing import List, Dict, Any, AsyncGenerator
import numpy as np
from contextlib import asynccontextmanager

from src.graph import create_graph
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, message_to_dict

def clean_obj_for_json(obj):
    """Recursively convert anything non-JSON-serializable to native types or strings."""
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            try:
                new_dict[str(k)] = clean_obj_for_json(v)
            except:
                new_dict[str(k)] = str(v)
        return new_dict
    if isinstance(obj, list):
        return [clean_obj_for_json(v) for v in obj]
    if isinstance(obj, (np.integer, np.floating, np.int64, np.float64)):
        return obj.item()
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    
    # LangChain Message Serialization (Official message_to_dict)
    if hasattr(obj, "type") and hasattr(obj, "content"):
        try:
            dtype = str(obj.type)
            role = "assistant" if dtype == "ai" else "user" if dtype == "human" else dtype
            
            # STRIP LARGE BASE64 DATA (LOOPHOLE FIX FOR BUFFER LIMITS)
            content = str(obj.content)
            if "data:image" in content and len(content) > 1000:
                content = "[Image Attachment Captured]"

            return {
                "type": dtype,
                "role": role,
                "content": content,
                "additional_kwargs": clean_obj_for_json(getattr(obj, "additional_kwargs", {})),
                "id": str(getattr(obj, "id", uuid.uuid4()))
            }
        except:
            return {"type": "ai", "role": "assistant", "content": str(obj), "id": str(uuid.uuid4())}
    
    # Generic object serialization
    if not isinstance(obj, (str, int, float, bool, type(None))):
        try:
            return str(obj)
        except:
            return "[Unserializable Object]"
    return obj

def safe_json_dumps(obj):
    """Aggressive, non-crashing JSON dump with disk logging for debugging."""
    try:
        cleaned = clean_obj_for_json(obj)
        dumped = json.dumps(cleaned)
        
        # NUCLEAR DISK LOGGING
        if "messages" in cleaned:
             try:
                 with open("NUCLEAR_STREAM_LOG.txt", "a") as f:
                     import datetime
                     f.write(f"[{datetime.datetime.now()}] OUTBOUND STATE: {len(cleaned['messages'])} messages\n")
             except:
                 pass
                 
        return dumped
    except Exception as e:
        print(f"CRITICAL: safe_json_dumps failed even after cleaning. Error: {e}")
        try:
             with open("NUCLEAR_STREAM_LOG.txt", "a") as f:
                 f.write(f"SERIALIZATION FATAL ERROR: {e}\n")
        except:
             pass
        # Final fallback
        return json.dumps({"error": "unserializable_state", "messages": []})

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# Use a global for the graph and checkpointer
checkpointer = None
graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    graph = create_graph()
    print("In-Memory Persistence Layer Ready.")
    yield

app = FastAPI(lifespan=lifespan)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/assistants")
async def list_assistants():
    # Mimic LangGraph SDK list assistants
    return [{"assistant_id": "agent", "name": "Solar Assistant"}]

@app.post("/threads")
async def create_thread():
    # Mimic LangGraph SDK create thread
    return {"thread_id": str(uuid.uuid4())}

# --- AGENT PROTOCOL COMPATIBILITY (WEEK 2 BONUS) ---

@app.post("/ap/v1/agent/tasks")
async def create_agent_task(request: Request):
    """
    Official Agent Protocol: Create a new task.
    We map this to a LangGraph thread, optionally using 'customer_id' as the anchor.
    """
    body = await request.json()
    input_str = body.get("input", "")
    customer_id = body.get("customer_id")
    
    # Bonus: Persist memory tied to customer_id or site_id
    thread_id = customer_id if customer_id else str(uuid.uuid4())
    
    # We trigger the first run and return the task_id (which is our thread_id)
    return {
        "task_id": thread_id,
        "input": input_str,
        "status": "created"
    }

@app.get("/ap/v1/agent/tasks/{task_id}")
async def get_agent_task(task_id: str):
    """
    Official Agent Protocol: Get task details.
    """
    state = await graph.aget_state({"configurable": {"thread_id": task_id}})
    return {
        "task_id": task_id,
        "status": "completed" if state.next is None else "running",
        "additional_info": {"has_state": state.values != {}}
    }

@app.post("/ap/v1/agent/tasks/{task_id}/steps")
async def execute_agent_step(task_id: str, request: Request):
    """
    Official Agent Protocol: Execute a step in the task.
    We map this to a LangGraph run.
    """
    return await stream_run(task_id, request)


@app.post("/assistants/{assistant_id}/runs/stream")
async def stream_run_assistant(assistant_id: str, request: Request):
    return await stream_run(str(uuid.uuid4()), request)

@app.post("/threads/{thread_id}/runs/stream")
async def stream_run(thread_id: str, request: Request):
    """
    Minimal SSE streaming implementation that matches the @langchain/langgraph-sdk format.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
        
    # Check both standard 'input' key and top-level submission
    input_data = body.get("input", body)
    
    # AGENT PROTOCOL FIX: If input is a raw string, wrap it as a human message
    if isinstance(input_data, str) and input_data.strip():
        input_data = {"messages": [{"type": "human", "content": input_data}]}
    elif isinstance(input_data, dict) and "messages" not in input_data and "messages" in body:
        input_data = {"messages": body["messages"]}
    
    if not input_data and not body:
        input_data = {}
    
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Detect button clicks and set is_button flag
            if input_data and "messages" in input_data:
                for msg in input_data["messages"]:
                    content = str(msg.get("content", "")).lower()
                    if content in ["use email", "use phone", "yes", "no", "retry", "exit"]:
                         msg["is_button"] = True
            
            config = {"configurable": {"thread_id": thread_id}}
            
            # Use 'values' mode for the most stable React SDK experience
            async for data in graph.astream(input_data, config=config, stream_mode="values"):
                # Protocol Alignment: The SDK expects a clean JSON representation of the state
                cleaned_data = clean_obj_for_json(data)
                
                # Double-check messages format
                if "messages" in cleaned_data:
                    for m in cleaned_data["messages"]:
                        # SDK specifically likes'role'
                        if "type" in m and "role" not in m:
                             m["role"] = "assistant" if m["type"] == "ai" else "user" if m["type"] == "human" else m["type"]
                
                # Emit standard 'values' event
                yield f"event: values\ndata: {json.dumps(cleaned_data)}\n\n"
                
            # Final message to close the stream
            yield "event: end\ndata: {}\n\n"
        except Exception as e:
            # Fix 17: Robust error logging
            import traceback
            print(f"Streaming Error: {e}")
            traceback.print_exc()
            yield f"event: error\ndata: {safe_json_dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    print("Starting local LangGraph-compatible server on http://localhost:8000")
    # Using 'asyncio' loop to be safe on Windows (though this server doesn't use psycopg3)
    uvicorn.run(app, host="0.0.0.0", port=8000)
