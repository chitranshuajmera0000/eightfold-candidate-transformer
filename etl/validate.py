"""
Stage 7: Validate
Check output matches expected types per schema.
"""
import json
import re
from typing import Dict, Any

EMAIL_RE = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]*[a-zA-Z0-9]$')
E164_RE = re.compile(r'^\+[1-9]\d{7,14}$')

def validate_output(record: Dict[str, Any], config: Dict[str, Any] = None) -> bool:
    """
    Validates that the output matches expected types.
    """
    try:
        json.dumps(record)
    except TypeError as e:
        raise TypeError(f"Output record is not JSON serializable: {e}")
        
    def check_email(e):
        if e and not EMAIL_RE.match(e):
            raise ValueError(f"Invalid email format: {e}")
            
    def check_phone(p):
        if p and not E164_RE.match(p):
            raise ValueError(f"Invalid phone format: {p}")
            
    for k, v in record.items():
        if "email" in k.lower() and isinstance(v, str):
            check_email(v)
        if "phone" in k.lower() and isinstance(v, str):
            check_phone(v)
            
    if not config or "fields" not in config:
        if record.get("full_name") is not None and not isinstance(record["full_name"], str):
            raise TypeError("full_name must be a string")
        
        emails = record.get("emails")
        if emails is not None:
            if not isinstance(emails, list):
                raise TypeError("emails must be a list")
            for em in emails:
                check_email(em)
                
        phones = record.get("phones")
        if phones is not None:
            if not isinstance(phones, list):
                raise TypeError("phones must be a list")
            for ph in phones:
                check_phone(ph)
                
    return True
