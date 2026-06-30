"""
Stage 2: Extract
Parse raw fields out of each source into an intermediate dict.
"""
import csv
import re
from typing import List, Dict, Any, Optional

from .normalize import SKILL_ALIASES

def extract_from_csv(file_path: str) -> List[Dict[str, Any]]:
    """Extract candidate records from a CSV file."""
    records = []
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                cleaned_row = {str(k).strip().lower(): str(v).strip() for k, v in row.items() if k and v}
                name = cleaned_row.get("name")
                if not name or not isinstance(name, str) or not name.strip():
                    print(f"Warning: Missing required 'name' field in CSV {file_path} row {reader.line_num}. Skipping.")
                    continue
                
                record = {
                    "_source_type": "csv",
                    "_source_file": str(file_path),
                    "name": name.strip(),
                    "email": cleaned_row.get("email"),
                    "phone": cleaned_row.get("phone"),
                    "current_company": cleaned_row.get("current company"),
                    "title": cleaned_row.get("title"),
                    "start_date": cleaned_row.get("start date"),
                    "end_date": cleaned_row.get("end date"),
                    "city": cleaned_row.get("city"),
                    "country_code": cleaned_row.get("country"),
                    "linkedin_url": cleaned_row.get("linkedin")
                }
                records.append(record)
    except Exception as e:
        print(f"Error reading CSV {file_path}: {e}")
    return records

def extract_from_txt(file_path: str) -> Optional[Dict[str, Any]]:
    """Extract candidate info from free-text notes."""
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading TXT {file_path}: {e}")
        return None

    # Name: Naive extraction - captures overlapping pairs to handle "Interviewed Chitranshu Ajmera"
    possible_names = [m.group(1) for m in re.finditer(r'(?=\b([A-Z][a-zA-Z]+ [A-Z][a-zA-Z]+)\b)', content)]
    name = None
    stop_words = {"interviewed", "spoke", "contact", "also", "had", "discussed", "great", "excellent"}
    for p in possible_names:
        first_word = p.split()[0].lower()
        if first_word not in stop_words and p.lower() not in SKILL_ALIASES:
            name = p
            break

    # Phone: Match Indian formats (5-5 grouping, 10 digits) and US formats (3-3-4)
    # Indian: +91 98989 89898, 98765 43210, +91-9876543210
    # US: (555) 123-4567, 555-123-4567, +1 555 123 4567
    phone_patterns = [
        r'(?:\+?\d{1,3}[\s-])?\d{5}[\s-]?\d{5}',           # Indian: +91 98989 89898
        r'(?:\+?\d{1,3}[\s-])?\d{10}',                       # Indian: +919876543210
        r'(?:\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}',  # US: (555) 123-4567
    ]
    phone = None
    for pat in phone_patterns:
        phone_match = re.search(pat, content)
        if phone_match:
            phone = phone_match.group(0)
            break

    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]*[a-zA-Z0-9]'
    email_match = re.search(email_pattern, content)
    email = email_match.group(0) if email_match else None

    # Years of experience: e.g. "5 years of experience", "10+ years experience"
    yoe_match = re.search(r'(\d+)\+?\s*years?\s*(?:of\s*)?experience', content, re.IGNORECASE)
    years_experience = int(yoe_match.group(1)) if yoe_match else None

    # Skills: Check against canonical skill list
    skills = []
    content_lower = content.lower()
    for alias, canonical in SKILL_ALIASES.items():
        if re.search(r'\b' + re.escape(alias) + r'\b', content_lower):
            if canonical not in skills:
                skills.append(canonical)
                
    # LinkedIn
    linkedin_match = re.search(r'linkedin\.com/in/([a-zA-Z0-9-]+)', content)
    linkedin_url = f"https://linkedin.com/in/{linkedin_match.group(1)}" if linkedin_match else None
    
    # GitHub
    github_match = re.search(r'github\.com/([a-zA-Z0-9-]+)', content)
    github_url = f"https://github.com/{github_match.group(1)}" if github_match else None
    
    # Portfolio
    urls = re.findall(r'https?://[^\s]+|(?<!@)\b[a-zA-Z0-9.-]+\.(?:vercel\.app|github\.io|com|in|org|net|io|dev|app|co)\b(?:/[^\s]*)?', content)
    portfolio_url = None
    for u in urls:
        if "linkedin.com" not in u and "github.com" not in u:
            portfolio_url = u.rstrip('.,')
            if not portfolio_url.startswith('http'):
                portfolio_url = 'https://' + portfolio_url
            break
    
    # Location (naive regex e.g. "from New Delhi, IN" or "Based out of Hyderabad, IN")
    city = None
    country_code = None
    location_match = re.search(r'(?:from|based\s+(?:out\s+of|in))\s+([^,\.]+),\s*([A-Z]{2})', content, re.IGNORECASE)
    if location_match:
        city = location_match.group(1).strip()
        country_code = location_match.group(2).strip()

    return {
        "_source_type": "txt",
        "_source_file": str(file_path),
        "name": name,
        "email": email,
        "phone": phone,
        "years_experience": years_experience,
        "skills": skills if skills else None,
        "linkedin_url": linkedin_url,
        "github_url": github_url,
        "portfolio_url": portfolio_url,
        "city": city,
        "country_code": country_code
    }

def extract_from_ats_json(file_path: str) -> List[Dict[str, Any]]:
    """Extract candidate records from ATS JSON."""
    ATS_FIELD_MAPPING = {
        "full_name": "name",
        "contact_email": "email",
        "contact_phone": "phone",
        "employer": "current_company",
        "job_title": "title",
        "expertise": "skills",
        "start_date": "start_date",
        "end_date": "end_date",
        "summary": "summary",
        "city": "city",
        "country_code": "country_code",
        "linkedin_url": "linkedin_url",
        "github_url": "github_url",
        "profile_headline": "headline",
        "education_history": "education"
    }
    
    records = []
    import json
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            data = json.load(f)
            
        if isinstance(data, dict):
            data = [data]
            
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
                
            mapped_item = {}
            for ats_key, canonical_key in ATS_FIELD_MAPPING.items():
                if ats_key in item:
                    mapped_item[canonical_key] = item[ats_key]
                    
            name = mapped_item.get("name")
            if not name or not isinstance(name, str) or not name.strip():
                print(f"Warning: Missing or invalid 'name' (full_name) field in ATS JSON {file_path} item {i+1}. Skipping.")
                continue
            mapped_item["name"] = name.strip()
                
            record = {
                "_source_type": "ats_json",
                "_source_file": str(file_path),
                "name": mapped_item.get("name"),
                "email": mapped_item.get("email"),
                "phone": mapped_item.get("phone"),
                "current_company": mapped_item.get("current_company"),
                "title": mapped_item.get("title"),
                "skills": mapped_item.get("skills"),
                "start_date": mapped_item.get("start_date"),
                "end_date": mapped_item.get("end_date"),
                "summary": mapped_item.get("summary"),
                "city": mapped_item.get("city"),
                "country_code": mapped_item.get("country_code"),
                "linkedin_url": mapped_item.get("linkedin_url"),
                "github_url": mapped_item.get("github_url"),
                "headline": mapped_item.get("headline"),
                "education": mapped_item.get("education")
            }
            records.append(record)
    except Exception as e:
        print(f"Error reading ATS JSON {file_path}: {e}")
    return records

def parse_linkedin_profile(item: Dict[str, Any], source_id: str) -> Optional[Dict[str, Any]]:
    """Helper to parse a single LinkedIn profile dict into our canonical schema."""
    if not isinstance(item, dict):
        return None
        
    # Name: concat firstName + lastName
    first = item.get("firstName", "")
    last = item.get("lastName", "")
    name = f"{first} {last}".strip() if (first or last) else None
    
    if not name:
        print(f"Warning: Missing required name in LinkedIn profile {source_id}. Skipping.")
        return None
        
    # Email
    email = item.get("emailAddress")
    
    # Phone: LinkedIn exports phone as a list, take the first
    phones = item.get("phoneNumbers", [])
    phone = phones[0] if phones else None
    
    # Experience: extract from first position
    positions = item.get("positions", [])
    current_company = None
    title = None
    start_date = None
    end_date = None
    summary = None
    if positions and isinstance(positions[0], dict):
        pos = positions[0]
        current_company = pos.get("companyName")
        title = pos.get("title")
        summary = pos.get("description")
        
        # Dates: LinkedIn uses {month: 1, year: 2020} format -> "2020-01"
        sd = pos.get("startDate")
        if isinstance(sd, dict) and "year" in sd:
            month = str(sd.get("month", 1)).zfill(2)
            start_date = f"{sd['year']}-{month}"
        ed = pos.get("endDate")
        if isinstance(ed, dict) and "year" in ed:
            month = str(ed.get("month", 1)).zfill(2)
            end_date = f"{ed['year']}-{month}"
            
    # Education: remap from LinkedIn schema to our canonical schema
    educations = item.get("educations", [])
    education = []
    for edu in educations:
        if isinstance(edu, dict):
            ed_entry = {
                "school": edu.get("schoolName"),
                "degree_level": edu.get("degreeName"),
                "major": edu.get("fieldOfStudy"),
                "grad_year": None
            }
            ed_date = edu.get("endDate")
            if isinstance(ed_date, dict) and "year" in ed_date:
                ed_entry["grad_year"] = ed_date["year"]
            education.append(ed_entry)
            
    # Skills
    skills = item.get("skills")
    
    # Headline
    headline = item.get("headline")
    
    # Location: "Bengaluru, Karnataka, India" -> city=Bengaluru, country=IN
    city = None
    country_code = None
    loc_str = item.get("locationName", "")
    if loc_str:
        parts = [p.strip() for p in loc_str.split(",")]
        if parts:
            city = parts[0]
        # Map common country names to codes
        if "India" in loc_str:
            country_code = "IN"
            
    # Links
    linkedin_url = item.get("profileUrl")
    
    return {
        "_source_type": "linkedin_json",
        "_source_file": source_id,
        "name": name,
        "email": email,
        "phone": str(phone) if phone else None,
        "current_company": current_company,
        "title": title,
        "skills": skills,
        "start_date": start_date,
        "end_date": end_date,
        "summary": summary,
        "city": city,
        "country_code": country_code,
        "linkedin_url": linkedin_url,
        "headline": headline,
        "education": education if education else None
    }

def extract_from_linkedin_json(file_path: str) -> List[Dict[str, Any]]:
    """Extract candidate records from a LinkedIn JSON export.
    
    LinkedIn exports use a different schema than ATS JSON.
    """
    records = []
    import json
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            data = json.load(f)
            
        if isinstance(data, dict):
            data = [data]
            
        for i, item in enumerate(data):
            parsed = parse_linkedin_profile(item, str(file_path))
            if parsed:
                records.append(parsed)
    except Exception as e:
        print(f"Error reading LinkedIn JSON {file_path}: {e}")
    return records

def extract_from_github_json(file_path: str) -> List[Dict[str, Any]]:
    """Extract candidate records from a GitHub API JSON response."""
    records = []
    import json
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            data = json.load(f)
            
        if isinstance(data, dict):
            data = [data]
            
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
                
            name = item.get("name") or item.get("login")
            if not name or not isinstance(name, str):
                print(f"Warning: Missing required 'name' in GitHub JSON {file_path} item {i+1}. Skipping.")
                continue
                
            company = item.get("company")
            if company and isinstance(company, str) and company.startswith("@"):
                company = company[1:] # Remove @ from GitHub company mentions
                
            city = None
            country_code = None
            loc = item.get("location")
            if loc and isinstance(loc, str):
                parts = [p.strip() for p in loc.split(",")]
                city = parts[0]
                if "India" in loc:
                    country_code = "IN"
                    
            record = {
                "_source_type": "github_json",
                "_source_file": str(file_path),
                "name": name.strip(),
                "email": item.get("email"),
                "current_company": company,
                "headline": item.get("bio"),
                "city": city,
                "country_code": country_code,
                "github_url": item.get("html_url"),
                "portfolio_url": item.get("blog")
            }
            records.append(record)
    except Exception as e:
        print(f"Error reading GitHub JSON {file_path}: {e}")
    return records
