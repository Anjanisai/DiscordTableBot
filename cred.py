import json
import os
from typing import Dict, Any

def load_credentials(file_path: str = "firebase_credentials.json") -> Dict[str, Any]:
    """Load Firebase credentials from JSON file with validation"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Firebase credentials file not found at {file_path}")
    
    with open(file_path) as f:
        try:
            creds = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in credentials file: {e}")
    
    # Validate required fields
    required_fields = {'type', 'project_id', 'private_key_id', 'private_key', 
                      'client_email', 'client_id', 'auth_uri', 'token_uri', 
                      'auth_provider_x509_cert_url', 'client_x509_cert_url'}
    
    if not required_fields.issubset(creds.keys()):
        missing = required_fields - set(creds.keys())
        raise ValueError(f"Missing required fields in credentials: {missing}")
    
    return creds

def print_credentials(file_path: str = "firebase_credentials.json") -> None:
    """Safely print credentials (with sensitive data redaction for production)"""
    creds = load_credentials(file_path)
    redacted = {**creds, 'private_key': '***REDACTED***'}  # Never print private keys
    print(json.dumps(redacted, indent=2))

# Example usage
if __name__ == "__main__":
    print_credentials()