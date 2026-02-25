from typing import TypedDict, Annotated, Dict
from langgraph.graph import StateGraph, END
from src.state import State
from src.nodes.entry import entry_node, support_router
from src.nodes.auth import (
    auth_collect_contact, auth_send_otp, auth_verify_otp, auth_router, auth_failed_node
)
from src.nodes.lookup import customer_lookup, post_auth_router, lookup_failure_router, lookup_reset_for_retry
from src.nodes.service import (
    service_status_check, service_resolution_router, service_issue_capture, 
    service_issue_context_collect, service_ticket_create, service_nps_and_close, 
    service_unregistered_start,
    unregistered_system_router,
    issue_capture_router, issue_context_router,
    service_availability_check, availability_router, service_live_chat_start
)
from src.nodes.sales import sales_start, sales_proposal_generate, sales_proposal_confirm, sales_router, sales_proposal_review, sales_info_capture, sales_existing_router

def create_graph():
    workflow = StateGraph(State)

    # Entry & Routing
    workflow.add_node("entry_node", entry_node)
    workflow.set_entry_point("entry_node")

    # Auth Flow
    workflow.add_node("auth_collect_contact", auth_collect_contact)
    workflow.add_node("auth_send_otp", auth_send_otp)
    workflow.add_node("auth_verify_otp", auth_verify_otp)
    workflow.add_node("auth_failed_node", auth_failed_node)
    
    # Lookup
    workflow.add_node("customer_lookup", customer_lookup)
    
    def lookup_failure_node(state: State) -> Dict:
        return {} # Just a pass-through node for routing
        
    workflow.add_node("lookup_failure_node", lookup_failure_node)
    workflow.add_node("lookup_reset_for_retry", lookup_reset_for_retry)

    # Service Flow
    workflow.add_node("service_status_check", service_status_check)
    workflow.add_node("service_issue_capture", service_issue_capture)
    workflow.add_node("service_issue_context_collect", service_issue_context_collect)
    workflow.add_node("service_availability_check", service_availability_check)
    workflow.add_node("service_live_chat_start", service_live_chat_start)
    workflow.add_node("service_ticket_create", service_ticket_create)
    workflow.add_node("service_nps_and_close", service_nps_and_close)
    workflow.add_node("service_unregistered_start", service_unregistered_start)

    # Sales Flow
    workflow.add_node("sales_start", sales_start)
    workflow.add_node("sales_existing_router", lambda x: x) # Compliance node
    workflow.add_node("sales_proposal_review", sales_proposal_review)
    workflow.add_node("sales_info_capture", sales_info_capture)
    workflow.add_node("sales_proposal_generate", sales_proposal_generate)
    workflow.add_node("sales_proposal_confirm", sales_proposal_confirm)

    workflow.add_conditional_edges("entry_node", support_router, {
        "auth_collect_contact": "auth_collect_contact",
        "auth_verify_otp": "auth_verify_otp",
        "customer_lookup": "customer_lookup",
        "service_status_check": "service_status_check",
        "lookup_failure_node": "lookup_failure_node",
        "sales_start": "sales_start",
        "__end__": END
    })

    workflow.add_conditional_edges("auth_collect_contact", 
        lambda state: "auth_send_otp" if state.get("auth_identifier_value") else "__end__",
        {
            "auth_send_otp": "auth_send_otp",
            "__end__": END
        }
    )
    
    workflow.add_edge("auth_send_otp", END)

    
    workflow.add_conditional_edges("auth_verify_otp", auth_router, {
        "customer_lookup": "customer_lookup",
        "auth_verify_otp": "auth_verify_otp",
        "auth_failed_node": "auth_failed_node",
        "__end__": END
    })
    
    workflow.add_edge("auth_failed_node", END)

    workflow.add_conditional_edges("customer_lookup", post_auth_router, {
        "service_status_check": "service_status_check",
        "lookup_failure_node": "lookup_failure_node",
        "sales_start": "sales_start",
        "__end__": END
    })

    # Choice node for failed lookup
    workflow.add_conditional_edges("lookup_failure_node", lookup_failure_router, {
        "lookup_reset_for_retry": "lookup_reset_for_retry",
        "service_unregistered_start": "service_unregistered_start",
        "__end__": END
    })

    workflow.add_edge("lookup_reset_for_retry", "auth_collect_contact")

    # Service edges
    workflow.add_conditional_edges("service_status_check", service_resolution_router, {
        "service_nps_and_close": "service_nps_and_close",
        "service_issue_capture": "service_issue_capture",
        "__end__": END
    })
    
    # Sequence for escalation:
    # 1. Capture asks for category -> END to wait for input
    # 2. Context Collect asks for desc/photos -> END to wait for input
    # 3. Create Ticket generates ID and ends conversation
    workflow.add_conditional_edges("service_issue_capture", issue_capture_router, {
        "service_issue_context_collect": "service_issue_context_collect",
        "__end__": END
    })
    workflow.add_conditional_edges("service_issue_context_collect", issue_context_router, {
        "service_availability_check": "service_availability_check",
        "__end__": END
    })
    
    workflow.add_conditional_edges("service_availability_check", availability_router, {
        "service_live_chat_start": "service_live_chat_start",
        "service_ticket_create": "service_ticket_create",
        "__end__": END
    })
    
    # Unregistered path sequence merges directly into standard escalation
    workflow.add_conditional_edges("service_unregistered_start", unregistered_system_router, {
        "service_issue_capture": "service_issue_capture",
        "__end__": END
    })
    
    workflow.add_edge("service_live_chat_start", END)
    workflow.add_edge("service_ticket_create", END)
    
    workflow.add_edge("service_nps_and_close", END)

    # Sales edges
    workflow.add_conditional_edges("sales_start", sales_router, {
        "sales_proposal_review": "sales_proposal_review",
        "sales_info_capture": "sales_info_capture",
        "__end__": END
    })
    
    workflow.add_conditional_edges("sales_proposal_review", sales_router, {
        "sales_info_capture": "sales_info_capture",
        "sales_proposal_confirm": "sales_proposal_confirm",
        "__end__": END
    })
    
    workflow.add_conditional_edges("sales_info_capture", sales_router, {
        "sales_info_capture": "sales_info_capture",
        "sales_proposal_generate": "sales_proposal_generate",
        "__end__": END
    })
    
    workflow.add_conditional_edges("sales_proposal_generate", sales_router, {
        "sales_proposal_confirm": "sales_proposal_confirm",
        "__end__": END
    })
    
    workflow.add_edge("sales_proposal_confirm", END)

    return workflow.compile()

graph = create_graph()
