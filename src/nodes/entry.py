from langchain_core.messages import AIMessage, HumanMessage
from src.state import State
from typing import Dict
from langgraph.graph import END
from langchain_openai import ChatOpenAI
import os
from pydantic import BaseModel, Field

class SupportRouteOptions(BaseModel):
    support_type: str = Field(description="The type of support the user is asking for. Must be 'sales' if they want to buy, upgrade, or add new solar systems. Must be 'service' if they have an issue with an existing system, need maintenance, or require repairs. If unclear, return 'unknown'.")

def entry_node(state: State) -> Dict:
    """
    Step 1 & 2: Greet visitor and ask for support type.
    """
    # Skip if we already have a support type
    if state.get("support_type"):
        return {}

    messages = state.get("messages", [])

    # Check for direct keyword matches as a high-fidelity fallback
    if messages:
        last_msg = messages[-1]
        content = str(getattr(last_msg, "content", last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg))).lower()
        if "sale" in content or "buy" in content or "quote" in content:
            return {"support_type": "sales", "auth_step": "identifier"}
        if "service" in content or "fix" in content or "repair" in content or "issue" in content:
            return {"support_type": "service", "auth_step": "identifier"}

    # Greeting Logic
    name = state.get("customer_name") or "there"
    auth_updates = {"auth_step": "identifier"} if not state.get("auth_step") else {}

    # If this is the first message or we need to prompt
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
        **auth_updates
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
            last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
            if last_type == "human":
                 content = getattr(last_msg, "content", last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg))
                 content = str(content)
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
            
        # Re-entry routing for multi-turn service flows
        if state.get("service_step") in ["nps", "feedback"]:
            return "service_nps_and_close"
        if state.get("service_step") in ["system_size", "inverter", "year", "online", "installer"]:
            return "service_unregistered_start"
            
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
            
        # Re-entry routing for multi-turn sales flows
        if state.get("sales_step") in ["review_complete", "generating", "options", "agent_feedback", "confirm"]:
            return "sales_start"
        
        # KEY FIX: Route directly to info capture if we are in that phase!
        input_steps = ["info_capture", "name", "contact_complement", "context", "segment", "usage_bill", "usage_increase", "design_count", "design_brand", "design_tier"]
        if state.get("sales_step") in input_steps:
            return "sales_info_capture"
            
        return "sales_start"
    
    return "__end__"
