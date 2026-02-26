from src.state import State
from typing import Dict
from langgraph.graph import END

def entry_node(state: State) -> Dict:
    """
    Step 1 & 2: Greet visitor and ask for support type.
    """
    # Skip if we already have a support type
    if state.get("support_type"):
        return {}

    messages = state.get("messages", [])
    
    # Check if the user has already been greeted
    greeting_sent = False
    for m in messages:
        content = ""
        if isinstance(m, str): content = m
        elif isinstance(m, dict): content = m.get("content", "") or m.get("text", "")
        if "help you today?" in content:
            greeting_sent = True
            break
            
    print(f"DEBUG ENTRY_NODE: greeting_sent={greeting_sent}, len={len(messages)}")
    if messages:
        print(f"DEBUG ENTRY_NODE last_msg: {messages[-1]}")
            
    # If the user sent a message (like "hi") but support_type is still None,
    # and we already sent the greeting, they need a re-prompt.
    if greeting_sent and len(messages) > 1:
        last_msg = messages[-1]
        last_type = last_msg.get("type") if isinstance(last_msg, dict) else "ai"
        
        if last_type == "human":
            content = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
            c_lower = content.lower()
            
            # Check for hidden text intent
            if "sale" in c_lower or "buy" in c_lower:
                return {"support_type": "sales", "auth_step": "identifier"}
            elif "service" in c_lower or "fix" in c_lower or "support" in c_lower:
                return {"support_type": "service", "auth_step": "identifier"}
                
            # Otherwise, render the fallback menu
            return {
                "messages": [
                    {
                        "type": "ai",
                        "content": "Please select one of the support options below to proceed:",
                        "additional_kwargs": {
                            "options": [
                                {"label": "Sales Support", "value": "sales"},
                                {"label": "Service Support", "value": "service"}
                            ]
                        }
                    }
                ]
            }
        # If it wasn't a human message, do nothing
        return {}

    name = state.get("customer_name") or "there"
    
    # Return greeting and routing buttons
    return {
        "messages": [
            {
                "type": "ai",
                "content": f"Hi {name}, how can we help you today?",
                "additional_kwargs": {
                    "options": [
                        {"label": "Sales Support – I’m interested in buying / upgrading a system", "value": "sales"},
                        {"label": "Service Support – I need help with an existing or new system", "value": "service"}
                    ]
                }
            }
        ],
        "auth_step": "identifier"
    }

def support_router(state: State) -> str:
    """
    Step 3: Store choice and move to authentication.
    """
    support_type = state.get("support_type")
    
    if not support_type:
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            last_type = last_msg.get("type") if isinstance(last_msg, dict) else "ai"
            if last_type == "human":
                 content = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
                 c_lower = content.lower()
                 if "sale" in c_lower or "buy" in c_lower:
                     support_type = "sales"
                 elif "service" in c_lower or "fix" in c_lower or "support" in c_lower:
                     support_type = "service"
                     
        if not support_type:
            return "__end__" # Bounce back to entry_node for the menu
    
    if support_type == "service":
        # Check if we already proved they aren't in the DB (unregistered bypass)
        if state.get("in_db") is False:
            return "lookup_failure_node"

        if not state.get("auth_verified"):
            step = state.get("auth_step")
            if step == "otp":
                return "auth_verify_otp"
            return "auth_collect_contact"
            
        return "service_status_check"
        
    elif support_type == "sales":
        # If they explicitly chose to continue unregistered (in_db is False), bypass auth loop!
        if state.get("in_db") is False:
            return "sales_start"

        if not state.get("auth_verified"):
            step = state.get("auth_step")
            if step == "otp":
                return "auth_verify_otp"
            return "auth_collect_contact"
            
        return "sales_start"
    
    return "__end__"
