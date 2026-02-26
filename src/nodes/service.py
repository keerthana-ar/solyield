from src.state import State
from src.utils.data_loader import load_site_by_id, load_metrics_by_site, check_agent_availability
from typing import Dict, List
from langgraph.graph import END
import uuid

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
    if any(isinstance(m, dict) and m.get("content") and "Let me quickly check" in m.get("content") for m in messages):
        return {}
    
    new_messages = ["Let me quickly check the current status of your solar system in our monitoring platform."]
    
    issue_flag = str(site_data.get("issue_flag")).lower() == "true"
    
    if issue_flag:
        issue_text = site_data.get("issue_text")
        action_text = site_data.get("recommended_action_text")
        new_messages.extend([
            "We are currently seeing an issue on your system.",
            f"Issue: {issue_text}.",
            f"Recommended action: {action_text}."
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
            total_prod = sum(m.get("production_kwh", 0) for m in metrics) # This is weekly total
            
            analysis_text = f"Your system is performing normally. Weekly production: {total_prod:.1f} kWh. Average cloudiness: {avg_cloudiness:.1f}%."
            if avg_cloudiness > 50:
                 analysis_text += " Higher cloudiness might affect production this week."
        
        new_messages.append(analysis_text)
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
            last_type = last_msg.get("type") if isinstance(last_msg, dict) else "ai"
            
            if last_type == "human":
                content = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
                if "happy" in content.lower():
                    status = "happy"
                elif "help" in content.lower() or "still need" in content.lower():
                    status = "unhappy"
                    
    if status == "happy":
        return "service_nps_and_close"
    elif status == "unhappy":
        return "service_issue_capture"
        
    return END

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
        last_type = last_msg.get("type") if isinstance(last_msg, dict) else "ai"
        if last_type == "human":
            content = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
            categories = ["Production Issue", "System Not Working", "Communication Loss", "Battery Failure", "Inverter Failure", "Others"]
            for cat in categories:
                if cat.lower() in content.lower():
                    return {"selected_issue": cat}
                    
    # Prevent double-prompting
    if any(isinstance(m, dict) and "Please select the category" in str(m.get("content", "")) for m in messages):
        return {}
                    
    # If app.py hasn't set it yet, we prompt the user
    return {
        "service_resolution_status": "unhappy",
        "messages": [
            "Sorry to hear that. Let’s understand the issue in a bit more detail.",
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
    return END

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
        last_type = last_msg.get("type") if isinstance(last_msg, dict) else "ai"
        if last_type == "human":
            content = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
            selected_issue = state.get("selected_issue", "").lower()
            
            # Make sure it's not the button click itself
            if content.lower() != selected_issue and "still need help" not in content.lower() and "continue" not in content.lower():
                prompt_str = "Please describe the issue"
                if any(isinstance(m, str) and prompt_str in m for m in messages) or \
                   any(isinstance(m, dict) and prompt_str in str(m.get("content", "")) for m in messages):
                    return {"description": content}
                
    # Prevent double-prompting
    prompt_str = "Please describe the issue"
    if any(isinstance(m, str) and prompt_str in m for m in messages) or \
       any(isinstance(m, dict) and prompt_str in str(m.get("content", "")) for m in messages):
        return {}
                
    # If we haven't prompted yet, do it
    return {
        "messages": [
            "Please describe the issue in your own words.",
            "If possible, please upload photos or screenshots that show what you’re seeing (inverter screen, app screenshots, physical damage, etc.)."
        ]
    }

def issue_context_router(state: State) -> str:
    if state.get("description"):
        return "service_availability_check"
    return END

def service_availability_check(state: State) -> Dict:
    """
    Check if a human is available and ask if they want a live chat.
    Matches Step 4.3 requirement 4 and 5.
    """
    # If they answered yes or no already, we don't need to ask
    if state.get("handoff_type") is not None:
        return {}
        
    # Check if we already asked
    messages = state.get("messages", [])
    if any(isinstance(m, dict) and "Would you like to start a live chat" in str(m.get("content")) for m in messages):
        return {}
        
    online = check_agent_availability("service")
    if online:
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
                 "Our service team is currently offline. I’ll create a ticket with all the details you’ve shared so we can follow up."
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
            last_type = last_msg.get("type") if isinstance(last_msg, dict) else "ai"
            if last_type == "human":
                content = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
                if "yes" in content.lower():
                    state["handoff_type"] = "chat"
                    return "service_live_chat_start"
                elif "no" in content.lower() or "ticket" in content.lower():
                    state["handoff_type"] = "ticket"
                    return "service_ticket_create"
        return END

    if state.get("representative_available") is False:
        return "service_ticket_create"
        
    return END

def service_live_chat_start(state: State) -> Dict:
    """
    Hand off to live chat.
    """
    if state.get("ticket_id"):
        return {}
        
    return {
        "ticket_id": f"TRANSFERRED-{uuid.uuid4().hex[:8].upper()}",
        "messages": [
            "We are transferring you to a service executive with the full context of your issue. Please wait..."
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
    
    messages = []
    messages.append(f"Your service ticket has been created. Ticket number: {ticket_id}. Our team will reach out to you shortly.")

    return {
        "ticket_id": ticket_id,
        "messages": messages
    }

def service_nps_and_close(state: State) -> Dict:
    """
    Handle NPS and close conversation.
    Matches Step 4.2 requirements.
    """
    if state.get("ticket_id"):
        return {}
        
    return {
        "ticket_id": f"RESOLVED-{uuid.uuid4().hex[:8].upper()}",
        "messages": [
            "Great, we’ll log that your query has been resolved.",
            "On a scale of 1 to 10, how satisfied are you with the support you received just now?",
            "Anything else you’d like to share about your experience?",
            "Thank you. Your feedback helps us improve. Have a great day!"
        ]
    }

def service_unregistered_start(state: State) -> Dict:
    """
    Step 5.2: Non-SunBun or unregistered system path.
    Prompt for system and installer information progressively.
    """
    messages = state.get("messages", [])
    human_reply = ""
    if messages:
        last_msg = messages[-1]
        last_type = last_msg.get("type") if isinstance(last_msg, dict) else "ai"
        if last_type == "human":
            human_reply = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)

    # 1. System Size
    if not state.get("unregistered_system_size"):
        if state.get("service_step") == "system_size" and human_reply:
             return {"unregistered_system_size": human_reply}
        return {
            "messages": ["We can still help, but we’ll need a few details about your setup.", "Approximate system size (kWp)"],
            "service_step": "system_size"
        }

    # 2. Inverter brand/model
    if not state.get("unregistered_inverter"):
        if state.get("service_step") == "inverter" and human_reply:
             return {"unregistered_inverter": human_reply}
        return {
            "messages": ["Inverter brand/model"],
            "service_step": "inverter"
        }

    # 3. Year of installation
    if not state.get("unregistered_year"):
        if state.get("service_step") == "year" and human_reply:
             return {"unregistered_year": human_reply}
        return {
            "messages": ["Year of installation"],
            "service_step": "year"
        }

    # 4. Online Monitoring
    if state.get("unregistered_online") is None:
        if state.get("service_step") == "online" and human_reply:
             val = True if "yes" in human_reply.lower() else False
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
            "messages": ["Who installed your system? (Enter name or 'Don’t remember')"],
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
        last_type = last_msg.get("type") if isinstance(last_msg, dict) else "ai"
        if last_type == "human":
            return "service_unregistered_start"
            
    return END

# Removing redundant unregistered issue nodes since we mapped them to the central issue capture flow
