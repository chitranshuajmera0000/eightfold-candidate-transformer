"""
Stage 1: Detect
Identify the source type of each input file based on extension and structure.
"""
from pathlib import Path
from typing import Optional

def detect_source_type(file_path: str) -> Optional[str]:
    """Detects the source type of an input file."""
    path = Path(file_path)
    if not path.is_file():
        return None
    
    ext = path.suffix.lower()
    if ext == ".csv":
        return "csv"
    elif ext == ".txt":
        return "txt"
    elif ext == ".json":
        import json
        try:
            with open(path, mode='r', encoding='utf-8') as f:
                data = json.load(f)
            # ATS JSON has "full_name" or "contact_email"
            # LinkedIn JSON has "firstName" and "lastName"
            # GitHub JSON has "login" or "public_repos"
            if isinstance(data, list) and len(data) > 0:
                sample = data[0]
                if isinstance(sample, dict):
                    if "full_name" in sample or "contact_email" in sample:
                        return "ats_json"
                    elif "firstName" in sample:
                        return "linkedin_json"
                    elif "login" in sample or "public_repos" in sample:
                        return "github_json"
                    else:
                        print(f"Warning: JSON file {file_path} does not contain expected keys. Skipping.")
                        return None
        except Exception as e:
            print(f"Warning: Could not parse JSON file {file_path}: {e}")
            return None
    return None
