"""
Stage 4: Merge
Match records across sources by name. If both sources have a value and they disagree,
structured sources win, and all values are recorded in provenance.
"""
import hashlib
from typing import List, Dict, Any

STRUCTURED_PRIORITY = ["csv", "ats_json", "linkedin_json", "github_json"]
UNSTRUCTURED_SOURCES = ["txt"]

def generate_id(name: str) -> str:
    """Generate a consistent ID based on the normalized name."""
    norm_name = name.lower().strip()
    return hashlib.md5(norm_name.encode('utf-8')).hexdigest()[:10]

def merge_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge records by name (case-insensitive, whitespace-trimmed).
    """
    grouped = {}
    for r in records:
        name = r.get("name")
        if not name:
            continue
        norm_name = name.strip().lower()
        if norm_name not in grouped:
            grouped[norm_name] = []
        grouped[norm_name].append(r)
        
    merged_results = []
    
    for norm_name, c_records in grouped.items():
        canonical = {
            "candidate_id": generate_id(norm_name),
            "full_name": None,
            "emails": [],
            "phones": [],
            "location": None,
            "links": None,
            "headline": None,
            "years_experience": None,
            "skills": [],
            "experience": [],
            "education": [],
            "provenance": [],
            "_raw_fields": {} # Tracker for confidence calculation
        }
        
        proposed = {
            "name": {},
            "email": {},
            "phone": {},
            "years_experience": {},
            "skills": {},
            "current_company": {},
            "title": {},
            "city": {},
            "country_code": {},
            "linkedin_url": {},
            "github_url": {},
            "portfolio_url": {},
            "headline": {},
            "education": {},
            "start_date": {},
            "end_date": {},
            "summary": {}
        }
        
        for r in c_records:
            source = r["_source_type"]
            for field in proposed.keys():
                val = r.get(field)
                if val is not None and val != [] and val != "":
                    proposed[field][source] = {
                        "value": val,
                        "file": r["_source_file"]
                    }
                    
        def resolve_scalar(field_key: str, out_key: str, is_list_wrap=False):
            prop = proposed[field_key]
            if not prop:
                return
                
            winner_source = None
            for s in STRUCTURED_PRIORITY:
                if s in prop:
                    winner_source = s
                    break
            if not winner_source:
                winner_source = list(prop.keys())[0]
                
            winning_val = prop[winner_source]["value"]
            all_files = [data["file"].replace("\\", "/") for data in prop.values()]
            source_str = " & ".join(all_files)
            
            if len(prop) == 1:
                if winner_source == "csv":
                    method = "csv_column"
                elif winner_source == "txt":
                    method = "regex_extraction"
                else:
                    method = f"{winner_source}_extraction"
            else:
                all_agree = True
                for data in prop.values():
                    if str(winning_val).lower() != str(data["value"]).lower():
                        all_agree = False
                        break
                if all_agree:
                    method = "agreed"
                else:
                    method = f"{winner_source}_wins"
                    
            if is_list_wrap:
                canonical[out_key] = [winning_val]
            else:
                canonical[out_key] = winning_val
                
            canonical["provenance"].append({
                "field": out_key,
                "source": source_str,
                "method": method
            })

        resolve_scalar("name", "full_name")
        resolve_scalar("email", "emails", is_list_wrap=True)
        resolve_scalar("phone", "phones", is_list_wrap=True)
        resolve_scalar("years_experience", "years_experience")
        resolve_scalar("headline", "headline")
        
        # Location
        city_prop = proposed["city"]
        country_prop = proposed["country_code"]
        if city_prop or country_prop:
            c_win = next((s for s in STRUCTURED_PRIORITY if s in city_prop), None) or next(iter(city_prop), None)
            co_win = next((s for s in STRUCTURED_PRIORITY if s in country_prop), None) or next(iter(country_prop), None)
            
            canonical["location"] = {
                "city": city_prop[c_win]["value"] if c_win else None,
                "region": None,
                "country": country_prop[co_win]["value"] if co_win else None
            }
            files = set()
            if c_win: files.add(city_prop[c_win]["file"].replace("\\", "/"))
            if co_win: files.add(country_prop[co_win]["file"].replace("\\", "/"))
            canonical["provenance"].append({
                "field": "location",
                "source": " & ".join(list(files)),
                "method": "agreed" if len(files) <= 1 else "mixed"
            })
            
        # Links
        li_prop = proposed["linkedin_url"]
        gh_prop = proposed["github_url"]
        po_prop = proposed["portfolio_url"]
        if li_prop or gh_prop or po_prop:
            li_win = next((s for s in STRUCTURED_PRIORITY if s in li_prop), None) or next(iter(li_prop), None)
            gh_win = next((s for s in STRUCTURED_PRIORITY if s in gh_prop), None) or next(iter(gh_prop), None)
            po_win = next((s for s in STRUCTURED_PRIORITY if s in po_prop), None) or next(iter(po_prop), None)
            
            canonical["links"] = {
                "linkedin": li_prop[li_win]["value"] if li_win else None,
                "github": gh_prop[gh_win]["value"] if gh_win else None,
                "portfolio": po_prop[po_win]["value"] if po_win else None,
                "other": []
            }
            files = set()
            if li_win: files.add(li_prop[li_win]["file"].replace("\\", "/"))
            if gh_win: files.add(gh_prop[gh_win]["file"].replace("\\", "/"))
            if po_win: files.add(po_prop[po_win]["file"].replace("\\", "/"))
            canonical["provenance"].append({
                "field": "links",
                "source": " & ".join(list(files)),
                "method": "agreed" if len(files) <= 1 else "mixed"
            })
            
        # Education
        edu_prop = proposed["education"]
        if edu_prop:
            win = next((s for s in STRUCTURED_PRIORITY if s in edu_prop), None) or next(iter(edu_prop), None)
            canonical["education"] = edu_prop[win]["value"]
            canonical["provenance"].append({
                "field": "education",
                "source": edu_prop[win]["file"].replace("\\", "/"),
                "method": "agreed" if len(edu_prop) == 1 else f"{win}_wins"
            })
        
        prop_skills = proposed["skills"]
        if prop_skills:
            all_skill_files = []
            for source, data in prop_skills.items():
                all_skill_files.append(data["file"].replace("\\", "/"))
                for sk in data["value"]:
                    existing = next((s for s in canonical["skills"] if s["name"].lower() == sk.lower()), None)
                    if existing:
                        if data["file"].replace("\\", "/") not in existing["sources"]:
                            existing["sources"].append(data["file"].replace("\\", "/"))
                    else:
                        canonical["skills"].append({
                            "name": sk,
                            "confidence": None,
                            "sources": [data["file"].replace("\\", "/")]
                        })
            method = "regex_extraction" if (len(prop_skills) == 1 and "txt" in prop_skills) else "combined_extraction"
            canonical["provenance"].append({
                "field": "skills", 
                "source": " & ".join(all_skill_files), 
                "method": method
            })
            
        exp_company = proposed["current_company"]
        exp_title = proposed["title"]
        exp_start = proposed["start_date"]
        exp_end = proposed["end_date"]
        exp_summary = proposed["summary"]
        
        if exp_company or exp_title:
            winner_c = next((s for s in STRUCTURED_PRIORITY if s in exp_company), None) or next(iter(exp_company), None)
            winner_t = next((s for s in STRUCTURED_PRIORITY if s in exp_title), None) or next(iter(exp_title), None)
            winner_s = next((s for s in STRUCTURED_PRIORITY if s in exp_start), None) or next(iter(exp_start), None)
            winner_e = next((s for s in STRUCTURED_PRIORITY if s in exp_end), None) or next(iter(exp_end), None)
            winner_sum = next((s for s in STRUCTURED_PRIORITY if s in exp_summary), None) or next(iter(exp_summary), None)
            
            c_val = exp_company[winner_c]["value"] if winner_c else "Unknown"
            t_val = exp_title[winner_t]["value"] if winner_t else "Unknown"
            s_val = exp_start[winner_s]["value"] if winner_s else None
            e_val = exp_end[winner_e]["value"] if winner_e else None
            sum_val = exp_summary[winner_sum]["value"] if winner_sum else None
            
            canonical["experience"].append({
                "company": c_val,
                "title": t_val,
                "start": s_val,
                "end": e_val,
                "summary": sum_val
            })
            
            files = set()
            if winner_c: files.add(exp_company[winner_c]["file"].replace("\\", "/"))
            if winner_t: files.add(exp_title[winner_t]["file"].replace("\\", "/"))
            if winner_s: files.add(exp_start[winner_s]["file"].replace("\\", "/"))
            if winner_e: files.add(exp_end[winner_e]["file"].replace("\\", "/"))
            if winner_sum: files.add(exp_summary[winner_sum]["file"].replace("\\", "/"))
                
            if winner_c == "csv" or winner_t == "csv":
                method = "csv_column"
            else:
                method = f"{winner_c or winner_t}_extraction"
                
            canonical["provenance"].append({
                "field": "experience", 
                "source": " & ".join(list(files)), 
                "method": method
            })
            
        canonical["_raw_fields"] = proposed
        merged_results.append(canonical)
        
    return merged_results
