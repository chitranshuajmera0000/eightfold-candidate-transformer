"""
Stage 3: Normalize
Normalize phones to E.164, skills to canonical, dates to YYYY-MM.
"""
import re
from typing import Dict, Any, Optional, List

SKILL_ALIASES = {
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "python": "Python",
    "aws": "AWS",
    "docker": "Docker",
    "devops": "DevOps",
    "react": "React",
    "node": "Node.js",
    "nodejs": "Node.js",
    "sql": "SQL",
    "java": "Java",
    "typescript": "TypeScript",
    "ts": "TypeScript"
}

def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """Normalize phone to E.164. Rejects unparseable rather than fabricating."""
    if not phone or not isinstance(phone, str):
        return None
        
    phone_clean = phone.strip()
    digits = re.sub(r'\D', '', phone_clean)
    
    if len(digits) not in (10, 11, 12):
        return None
        
    # 1. Match Indian 5-5 grouping (e.g. "98989 89898" or "98989-89898")
    if re.search(r'(?:\+?91[\s-]?)?\b\d{5}[\s-]\d{5}\b', phone_clean):
        return f"+91{digits[-10:]}"
        
    # 2. Explicit country code
    if phone_clean.startswith('+91') or (len(digits) == 12 and digits.startswith('91')):
        return f"+{digits}"
    if phone_clean.startswith('+1') or (len(digits) == 11 and digits.startswith('1')):
        return f"+{digits}"
        
    # 3. US grouping (3-3-4)
    if re.search(r'(?:\+?1[\s-]?)?\(?\b\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b', phone_clean):
        return f"+1{digits[-10:]}"
        
    # 4. Ambiguous exactly 10 digits
    if len(digits) == 10:
        # Default to India (+91) as per user requirement for Indian dataset
        return f"+91{digits}"
        
    return None

def normalize_skills(skills: Optional[List[str]]) -> List[str]:
    """Map skills to canonical names, remove duplicates."""
    if not skills:
        return []
        
    if not isinstance(skills, list):
        # Try to convert string to list if it was mistakenly parsed as a single string
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(',')]
        else:
            return []
            
    normalized = []
    seen = set()
    for s in skills:
        if not isinstance(s, str):
            continue
        s_clean = s.strip()
        if not s_clean:
            continue
            
        canonical = SKILL_ALIASES.get(s_clean.lower(), s_clean)
        canonical_lower = canonical.lower()
        if canonical_lower not in seen:
            normalized.append(canonical)
            seen.add(canonical_lower)
            
    return normalized

def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Applies normalization to an intermediate record."""
    normalized = record.copy()
    
    if normalized.get("phone"):
        normalized["phone"] = normalize_phone(normalized["phone"])
        
    if normalized.get("skills"):
        normalized["skills"] = normalize_skills(normalized["skills"])
    
    # years_experience passes through as-is (already numeric or None)
    
    return normalized
