"""
Stage 6: Project
Reshape canonical record to target schema based on config.
"""
from typing import Dict, Any

def extract_path(data: Any, path: str) -> Any:
    """Extract a value from a nested dict using a path string."""
    if not data or path is None:
        return None
        
    # Handle "skills[].name"
    if "[]." in path:
        list_key, rest = path.split("[].", 1)
        if isinstance(data, dict) and list_key in data and isinstance(data[list_key], list):
            return [extract_path(item, rest) for item in data[list_key]]
        return None
        
    # Handle "emails[0]"
    import re
    match = re.match(r'([a-zA-Z0-9_]+)\[(\d+)\]', path)
    if match:
        key = match.group(1)
        idx = int(match.group(2))
        if isinstance(data, dict) and key in data and isinstance(data[key], list) and len(data[key]) > idx:
            return data[key][idx]
        return None
        
    # Handle simple keys
    if isinstance(data, dict):
        return data.get(path)
    return None

def project(canonical_record: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Project canonical record to target schema based on config.
    """
    out = {}
    
    # If no config fields provided, return the full record.
    if "fields" not in config:
        out = {k: v for k, v in canonical_record.items() if not k.startswith("_")}
        if not config.get("include_confidence", True):
            out.pop("overall_confidence", None)
            if "skills" in out:
                for s in out["skills"]:
                    if isinstance(s, dict):
                        s.pop("confidence", None)
        if not config.get("include_provenance", True):
            out.pop("provenance", None)
        return out
        
    on_missing = config.get("on_missing", "null")
    
    for field_spec in config["fields"]:
        source_path = field_spec["from"]
        target_path = field_spec["path"]
        
        val = extract_path(canonical_record, source_path)
        
        # Handle per-field "normalize" override
        if field_spec.get("normalize") == "E164" and val:
            from .normalize import normalize_phone
            if isinstance(val, str):
                val = normalize_phone(val)
            elif isinstance(val, list):
                val = [normalize_phone(v) for v in val if isinstance(v, str)]
        elif field_spec.get("normalize") == "canonical" and val:
            from .normalize import normalize_skills
            if isinstance(val, list):
                # If list of dicts (skill objects), extract and canonicalize names
                if val and isinstance(val[0], dict):
                    val = normalize_skills([s.get("name", s) for s in val if isinstance(s, dict)])
                else:
                    val = normalize_skills(val)
            
        if val is None:
            if on_missing == "omit":
                continue
            elif on_missing == "error":
                raise ValueError(f"Required field missing: {source_path}")
            else: # "null"
                val = None
                
        out[target_path] = val
        
        # Inject field-level confidence if requested
        if config.get("include_confidence"):
            base_source_path = source_path.split("[")[0]
            if canonical_record.get("_confidences") and base_source_path in canonical_record["_confidences"]:
                out[f"{target_path}_confidence"] = canonical_record["_confidences"][base_source_path]
                
    if config.get("include_confidence") and canonical_record.get("overall_confidence") is not None:
        out["overall_confidence"] = canonical_record.get("overall_confidence")
        
    if config.get("include_provenance") and canonical_record.get("provenance"):
        out["provenance"] = canonical_record.get("provenance")
        
    return out
