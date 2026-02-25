from src.state import State
from src.utils.data_loader import load_customer_by_identifier
from typing import Dict
from langgraph.graph import END

def customer_lookup(state: State) -> Dict:
    """
    Lookup customer in the database using the verified identifier.
    """
    identifier = state.get("auth_identifier_value")
    customer_data = load_customer_by_identifier(identifier)
    
    if customer_data:
        name = customer_data["customer_name"]
        location = customer_data["location"]
        return {
            "in_db": True,
            "customer_id": str(customer_data["customer_id"]),
            "customer_name": name,
            "location": location,
            "site_id": str(customer_data["site_id"]),
            "has_proposals": str(customer_data["has_proposals"]).lower() == "true",
            "messages": [f"Hi {name} from {location}, welcome back to SunBun."]
        }
    else:
        # Step 5.1: First failed lookup
        retries = state.get("lookup_retries", 0)
        
        if retries == 0:
            return {
                "in_db": False,
                "lookup_retries": 1,
                "messages": [
                    "We couldn’t find a system in our records matching this email/phone.",
                    "If you are an existing SunBun customer, please make sure you’re using the same email or phone number that you used for your monitoring portal.",
                    {
                        "type": "ai",
                        "content": "Would you like to try a different email/phone?",
                        "additional_kwargs": {
                            "options": [
                                {"label": "Try again", "value": "Try again"},
                                {"label": "No, continue anyway", "value": "No, continue anyway"}
                            ]
                        }
                    }
                ]
            }
        else:
            # Second fail - move to unregistered path
            return {
                "in_db": False,
                "messages": [
                    "It looks like we don’t have your system in our records. We can still help, but we’ll need a few details about your setup."
                ]
            }

def post_auth_router(state: State) -> str:
    """
    After auth/lookup, route to the appropriate flow.
    """
    support_type = state.get("support_type")
    in_db = state.get("in_db")
    retries = state.get("lookup_retries", 0)
    
    if support_type == "service":
        if in_db:
            return "service_status_check"
        else:
            if state.get("lookup_retry_choice"):
                return "lookup_failure_node"
            return END
    elif support_type == "sales":
        return "sales_start"
    
    return END

def lookup_failure_router(state: State) -> str:
    """
    Handle the 'Try again' vs 'No, continue anyway' choice.
    """
    choice = state.get("lookup_retry_choice")
    if choice == "Try again":
        return "lookup_reset_for_retry"
    elif choice == "No, continue anyway":
        return "service_unregistered_start"
    
    return END

def lookup_reset_for_retry(state: State) -> Dict:
    """
    Reset auth fields so the user can try a different identifier.
    """
    return {
        "auth_verified": False,
        "auth_step": "identifier",
        "auth_identifier_value": None,
        "auth_otp_sent": None,
        "auth_otp_retries": 0,
        "lookup_retry_choice": None
    }
