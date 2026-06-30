"""
Stage 5: Confidence
Compute per-field confidence based on rules.
"""
from typing import List, Dict, Any

def compute_confidence(canonical_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    STRUCTURED_PRIORITY = ["csv", "ats_json"]
    
    for record in canonical_records:
        proposed = record.pop("_raw_fields", {})
        confidences = []
        field_confidences = {}
        
        def calculate_field_conf(sources_data: dict, is_list_compare=False):
            if not sources_data:
                return None
                
            n = len(sources_data)
            if n == 1:
                source = list(sources_data.keys())[0]
                if source in STRUCTURED_PRIORITY:
                    return 0.7
                else:
                    return 0.5
            
            first_val = list(sources_data.values())[0]["value"]
            agree = True
            for data in sources_data.values():
                if is_list_compare:
                    if data["value"] != first_val:
                        agree = False
                        break
                else:
                    if str(data["value"]).lower() != str(first_val).lower():
                        agree = False
                        break
                        
            if agree:
                return min(0.95 + 0.02 * (n - 2), 0.99)
            else:
                return 0.4
                
        def process_field_conf(field_key: str, conf_key: str, is_list_compare=False):
            sources_data = proposed.get(field_key, {})
            c = calculate_field_conf(sources_data, is_list_compare)
            if c is not None:
                field_confidences[conf_key] = c
                confidences.append(c)
                
        process_field_conf("name", "full_name")
        process_field_conf("email", "emails")
        process_field_conf("phone", "phones")
        
        if record.get("skills"):
            skill_confidences = []
            for skill in record["skills"]:
                skill_name_lower = skill["name"].lower()
                sources_for_skill = []
                for s_type, s_data in proposed.get("skills", {}).items():
                    source_skills = [sk.lower() for sk in s_data["value"]]
                    if skill_name_lower in source_skills:
                        sources_for_skill.append(s_type)
                        
                n = len(sources_for_skill)
                if n == 1:
                    c = 0.7 if sources_for_skill[0] in STRUCTURED_PRIORITY else 0.5
                elif n > 1:
                    c = min(0.95 + 0.02 * (n - 2), 0.99)
                else:
                    c = 0.5
                    
                skill["confidence"] = c
                skill_confidences.append(c)
                
            if skill_confidences:
                avg_skills_conf = sum(skill_confidences) / len(skill_confidences)
                field_confidences["skills"] = avg_skills_conf
                confidences.append(avg_skills_conf)
            
        exp_company = proposed.get("current_company", {})
        exp_title = proposed.get("title", {})
        exp_sources = set(exp_company.keys()).union(set(exp_title.keys()))
        if exp_sources:
            agree = True
            n = len(exp_sources)
            if n > 1:
                first_c = exp_company[list(exp_company.keys())[0]]["value"] if exp_company else None
                first_t = exp_title[list(exp_title.keys())[0]]["value"] if exp_title else None
                for src in exp_sources:
                    c_val = exp_company.get(src, {}).get("value")
                    t_val = exp_title.get(src, {}).get("value")
                    if c_val != first_c or t_val != first_t:
                        agree = False
                        break
            
            if n == 1:
                src = list(exp_sources)[0]
                c_exp = 0.7 if src in STRUCTURED_PRIORITY else 0.5
            else:
                c_exp = min(0.95 + 0.02 * (n - 2), 0.99) if agree else 0.4
                
            field_confidences["experience"] = c_exp
            confidences.append(c_exp)
            
        if confidences:
            record["overall_confidence"] = round(sum(confidences) / len(confidences), 4)
        else:
            record["overall_confidence"] = None
            
        record["_confidences"] = field_confidences
        
    return canonical_records
