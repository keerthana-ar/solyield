from langchain_core.messages import AIMessage, HumanMessage
from src.state import State
from src.utils.data_loader import load_proposals_by_customer, get_proposal_templates, check_agent_availability
from typing import Dict, List
from langgraph.graph import END
import uuid

def sales_start(state: State) -> Dict:
    """
    Step 6.1 & 7: Greeting and context.
    """
    # Prevent re-running if we already passed greeting
    if state.get("sales_step") and state.get("sales_step") != "greeting":
         return {}
         
    messages = state.get("messages", [])
    
    # Anti-spam check: Did we already ask how to help with solar plans?
    def _msg_content(m: object) -> str:
        if isinstance(m, str):
            return m
        if isinstance(m, dict):
            return str(m.get("content") or m.get("text") or "")
        # LangGraph/LangChain may store messages as objects with `.content`
        return str(getattr(m, "content", "") or "")

    prompt_marker = "how can we help with your solar plans"
    if any(prompt_marker in (_msg_content(m) or "").lower() for m in messages):
        
        # Check if user made a choice
        if messages:
            last_msg = messages[-1]
            last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
            if last_type == "human":
                content = getattr(last_msg, "content", last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg))
                content = str(content).lower()
                # ULTRA PERMISSIVE: If they said anything, assume they want a choice
                if "old" in content or "review" in content:
                    return {
                        "sales_review_choice": "Review old proposals",
                        "sales_step": "sales_proposal_review"
                    }
                else:
                    # DEFAULT TO CREATE NEW (The most common path for Demo 1)
                    return {
                        "sales_review_choice": "Create new proposals",
                        "sales_step": "sales_info_capture"
                    }
                    
        return {} # Wait for input

    in_db = state.get("in_db")
    customer_name = state.get("customer_name") or "there"
    has_proposals = state.get("has_proposals")
    customer_id = state.get("customer_id")
    
    new_messages = []
    
    if in_db is False:
        new_messages.append({"type": "ai", "content": "We couldn’t find an existing SunBun system under your details. Let’s collect some information to prepare a customized solar proposal for you."})
    else:
        new_messages.append({"type": "ai", "content": f"Hi {customer_name}, how can we help with your solar plans today?"})
        
    if in_db and has_proposals:
        new_messages.append({"type": "ai", "content": "We see that we’ve previously shared one or more proposals with you."})
        new_messages.append({
            "type": "ai",
            "content": "Would you like to review those, or create new options?",
            "additional_kwargs": {
                "options": [
                    {"label": "Review old proposals", "value": "Review old proposals"},
                    {"label": "Create new proposals", "value": "Create new proposals"}
                ]
            }
        })
        return {
            "messages": new_messages,
            "sales_step": "greeting",
            "proposals": load_proposals_by_customer(customer_id)
        }
    else:
        # Step 6.1 (no proposals) or Step 7 (not in DB)
        # Fast-forward to context collection with strict logic
        return {
            "messages": new_messages,
            "sales_review_choice": "Create new proposals",
            "sales_step": "sales_info_capture"
        }

def sales_existing_router(state: State) -> str:
    """
    Step 8.2: branch if customer has prior proposals.
    Router for the first sales turn if proposals exist.
    """
    # If we already passed the greeting phase, relinquish control to the master router!
    if state.get("sales_step") != "greeting":
        return sales_router(state)
        
    choice = state.get("sales_review_choice")
    if choice == "Review old proposals":
        return "sales_proposal_review"
    elif choice == "Create new proposals":
        return "sales_info_capture"
        
    # Check if they just replied to the greeting
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
        if last_type == "human":
             content = getattr(last_msg, "content", last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg))
             content = str(content).lower()
             if "old" in content or "review" in content:
                 return "sales_proposal_review"
             elif "new" in content or "create" in content:
                 return "sales_info_capture"
    
    # Wait for input
    return "__end__"

def sales_proposal_review(state: State) -> Dict:
    """
    Step 6.2: Reviewing old proposals.
    """
    # Read human input if provided
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
        if last_type == "human":
            content = getattr(last_msg, "content", last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg))
            content = str(content).lower()
            if "select" in content or "proceed" in content:
                 return {
                     "sales_review_result": "Select a proposal", 
                     "chosen_proposal_name": "your previous",
                     "sales_step": "review_complete" # Move step forward
                 }
            elif "new" in content or "generate" in content:
                 return {
                     "sales_review_result": "Generate new options",
                     "sales_step": "review_complete" # Move step forward
                 }

    # Protection: Did we already print the proposals?
    if any(isinstance(m, str) and "Here are your past proposals" in m for m in messages) or \
       any(isinstance(m, dict) and "Here are your past proposals" in str(getattr(m, "content", m.get("content", "") if isinstance(m, dict) else "")) for m in messages):
        return {}

    proposals = state.get("proposals", [])
    messages = [{"type": "ai", "content": "Here are your past proposals:"}]
    
    for p in proposals:
        card = f"**Proposal:** {p.get('proposal_name')}\n**Price:** ${p.get('approx_price')}\n**Savings:** ${p.get('estimated_yearly_savings')}/yr\n**Date:** {p.get('date_created')}\n**Status:** {p.get('status')}\n[View full proposal](#)"
        messages.append({"type": "ai", "content": card})
        
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
        "sales_step": "review" # Lock the step
    }

def sales_info_capture(state: State) -> Dict:
    """
    Step 6.3: Creating new proposals.
    Progressively collect customer context, segment, demand, and preferences.
    """
    messages = state.get("messages", [])
    
    # Helper to check if a human just replied
    human_reply = ""
    if messages:
        last_msg = messages[-1]
        last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
        if last_type == "human":
            human_reply = getattr(last_msg, "content", last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg))

    # 0. Name Capture (Unregistered)
    in_db = state.get("in_db")
    if in_db is False and not state.get("customer_name"):
        if state.get("sales_step") == "name" and human_reply:
             return {"customer_name": human_reply}
             
        if any(isinstance(m, str) and "provide your full name" in m.lower() for m in messages) or \
           any(isinstance(m, dict) and "provide your full name" in str(getattr(m, "content", m.get("content", "") if isinstance(m, dict) else "")).lower() for m in messages):
            return {"sales_step": "name"}
            
        return {
            "messages": [{"type": "ai", "content": "Could you please provide your full name so we can personalize your proposal?"}],
            "sales_step": "name"
        }

    # 0.5 Contact Complement
    if state.get("sales_contact_complement") is None:
        auth_type = state.get("auth_identifier_type")
        missing_type = "email address" if auth_type == "phone" else "phone number"
        
        if state.get("sales_step") == "contact_complement" and human_reply:
             return {"sales_contact_complement": human_reply}
             
        if any(isinstance(m, str) and f"provide your {missing_type}" in m.lower() for m in messages) or \
           any(isinstance(m, dict) and f"provide your {missing_type}" in str(getattr(m, "content", m.get("content", "") if isinstance(m, dict) else "")).lower() for m in messages):
            return {"sales_step": "contact_complement"}
            
        return {
            "messages": [{"type": "ai", "content": f"Could you please also provide your {missing_type} so we can reach out with the proposal?"}],
            "sales_step": "contact_complement"
        }

    # 1. Postal Code & City
    if not state.get("sales_postal_code"):
        if state.get("sales_step") == "context" and human_reply:
             return {"sales_postal_code": human_reply}
             
        if any(isinstance(m, str) and "postal code and city" in m.lower() for m in messages) or \
           any(isinstance(m, dict) and "postal code and city" in str(getattr(m, "content", m.get("content", "") if isinstance(m, dict) else "")).lower() for m in messages):
            return {"sales_step": "context"}
            
        return {
            "messages": [{"type": "ai", "content": "Great! To prepare your new proposal, please provide your postal code and city."}],
            "sales_step": "context"
        }
        
    # 2. Segment
    if not state.get("sales_segment_choice"):
        if state.get("sales_step") == "segment" and human_reply:
             return {"sales_segment_choice": human_reply}

        if any(isinstance(m, dict) and "Are you a Residential, Commercial" in str(getattr(m, "content", m.get("content", "") if isinstance(m, dict) else "")) for m in messages):
            return {"sales_step": "segment"}
            
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
        
    # 3. Demand (Bill & Increase)
    # 3a. Bill
    if not state.get("sales_monthly_bill"):
        if state.get("sales_step") == "usage_bill" and human_reply:
             return {"sales_monthly_bill": human_reply}

        if any(isinstance(m, str) and "average monthly electricity bill" in m.lower() for m in messages) or \
           any(isinstance(m, dict) and "average monthly electricity bill" in str(getattr(m, "content", m.get("content", "") if isinstance(m, dict) else "")).lower() for m in messages):
            return {"sales_step": "usage_bill"}
            
        return {
            "messages": [{"type": "ai", "content": "What is your average monthly electricity bill (in currency)?"}],
            "sales_step": "usage_bill"
        }
        
    # 3b. Increase
    if not state.get("sales_consumption_increase"):
        if state.get("sales_step") == "usage_increase" and human_reply:
             return {"sales_consumption_increase": human_reply}

        if any(isinstance(m, str) and "expect your electricity consumption" in m.lower() for m in messages) or \
           any(isinstance(m, dict) and "expect your electricity consumption" in str(getattr(m, "content", m.get("content", "") if isinstance(m, dict) else "")).lower() for m in messages):
            return {"sales_step": "usage_increase"}
            
        return {
            "messages": [{"type": "ai", "content": "By what percentage do you expect your electricity consumption to increase in the next few years (e.g., EV, heating, new loads)?"}],
            "sales_step": "usage_increase"
        }
        
    # 4. Design Preferences
    # 4a. Count
    if not state.get("sales_solution_count"):
        if state.get("sales_step") == "design_count" and human_reply:
             import re
             num = re.sub(r'[^\d]', '', str(human_reply))
             count = int(num) if num else 1
             return {"sales_solution_count": count}

        if any(isinstance(m, str) and "How many solution options" in m for m in messages) or \
           any(isinstance(m, dict) and "How many solution options" in str(getattr(m, "content", m.get("content", "") if isinstance(m, dict) else "")) for m in messages):
            return {"sales_step": "design_count"}
            
        return {
            "messages": [{"type": "ai", "content": "How many solution options would you like to evaluate right now? (up to 5)"}],
            "sales_step": "design_count"
        }
    
    # 4b. Brand Preferences
    if state.get("sales_brand_preferences") is None:
        if state.get("sales_step") == "design_brand" and human_reply:
             return {"sales_brand_preferences": [human_reply]}

        if any(isinstance(m, str) and "brand preferences" in m for m in messages) or \
           any(isinstance(m, dict) and "brand preferences" in str(getattr(m, "content", m.get("content", "") if isinstance(m, dict) else "")) for m in messages):
            return {"sales_step": "design_brand"}
            
        return {
            "messages": [{"type": "ai", "content": "Do you have any brand preferences for Inverters (Enphase, SolarEdge, Sungrow, GoodWe) or Modules (Jinko, Trina, Waaree)?"}],
            "sales_step": "design_brand"
        }
        
    # 4c. Budget Tier
    if state.get("sales_budget_tiers") is None:
        # Check if they had distinct brand preferences, skip tier if true
        brand_prefs = state.get("sales_brand_preferences", [])
        brand_str = brand_prefs[0] if brand_prefs else ""
        if brand_str and brand_str.lower() not in ["no", "none", "nope", "n/a"]:
            return {"sales_budget_tiers": ["Standard"], "sales_step": "generating"}

        if state.get("sales_step") == "design_tier" and human_reply:
             return {"sales_budget_tiers": [human_reply], "sales_step": "generating"}

        if any(isinstance(m, str) and "prefer Premium, Standard" in m for m in messages) or \
           any(isinstance(m, dict) and "prefer Premium, Standard" in str(getattr(m, "content", m.get("content", "") if isinstance(m, dict) else "")) for m in messages):
            return {"sales_step": "design_tier"}
            
        return {
            "messages": [
                {
                    "type": "ai",
                    "content": "Would you prefer Premium, Standard, or Budget options? You can pick more than one.",
                    "additional_kwargs": {
                        "checkboxes": [
                            {"label": "Premium", "value": "Premium"},
                            {"label": "Standard", "value": "Standard"},
                            {"label": "Budget", "value": "Budget"}
                        ]
                    }
                }
            ],
            "sales_step": "design_tier"
        }

    # 5. Transition to Generation
    if state.get("sales_step") != "generating":
        return {
            "messages": [{"type": "ai", "content": "Give us a moment while we design the best options based on your requirements."}],
            "sales_step": "generating" # Lock the transition
        }
    return {}

def sales_proposal_generate(state: State) -> Dict:
    """
    Step 6.4: Backend proposal generation.
    """
    if state.get("sales_step") == "options":
        # Waiting for user to select a proposal
        messages = state.get("messages", [])
        if messages:
             last_msg = messages[-1]
             last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
             if last_type == "human":
                  content = getattr(last_msg, "content", last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg))
                  # If they selected an option
                  return {"chosen_proposal_id": "PROP-NEW", "chosen_proposal_name": content}
        return {}

    templates = get_proposal_templates()
    tiers = state.get("sales_budget_tiers", ["Standard"])
    tier = tiers[0] if tiers else "Standard"
              
    count = state.get("sales_solution_count") or 1
    
    # filter by tier
    options = [t for t in templates if t.get("category") == tier]
    if not options:
        options = templates
        
    selected = options[:count]
    
    messages = ["I've designed these options for you:"]
    for p in selected:
        messages.append({"type": "ai", "content": f"**{p.get('proposal_name')}**\nExpected Savings: ${p.get('estimated_yearly_savings')}/yr | Approx Price: ${p.get('approx_price')}\n[View full proposal](#)"})
        
    messages.append({
        "type": "ai",
        "content": "Which option would you like to select?",
        "additional_kwargs": {
            "options": [{"label": f"Select {p.get('proposal_name')}", "value": p.get('proposal_name')} for p in selected]
        }
    })
        
    return {
        "proposals": selected,
        "messages": messages,
        "sales_step": "agent_feedback" # Force immediate transition to Assistant Moment
    }

def sales_proposal_confirm(state: State) -> Dict:
    """
    Step 8.2 & 6.4: store chosen proposal and handoff to Inside Sales.
    This is now preceded by the Sales Agent Assistant feedback loop.
    """
    if state.get("sales_step") == "confirm":
        # We are pausing for the call/chat payload from the user
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
            if last_type == "human":
                content = getattr(last_msg, "content", last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg))
                cust_name = state.get("customer_name") or "customer"
                prop_name = state.get("chosen_proposal_name") or "proposal"
                content = str(content).lower()
                
                final_msgs = []
                if "call" in content:
                    final_msgs.append({"type": "ai", "content": f"CRM Task created: 'Call {cust_name} about {prop_name} within 1 hour.'"})
                elif "chat" in content:
                    final_msgs.append({"type": "ai", "content": "CRM Opportunity created: Opening live chat with Inside Sales..."})
                    
                final_msgs.append({"type": "ai", "content": "Thank you for using the SunBun Sales Assistant. The workflow is complete."})
                return {
                    "messages": final_msgs,
                    "sales_step": "handoff"
                }
        return {}
        
    agent_online = check_agent_availability("sales")
    proposal_name = state.get("chosen_proposal_name") or "the selected"
    
    messages = [{"type": "ai", "content": f"The {proposal_name} option has been confirmed and shared."}]
    
    if agent_online:
        messages.append({
            "type": "ai",
            "content": "Would you like to initiate a live call or chat with the customer now?",
            "additional_kwargs": {
                "options": [
                    {"label": "Call Customer", "value": "Call"},
                    {"label": "Start Chat", "value": "Chat"}
                ]
            }
        })
    else:
        messages.append({"type": "ai", "content": "The sales team has been notified. They will receive the proposal details automatically."})
        messages.append({"type": "ai", "content": "Thank you for using the SunBun Sales Assistant."})
        
    return {
        "messages": messages,
        "representative_available": agent_online,
        "sales_step": "handoff" if not agent_online else "confirm"
    }

# --- WEEK 2 BONUS: SALES AGENT ASSISTANT NODES ---

def sales_agent_feedback(state: State) -> Dict:
    """
    Bonus: Task the Agent to act as an assistant to a Sales Agent.
    Asks for feedback on the generated proposals before sharing.
    """
    # Phase 2: Handle reply
    if state.get("sales_step") == "agent_feedback_waiting":
        messages = state.get("messages", [])
        if messages:
             last_msg = messages[-1]
             last_type = getattr(last_msg, "type", last_msg.get("type", "ai") if isinstance(last_msg, dict) else "ai")
             if last_type == "human":
                  return {"sales_step": "feedback_reviewed"}
        return {}

    proposal_name = state.get("chosen_proposal_name") or "these options"
    return {
        "messages": [{
            "type": "ai", 
            "content": f"Proposals generated. As a Sales Assistant, I recommend the {proposal_name}. I can also list the top 5 options from our design system if you'd like. Do you have any feedback?",
            "additional_kwargs": {
                "options": [
                    {"label": "Looks Good", "value": "looks good"},
                    {"label": "List Top 5 Options", "value": "list top 5"},
                    {"label": "Modify / Feedback", "value": "feedback"}
                ]
            }
        }],
        "sales_step": "agent_feedback_waiting"
    }

def sales_proposal_share(state: State) -> Dict:
    """
    Bonus: Option to share the verified proposal with the customer.
    """
    if state.get("sales_step") == "proposal_share":
        messages = state.get("messages", [])
        if messages:
             last_msg = messages[-1]
             last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
             if last_type == "human":
                  return {"sales_step": "shared"}
        return {}

    return {
        "messages": [{
            "type": "ai",
            "content": "Proposal is ready. Should I share this with the customer now?",
            "additional_kwargs": {
                "options": [
                    {"label": "Yes, Share Now", "value": "share"},
                    {"label": "Wait, hold on", "value": "hold"}
                ]
            }
        }],
        "sales_step": "proposal_share"
    }

def sales_router(state: State) -> str:
    """
    Final router for Sales flow turns.
    """
    step = state.get("sales_step")
    
    if step == "greeting":
        # Check if the human just clicked one of the greeting buttons
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
            if last_type == "human":
                return sales_existing_router(state)
        return "__end__"
        
    if step == "review":
        # Check if the human just replied
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
            if last_type == "human":
                return "sales_proposal_review"
        return "__end__"
        
    if step == "review_complete":
        # Check if they chose a proposal or "Generate new"
        choice = state.get("sales_review_result")
        if choice == "Generate new options":
            return "sales_info_capture"
        elif choice == "Select a proposal":
            return "sales_proposal_confirm"
        return "__end__"
        
    if step == "generating":
        return "sales_proposal_generate"
        
    if step == "options":
        if state.get("chosen_proposal_id"):
            return "sales_agent_feedback" # Move to feedback instead of confirm
            
        # Check if the human just clicked a proposal button
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
            if last_type == "human":
                return "sales_proposal_generate"
                
        return "__end__"

    if step == "agent_feedback":
        # Proactive: We just arrived from the design node.
        return "sales_agent_feedback"
        
    if step == "agent_feedback_waiting":
        # Check if human replied
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            last_type = getattr(last_msg, "type", last_msg.get("type", "ai") if isinstance(last_msg, dict) else "ai")
            if last_type == "human":
                return "sales_agent_feedback"
        return "__end__"
        
    if step == "feedback_reviewed":
        return "sales_proposal_share"
        
    if step == "proposal_share":
        # Check if human replied
        messages = state.get("messages", [])
        if messages:
             last_msg = messages[-1]
             last_type = getattr(last_msg, "type", last_msg.get("type", "ai") if isinstance(last_msg, dict) else "ai")
             if last_type == "human":
                 return "sales_proposal_share"
        return "__end__"
        
    if step == "shared":
        return "sales_proposal_confirm"

    if step == "confirm":
        # Check if the human just replied with Call/Chat
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
            if last_type == "human":
                return "sales_proposal_confirm"
        return "__end__"

    if step == "handoff":
        return "__end__"

    # Input capture steps should pause for user input
    input_steps = ["name", "contact_complement", "context", "segment", "usage_bill", "usage_increase", "design_count", "design_brand", "design_tier"]
    if step in input_steps:
        # Check if the human just replied
        messages = state.get("messages", [])
        human_just_replied = False
        if messages:
            last_msg = messages[-1]
            last_type = getattr(last_msg, "type", last_msg.get("type") if isinstance(last_msg, dict) else "ai")
            if last_type == "human":
                human_just_replied = True
                
        # If the human replied, we MUST route to info_capture so it can extract the data!
        if human_just_replied:
            return "sales_info_capture"
            
        # If not, it means we just printed the question, so END to pause for input
        return "__end__"
        
    # Default to capture turns if not completed
    return "sales_info_capture"
