from langchain_core.messages import AIMessage, HumanMessage
from src.state import State
from src.utils.data_loader import load_site_by_id, load_metrics_by_site, check_agent_availability
from typing import Dict, List
from langgraph.graph import END
import uuid

def _extract_msg_content(m: object) -> str:
    """Best-effort content extraction for both dict messages and LangChain message objects."""
    if isinstance(m, str):
        return m
    if isinstance(m, dict):
        return str(m.get("content") or m.get("text") or "")
    return str(getattr(m, "content", "") or "")

def service_status_check(state: State) -> Dict:
    """
    Check the current status of the user's solar system.
    Matches Step 4.1 requirements.
    """
    site_id = state.get("site_id")
    site_data = load_site_by_id(site_id)
    
    if not site_data:
        return {"error": "Site not found"}
    
    messages = state.get("messages", [])
    
    # Check if we've already done this check to avoid duplicate messages on re-entry
    if any("Let me quickly check" in _extract_msg_content(m) for m in messages):
        return {}
    
    new_messages = [{"type": "ai", "content": "Let me quickly check the current status of your solar system in our monitoring platform."}]
    
    issue_flag = str(site_data.get("issue_flag")).lower() == "true"
    
    if issue_flag:
        issue_text = site_data.get("issue_text")
        action_text = site_data.get("recommended_action_text")
        new_messages.extend([
            {"type": "ai", "content": "We are currently seeing an issue on your system."},
            {"type": "ai", "content": f"Issue: {issue_text}."},
            {"type": "ai", "content": f"Recommended action: {action_text}."}
        ])
        # Placeholder for ETA if present in a real scenario
        return {
            "issue_flag": True,
            "issue_text": issue_text,
            "action_text": action_text,
            "messages": new_messages + [
                {
                    "type": "ai",
                    "content": "Does this answer your question, or would you like to speak to support?",
                    "additional_kwargs": {
                        "options": [
                            {"label": "I’m happy with this explanation", "value": "happy"},
                            {"label": "I still need help", "value": "unhappy"}
                        ]
                    }
                }
            ]
        }
    else:
        # Case B: No active issue, check metrics
        metrics = load_metrics_by_site(site_id)
        if not metrics:
            analysis_text = "Your system does not show any active faults and no recent monitoring data is available."
        else:
            avg_cloudiness = sum(m.get("cloudiness_percentage", 0) for m in metrics) / len(metrics)
            total_prod = sum(m.get("production_kwh", 0) for m in metrics)
            avg_perf = sum(m.get("performance_score", 0) for m in metrics) / len(metrics)
            
            if avg_cloudiness > 60:
                 analysis_text = f"Your system does not show any active faults. However, the last week has been unusually cloudy at your location, which is likely why your production has been lower than normal. It should auto-correct as weather improves."
            elif avg_perf > 90:
                 analysis_text = f"Your system appears to be performing normally. Last week’s total production was {total_prod:.1f} kWh."
            else:
                 analysis_text = "We see a slight underperformance trend, but nothing critical yet. We’ll continue monitoring it."
        
        new_messages.append({"type": "ai", "content": analysis_text})
        return {
            "issue_flag": False,
            "issue_text": analysis_text,
            "metrics": metrics,
            "messages": new_messages + [
                {
                    "type": "ai",
                    "content": "Does this answer your question, or would you like to speak to support?",
                    "additional_kwargs": {
                        "options": [
                            {"label": "I’m happy with this explanation", "value": "happy"},
                            {"label": "I still need help", "value": "unhappy"}
                        ]
                    }
                }
            ]
        }

def service_resolution_router(state: State) -> str:
    """
    Route based on whether the customer is happy with the status check.
    Wait for input if status is None.
    """
    status = state.get("service_resolution_status")
    
    if not status:
        # Check messages for button clicks if not explicitly set
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
            
            if last_type == "human":
                content = getattr(last_msg, "content", last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg))
                content = str(content).lower()
                # Fix 13: Standardize on exact values for button clicks
                if "happy" == content:
                    status = "happy"
                elif "unhappy" == content:
                    status = "unhappy"
                    
    if status == "happy":
        return "service_nps_and_close"
    elif status == "unhappy":
        return "service_issue_capture"
        
    return "__end__"

def service_issue_capture(state: State) -> Dict:
    """
    Record details when the customer still needs help.
    """
    # If app.py already parsed a category click and injected it into State, we are done here.
    if state.get("selected_issue"):
         return {}
         
    # We haven't asked for a category yet, check if the user just clicked one right now
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
        if last_type == "human":
            content = getattr(last_msg, "content", last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg))
            content_lower = str(content).lower()
            categories = ["Production Issue", "System Not Working", "Communication Loss", "Battery Failure", "Inverter Failure", "Others"]
            for cat in categories:
                if cat.lower() in content_lower:
                    return {"selected_issue": cat}
                    
    # Prevent double-prompting
    if any("Please select the category" in _extract_msg_content(m) for m in messages):
        return {}
                    
    # If app.py hasn't set it yet, we prompt the user
    return {
        "service_resolution_status": "unhappy",
        "messages": [
            {"type": "ai", "content": "Sorry to hear that. Let’s understand the issue in a bit more detail."},
            {
                "type": "ai",
                "content": "Please select the category that best describes your issue:",
                "additional_kwargs": {
                    "options": [
                        {"label": "Production Issue", "value": "Production Issue"},
                        {"label": "System Not Working", "value": "System Not Working"},
                        {"label": "Communication Loss", "value": "Communication Loss"},
                        {"label": "Battery Failure", "value": "Battery Failure"},
                        {"label": "Inverter Failure", "value": "Inverter Failure"},
                        {"label": "Others", "value": "Others"}
                    ]
                }
            }
        ]
    }

def issue_capture_router(state: State) -> str:
    """
    Route to context collection once an issue category is selected.
    """
    if state.get("selected_issue"):
        return "service_issue_context_collect"
    return "__end__"

def service_issue_context_collect(state: State) -> Dict:
    """
    Collect free-text description and photo evidence.
    """
    if state.get("description"):
         return {}
         
    # Check if they just provided the description right now
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
        if last_type == "human":
            content = getattr(last_msg, "content", last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg))
            content_lower = str(content).lower()
            selected_issue = state.get("selected_issue", "").lower()
            
            # Make sure it's not the button click itself
            if content_lower != selected_issue and "still need help" not in content_lower and "continue" not in content_lower():
                prompt_str = "Please describe the issue"
                if any(prompt_str in _extract_msg_content(m) for m in messages):
                    return {"description": content}
                
    # Prevent double-prompting
    prompt_str = "Please describe the issue"
    if any(prompt_str in _extract_msg_content(m) for m in messages):
        return {}
                
    # If we haven't prompted yet, do it
    return {
        "messages": [
            {"type": "ai", "content": "Please describe the issue in your own words."},
            {"type": "ai", "content": "If possible, please upload photos or screenshots that show what you’re seeing (inverter screen, app screenshots, physical damage, etc.)."}
        ]
    }

def issue_context_router(state: State) -> str:
    if state.get("description"):
        return "service_availability_check"
    return "__end__"

def service_availability_check(state: State) -> Dict:
    """
    Check if a human is available and ask if they want a live chat.
    Matches Step 4.3 requirement 4 and 5.
    """
    # If they answered yes or no already, we don't need to ask
    if state.get("handoff_type") is not None:
        return {}
        
    # Check if they just answered
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
        if last_type == "human":
            content = getattr(last_msg, "content", last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg))
            content = str(content).lower()
            # If we already asked, process the answer
            if any("Would you like to start a live chat" in _extract_msg_content(m) for m in messages):
                if "yes" in content:
                    return {"handoff_type": "chat"}
                elif "no" in content or "ticket" in content:
                    return {"handoff_type": "ticket"}
        
    online = check_agent_availability("service")
    if online:
        # Fix 13: We'll extract message content later, but we need to prompt
        return {
            "representative_available": True,
            "messages": [
                {
                    "type": "ai",
                    "content": "We have a service executive available right now. Would you like to start a live chat?",
                    "additional_kwargs": {
                        "options": [
                            {"label": "Yes", "value": "Yes"},
                            {"label": "No, just create a ticket", "value": "No"}
                        ]
                    }
                }
            ]
        }
    else:
        return {
            "representative_available": False,
            "handoff_type": "ticket", # No live chat possible
            "messages": [
                 {"type": "ai", "content": "Our service team is currently offline. I’ll create a ticket with all the details you’ve shared so we can follow up."}
            ]
        }

def availability_router(state: State) -> str:
    if state.get("handoff_type"):
        if state.get("handoff_type") == "chat":
            return "service_live_chat_start"
        else:
            return "service_ticket_create"
            
    if state.get("representative_available"):
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
            if last_type == "human":
                content = getattr(last_msg, "content", last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg))
                content = str(content).lower()
                # Fix 4: Router must be pure. We rely on the node to have set the choice 
                # or we check the message without mutating.
                if "yes" in content:
                    return "service_live_chat_start"
                elif "no" in content or "ticket" in content:
                    return "service_ticket_create"
        return "__end__"

    if state.get("representative_available") is False:
        return "service_ticket_create"
        
    return "__end__"

def service_live_chat_start(state: State) -> Dict:
    """
    Hand off to live chat.
    """
    if state.get("ticket_id"):
        return {}
        
    return {
        "ticket_id": f"TRANSFERRED-{uuid.uuid4().hex[:8].upper()}",
        "messages": [
            {"type": "ai", "content": "We are transferring you to a service executive with the full context of your issue. Please wait..."}
        ]
    }

def service_ticket_create(state: State) -> Dict:
    """
    Create a service ticket and check for human availability.
    Matches Step 4.3 requirements.
    """
    if state.get("ticket_id"):
        return {}
        
    ticket_id = f"TICKET-{uuid.uuid4().hex[:8].upper()}"
    return {
        "ticket_id": ticket_id,
        "messages": [{"type": "ai", "content": f"Your service ticket has been created. Ticket number: {ticket_id}. Our team will reach out to you shortly."}]
    }

def service_nps_and_close(state: State) -> Dict:
    """
    Handle NPS and close conversation.
    Matches Step 4.2 requirements (Interactive loop).
    """
    messages = state.get("messages", [])
    if not messages:
        return {}
        
    last_msg = messages[-1]
    if hasattr(last_msg, "type"):
        l_type = last_msg.type
        l_content = last_msg.content
    else:
        l_type = last_msg.get("type", "ai")
        l_content = last_msg.get("content", "")

    # 1. Start NPS if we haven't yet
    if not state.get("service_step"):
        return {
            "messages": [
                {"type": "ai", "content": "Great, we’ll log that your query has been resolved."},
                {"type": "ai", "content": "On a scale of 1 to 10, how satisfied are you with the support you received just now?"}
            ],
            "service_step": "nps"
        }

    # If the last message was AI, we just asked a question, wait for human
    if l_type == "ai":
        return {}

    # 2. Process NPS score (ULTRA PERMISSIVE FIX)
    if state.get("service_step") == "nps":
        # ULTRA PERMISSIVE: If we are here and the human replied, JUST GO TO NEXT STEP
        # Extract number if possible for the state, but advance regardless
        import re
        match = re.search(r'\d+', str(l_content))
        score = int(match.group()) if match else 10
        
        return {
            "nps_score": score, 
            "service_step": "feedback",
            "messages": [{"type": "ai", "content": "Anything else you’d like to share about your experience?"}]
        }

    # 3. Process feedback and close
    if state.get("service_step") == "feedback":
        return {
            "messages": [{"type": "ai", "content": "Thank you. Your feedback helps us improve. Have a great day!"}],
            "service_step": "closed",
            "ticket_id": f"RESOLVED-{uuid.uuid4().hex[:8].upper()}"
        }

    return {}

def service_nps_router(state: State) -> str:
    if state.get("service_step") == "closed":
        return "__end__"
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
        if last_type == "human":
            return "service_nps_and_close"
    return "__end__"

def service_unregistered_start(state: State) -> Dict:
    """
    Step 5.2: Non-SunBun or unregistered system path.
    Prompt for system and installer information progressively.
    """
    messages = state.get("messages", [])
    human_reply = ""
    if messages:
        last_msg = messages[-1]
        last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
        if last_type == "human":
            human_reply = getattr(last_msg, "content", last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg))

    # 1. System Size
    if not state.get("unregistered_system_size"):
        if state.get("service_step") == "system_size" and human_reply:
             return {"unregistered_system_size": human_reply}
        return {
            "messages": [
                {"type": "ai", "content": "We can still help, but we’ll need a few details about your setup."},
                {"type": "ai", "content": "Approximate system size (kWp)"}
            ],
            "service_step": "system_size"
        }

    # 2. Inverter brand/model
    if not state.get("unregistered_inverter"):
        if state.get("service_step") == "inverter" and human_reply:
             return {"unregistered_inverter": human_reply}
        return {
            "messages": [{"type": "ai", "content": "Inverter brand/model"}],
            "service_step": "inverter"
        }

    # 3. Year of installation
    if not state.get("unregistered_year"):
        if state.get("service_step") == "year" and human_reply:
             return {"unregistered_year": human_reply}
        return {
            "messages": [{"type": "ai", "content": "Year of installation"}],
            "service_step": "year"
        }

    # 4. Online Monitoring
    if state.get("unregistered_online") is None:
        if state.get("service_step") == "online" and human_reply:
             val = True if "yes" in str(human_reply).lower() else False
             return {"unregistered_online": val}
        return {
            "messages": [{
                "type": "ai",
                "content": "Is online monitoring active?",
                "additional_kwargs": {
                    "options": [
                        {"label": "Yes", "value": "Yes"},
                        {"label": "No", "value": "No"}
                    ]
                }
            }],
            "service_step": "online"
        }

    # 5. Installer
    if not state.get("unregistered_installer"):
        if state.get("service_step") == "installer" and human_reply:
             return {"unregistered_installer": human_reply, "unregistered_system_info": "captured"}
        return {
            "messages": [{"type": "ai", "content": "Who installed your system? (Enter name or 'Don’t remember')"}],
            "service_step": "installer"
        }

    return {}

def unregistered_system_router(state: State) -> str:
    """
    Route after system info is collected progressively.
    """
    if state.get("unregistered_system_info") == "captured":
        return "service_issue_capture"

    # We need to wait for input unless the human just replied
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
        if last_type == "human":
            return "service_unregistered_start"
            
    return "__end__"

# Removing redundant unregistered issue nodes since we mapped them to the central issue capture flow
