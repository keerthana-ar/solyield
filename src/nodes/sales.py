from src.state import State
from src.utils.data_loader import load_proposals_by_customer, get_proposal_templates, check_agent_availability
from typing import Dict, List
import uuid

def sales_start(state: State) -> Dict:
    """
    Step 6.1 & 7: Greeting and context.
    """
    in_db = state.get("in_db")
    customer_name = state.get("customer_name") or "there"
    has_proposals = state.get("has_proposals")
    customer_id = state.get("customer_id")
    
    messages = []
    
    if in_db is False:
        # Step 7.1
        messages.append("We couldn’t find an existing SunBun system under your details. Let’s collect some information to prepare a customized solar proposal for you.")
    
    messages.append(f"Hi {customer_name}, how can we help with your solar plans today?")
    
    if in_db and has_proposals:
        messages.append("We see that we’ve previously shared one or more proposals with you.")
        return {
            "messages": messages,
            "sales_step": "greeting",
            "proposals": load_proposals_by_customer(customer_id)
        }
    else:
        # Step 6.1 (no proposals) or Step 7 (not in DB)
        return {
            "messages": messages,
            "sales_step": "context"
        }

def sales_existing_router(state: State) -> str:
    """
    Step 8.2: branch if customer has prior proposals.
    Router for the first sales turn if proposals exist.
    """
    choice = state.get("sales_review_choice")
    if choice == "Review old proposals":
        return "sales_proposal_review"
    elif choice == "Create new proposals":
        return "sales_info_capture"
    
    # Wait for input
    return "__end__"

def sales_proposal_review(state: State) -> Dict:
    """
    Step 6.2: Reviewing old proposals.
    """
    proposals = state.get("proposals", [])
    messages = ["Here are your past proposals:"]
    
    for p in proposals:
        card = f"Proposal: {p.get('name')}\nPrice: {p.get('price')}\nSavings: {p.get('savings')}\nDate: {p.get('date')}\nStatus: {p.get('status')}"
        messages.append(card)
        
    messages.append({
        "type": "ai",
        "content": "Would you like to proceed with any of these proposals, or generate new options?",
        "additional_kwargs": {
            "options": [
                {"label": "Select a proposal", "value": "Select a proposal"},
                {"label": "Generate new options", "value": "Generate new options"}
            ]
        }
    })
    
    return {
        "messages": messages,
        "sales_step": "review"
    }

def sales_info_capture(state: State) -> Dict:
    """
    Step 6.3: Creating new proposals.
    Progressively collect customer context, segment, demand, and preferences.
    """
    messages = []
    
    # 6.3.1: Context (Name, Postal code, email/phone)
    if not state.get("sales_postal_code"):
        return {
            "messages": ["Great! Let’s get some details for your new proposal.", "Please provide your postal code and city."],
            "sales_step": "context"
        }
        
    # 6.3.2: Segment
    if not state.get("sales_segment_choice"):
        return {
            "messages": [{
                "type": "ai",
                "content": "Are you a Residential, Commercial, or Industrial customer?",
                "additional_kwargs": {
                    "options": [
                        {"label": "Residential", "value": "Residential"},
                        {"label": "Commercial", "value": "Commercial"},
                        {"label": "Industrial", "value": "Industrial"}
                    ]
                }
            }],
            "sales_step": "segment"
        }
        
    # 6.3.3: Demand
    if not state.get("sales_monthly_bill"):
        return {
            "messages": ["What is your average monthly electricity bill (in currency)?"],
            "sales_step": "usage_bill"
        }
    if not state.get("sales_consumption_increase"):
        return {
            "messages": ["By what percentage do you expect your electricity consumption to increase in the next few years (e.g., EV, heating, new loads)?"],
            "sales_step": "usage_increase"
        }
        
    # 6.3.4: Design Preferences
    if not state.get("sales_solution_count"):
        return {
            "messages": ["How many solution options would you like to evaluate right now? (1-3)"],
            "sales_step": "design_count"
        }
    
    # Brand or Budget
    if state.get("sales_brand_preferences") is None and state.get("sales_budget_tiers") is None:
        return {
            "messages": [
                "Do you have any brand preferences for Inverters (Enphase, SolarEdge, Sungrow, GoodWe) or Modules (Jinko, Trina, Waaree)?",
                "If not, would you prefer Premium, Standard, or Budget options? (You can pick more than one)"
            ],
            "sales_step": "design_prefs"
        }

    # If all collected, move to generation
    return {
        "messages": ["Give us a moment while we design the best options based on your requirements."],
        "sales_step": "design_complete"
    }

def sales_proposal_generate(state: State) -> Dict:
    """
    Step 6.4: Backend proposal generation.
    """
    templates = get_proposal_templates()
    budget_tiers = state.get("sales_budget_tiers") or ["Standard"]
    count = state.get("sales_solution_count") or 1
    
    # filter by tier
    options = [t for t in templates if t.get("category") in budget_tiers]
    if not options:
        options = templates
        
    selected = options[:count]
    
    messages = ["I've designed these options for you:"]
    for p in selected:
        messages.append(f"{p.get('name')}: {p.get('price')} - Expected Savings: {p.get('savings')}")
        
    return {
        "proposals": selected,
        "messages": messages,
        "sales_step": "options"
    }

def sales_proposal_confirm(state: State) -> Dict:
    """
    Step 8.2 & 6.4: store chosen proposal and handoff to Inside Sales.
    """
    agent_online = check_agent_availability("sales")
    proposal_name = state.get("chosen_proposal_name") or "the selected"
    
    messages = [f"Thank you for your interest in the {proposal_name} option."]
    
    if agent_online:
        messages.append({
            "type": "ai",
            "content": "Would you prefer to speak with our sales representative via call or chat?",
            "additional_kwargs": {
                "options": [
                    {"label": "Call", "value": "Call"},
                    {"label": "Chat", "value": "Chat"}
                ]
            }
        })
    else:
        messages.append("Our sales team is currently unavailable for live conversations, but we’ve logged your interest.")
        messages.append("You’ll receive a call or email from our team soon with the next steps.")
        messages.append("Thank you for considering SunBun. We’ll be in touch shortly.")
        
    return {
        "messages": messages,
        "representative_available": agent_online,
        "sales_step": "confirm"
    }

def sales_router(state: State) -> str:
    """
    Final router for Sales flow turns.
    """
    step = state.get("sales_step")
    
    if step == "greeting":
        return sales_existing_router(state)
        
    if step == "review":
        # Check if they chose a proposal or "Generate new"
        choice = state.get("sales_review_result")
        if choice == "Generate new options":
            return "sales_info_capture"
        elif choice == "Select a proposal":
            return "sales_proposal_confirm"
        return "__end__"
        
    if step == "design_complete":
        return "sales_proposal_generate"
        
    if step == "options":
        if state.get("chosen_proposal_id"):
            return "sales_proposal_confirm"
        return "__end__"

    # Input capture steps should pause for user input
    input_steps = ["context", "segment", "usage_bill", "usage_increase", "design_count", "design_prefs"]
    if step in input_steps:
        return "__end__"
        
    # Default to capture turns if not completed
    return "sales_info_capture"
