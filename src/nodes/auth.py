from src.state import State
from src.utils.data_loader import verify_otp_sim
from typing import Dict
from langgraph.graph import END

def auth_collect_contact(state: State) -> Dict:
    """
    Node to prompt for email or phone.
    """
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None
    
    auth_type = state.get("auth_identifier_type")
    auth_val = state.get("auth_identifier_value")
    auth_step = state.get("auth_step")

    if last_msg:
        last_type = last_msg.get("type") if isinstance(last_msg, dict) else "ai"
        if last_type == "human":
            content = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
            
            if auth_step == "failed":
                if "Retry" in content or "retry" in content.lower():
                    return {
                        "auth_step": "identifier",
                        "auth_identifier_type": "",
                        "auth_identifier_value": "",
                        "auth_otp_sent": "",
                        "auth_otp_retries": 0,
                        "messages": [
                            {
                                "type": "ai",
                                "content": "Please continue with either your registered email or phone number.",
                                "additional_kwargs": {
                                    "options": [
                                        {"label": "Use email", "value": "email"},
                                        {"label": "Use phone", "value": "phone"}
                                    ]
                                }
                            }
                        ]
                    }
                elif "Exit" in content or "exit" in content.lower():
                    return {"messages": [{"type": "ai", "content": "Please refresh the page to start over or select a new support option."}], "auth_step": "exit"}

            if not auth_type or auth_type == "":
                # Expecting 'Use email' or 'Use phone'
                if "use email" in content.lower():
                    return {
                        "auth_identifier_type": "email",
                        "messages": [{"type": "ai", "content": "Enter your email address."}]
                    }
                elif "use phone" in content.lower():
                    return {
                        "auth_identifier_type": "phone",
                        "messages": [{"type": "ai", "content": "Enter your mobile number."}]
                    }
            elif not auth_val or auth_val == "":
                # Expecting the actual identifier string
                if auth_type == "email" and "@" in content:
                    return {"auth_identifier_value": content.strip().split()[-1]}
                elif auth_type == "phone" and any(c.isdigit() for c in content):
                    phone = "".join(c for c in content if c.isdigit() or c == '-')
                    return {"auth_identifier_value": phone}

    # If we haven't asked yet or they gave invalid input
    if not auth_type or auth_type == "":
        return {
            "messages": [
                {
                    "type": "ai",
                    "content": "Please continue with either your registered email or phone number.",
                    "additional_kwargs": {
                        "options": [
                            {"label": "Use email", "value": "email"},
                            {"label": "Use phone", "value": "phone"}
                        ]
                    }
                }
            ],
            "auth_step": "identifier"
        }
    elif not auth_val or auth_val == "":
        # Prompt again if input was invalid
        prompt = "Enter your email address." if auth_type == "email" else "Enter your mobile number."
        return {"messages": [{"type": "ai", "content": prompt}]}
        
    return {}


def auth_send_otp(state: State) -> Dict:
    """
    Simulate sending OTP.
    """
    channel = state.get("auth_identifier_type")
    channel_name = "email" if channel == "email" else "SMS"
    
    return {
        "messages": [
            f"We’re sending you a one-time code. Please check your {channel_name} and enter the code here."
        ],
        "auth_step": "otp",
        "auth_otp_retries": 0
    }

def auth_verify_otp(state: State) -> Dict:
    """
    Verify the 6-digit code.
    """
    user_otp = state.get("auth_otp_sent")
    messages = state.get("messages", [])
    
    if not user_otp and messages:
        last_msg = messages[-1]
        last_type = last_msg.get("type") if isinstance(last_msg, dict) else "ai"
        if last_type == "human":
            content = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
            # Find a 4 to 6 digit number
            import re
            match = re.search(r'\b\d{4,6}\b', content)
            if match:
                user_otp = match.group()
            else:
                user_otp = "".join(filter(str.isdigit, content))

    identifier = state.get("auth_identifier_value")
    channel = state.get("auth_identifier_type")
    
    # Needs a fallback if user_otp is completely blank or missing
    if not user_otp:
        return {
            "messages": ["I didn't catch a 6-digit code. Please enter the OTP sent to your device."]
        }
    
    is_correct = verify_otp_sim(identifier, user_otp, channel)
    
    if is_correct:
        return {
            "auth_verified": True,
            "auth_step": "verified"
        }
    else:
        retries = state.get("auth_otp_retries", 0) + 1
        return {
            "auth_otp_retries": retries,
            "auth_verified": False,
            "messages": ["That code doesn’t look right. Please try again."]
        }

def auth_failed_node(state: State) -> Dict:
    """
    Terminal node for failed authentication.
    """
    return {
        "auth_step": "failed",
        "messages": [
            {
                "type": "ai",
                "content": "We couldn’t verify your identity right now. Would you like to try again or exit?",
                "additional_kwargs": {
                    "options": [
                        {"label": "Retry authentication", "value": "retry"},
                        {"label": "Exit", "value": "exit"}
                    ]
                }
            }
        ]
    }

def auth_router(state: State) -> str:
    """
    Conditional routing for OTP loop.
    """
    if state.get("auth_verified"):
        return "customer_lookup"
    
    if state.get("auth_otp_retries", 0) >= 3:
        return "auth_failed_node"

    return "__end__"
