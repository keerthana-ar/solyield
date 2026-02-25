import asyncio
from src.graph import create_graph, END
from langgraph.graph import StateGraph
from src.state import State
import json

async def run_test():
    # 1. Compile the graph
    app = create_graph()
    
    # 2. Build the state simulating "No, continue anyway"
    state = {
        "session_id": "test_session",
        "user_role": "customer",
        "support_type": "service",
        "auth_verified": True,
        "auth_step": "verified",
        "auth_identifier_type": "email",
        "auth_identifier_value": "nobody@google.com",
        "in_db": False,
        "lookup_retries": 1,
        "lookup_retry_choice": "No, continue anyway",
        "messages": [
            {"type": "human", "content": "No, continue anyway", "id": "123"}
        ]
    }
    
    try:
        print("Starting graph run")
        async for chunk in app.astream(state, stream_mode="values"):
            print(f"Update: {chunk.keys()}")
            if "messages" in chunk:
                print(f"Messages count: {len(chunk['messages'])}")
            
            # Test JSON Serialization which is what FastAPI uses
            try:
                json.dumps(chunk)
            except Exception as e:
                print(f"JSON Serialization Error: {e}")
        print("Graph run complete")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
