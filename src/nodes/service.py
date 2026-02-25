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
    
    messages = ["Let me quickly check the current status of your solar system in our monitoring platform."]
    
    issue_flag = str(site_data.get("issue_flag")).lower() == "true"
    
    if issue_flag:
        issue_text = site_data.get("issue_text")
        action_text = site_data.get("recommended_action_text")
        messages.extend([
            "We are currently seeing an issue on your system.",
            f"Issue: {issue_text}.",
            f"Recommended action: {action_text}."
        ])
        # Placeholder for ETA if present in a real scenario
        return {
            "issue_flag": True,
            "issue_text": issue_text,
            "action_text": action_text,
            "messages": messages + [
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
        
        messages.append(analysis_text)
        return {
            "issue_flag": False,
            "issue_text": analysis_text,
            "metrics": metrics,
            "messages": messages + [
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
    if status == "happy":
        return "service_nps_and_close"
    elif status == "unhappy":
        return "service_issue_capture"
    return END

def service_issue_capture(state: State) -> Dict:
    """
    Record details when the customer still needs help.
    Matches Step 4.3 requirements.
    """
    # This node is triggered when user clicks "I still need help"
    # We first show the list of categories.
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

def service_issue_context_collect(state: State) -> Dict:
    """
    Collect free-text description and photo evidence.
    """
    # This node would be hit after the user selects a category.
    # We'll assume the category is already picked or will be picked.
    return {
        "messages": [
            "Please describe the issue in your own words.",
            "If possible, please upload photos or screenshots that show what you’re seeing (inverter screen, app screenshots, physical damage, etc.)."
        ]
    }

def service_ticket_create(state: State) -> Dict:
    """
    Create a service ticket and check for human availability.
    Matches Step 4.3 requirements.
    """
    ticket_id = f"TICKET-{uuid.uuid4().hex[:8].upper()}"
    agent_online = check_agent_availability("service")
    
    messages = []
    if not agent_online:
        messages.append("Our service team is currently offline. I’ll create a ticket with all the details you’ve shared so we can follow up.")
    else:
        # If online, the graph should have handled the "Live Chat" question before this 
        # but for simplicity in deterministic mode, we'll inform them and create ticket.
        messages.append(f"We have a service executive available right now. I've also created a ticket for your records.")

    messages.append(f"Your service ticket has been created. Ticket number: {ticket_id}. Our team will reach out to you shortly.")

    return {
        "ticket_id": ticket_id,
        "representative_available": agent_online,
        "messages": messages
    }

def service_nps_and_close(state: State) -> Dict:
    """
    Handle NPS and close conversation.
    Matches Step 4.2 requirements.
    """
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
    Prompt for system and installer information.
    """
    return {
        "messages": [
            "We can still help, but we’ll need a few details about your setup.",
            "Approximate system size (kWp)",
            "Inverter brand/model",
            "Year of installation",
            {
                "type": "ai",
                "content": "Is online monitoring active?",
                "additional_kwargs": {
                    "options": [
                        {"label": "Yes", "value": "Yes"},
                        {"label": "No", "value": "No"}
                    ]
                }
            },
            "Who installed your system? (Enter name or 'Don’t remember')"
        ],
        "service_step": "system_info"
    }

def unregistered_system_router(state: State) -> str:
    """
    Route after system info is collected.
    """
    # For Week 1 deterministic, we'll assume info is provided if we are in this step
    if state.get("service_step") == "system_info":
        return "service_unregistered_issue_start"
    return END

def service_unregistered_issue_start(state: State) -> Dict:
    """
    Collect issue details for unregistered systems.
    """
    return {
        "messages": [
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
            },
            "Please describe the issue in your own words.",
            "If possible, please upload photos or screenshots that show what you’re seeing."
        ],
        "service_step": "issue_info"
    }

def unregistered_issue_router(state: State) -> str:
    """
    Route after issue info is collected.
    """
    if state.get("service_step") == "issue_info":
        return "service_ticket_create"
    return END
