import pandas as pd
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "supportingData")

def get_csv_path(filename: str) -> str:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        # Fallback for local dev if pathing is weird
        path = os.path.join("supportingData", filename)
    return path

def load_customer_by_identifier(identifier: str):
    df = pd.read_csv(get_csv_path("customers.csv"))
    # Match email or phone
    match = df[(df['email'] == identifier) | (df['phone'].astype(str) == str(identifier))]
    if not match.empty:
        data = match.iloc[0].to_dict()
        # Rename 'name' to 'customer_name' for consistency with state
        data['customer_name'] = data.pop('name')
        return data
    return None

def load_site_by_id(site_id: str):
    df = pd.read_csv(get_csv_path("sites.csv"))
    match = df[df['site_id'].astype(str) == str(site_id)]
    if not match.empty:
        return match.iloc[0].to_dict()
    return None

def load_metrics_by_site(site_id: str):
    df = pd.read_csv(get_csv_path("weekly_metrics.csv"))
    match = df[df['site_id'].astype(str) == str(site_id)]
    return match.to_dict(orient="records")

def load_proposals_by_customer(customer_id: str):
    df = pd.read_csv(get_csv_path("proposals.csv"))
    match = df[df['customer_id'].astype(str) == str(customer_id)]
    return match.to_dict(orient="records")

def verify_otp_sim(identifier: str, otp: str, channel: str):
    filename = "email_otp.csv" if channel == "email" else "sms_otp.csv"
    id_col = "email" if channel == "email" else "phone"
    df = pd.read_csv(get_csv_path(filename))
    match = df[(df[id_col].astype(str) == str(identifier)) & (df['otp'].astype(str) == str(otp))]
    return not match.empty

def check_agent_availability(agent_type: str):
    df = pd.read_csv(get_csv_path("agent_availability.csv"))
    # agent_type will be 'sales' or 'service'
    dept = agent_type.capitalize() # 'Sales' or 'Service'
    match = df[(df['department'] == dept) & (df['is_online'].astype(str).str.lower() == 'true')]
    return not match.empty

def get_proposal_templates():
    df = pd.read_csv(get_csv_path("proposal_template.csv"))
    return df.to_dict(orient="records")

def load_site_issues():
    df = pd.read_csv(get_csv_path("site_issues.csv"))
    return df.to_dict(orient="records")
