import argparse
import json
import sys
from pathlib import Path

# Add the current directory to sys.path so 'etl' can be imported
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from etl.detect import detect_source_type
from etl.extract import extract_from_csv, extract_from_txt, extract_from_ats_json, extract_from_linkedin_json, extract_from_github_json, parse_linkedin_profile
from etl.normalize import normalize_record
from etl.merge import merge_records
from etl.confidence import compute_confidence
from etl.project import project
from etl.validate import validate_output

def main():
    parser = argparse.ArgumentParser(description="Multi-Source Candidate Data Transformer")
    parser.add_argument("--csv", help="Path to recruiter CSV export", required=False)
    parser.add_argument("--notes", help="Path to recruiter notes directory", required=False)
    parser.add_argument("--ats-json", help="Path to ATS JSON file", required=False)
    parser.add_argument("--linkedin-json", help="Path to LinkedIn JSON export", required=False)
    parser.add_argument("--github-json", help="Path to GitHub API JSON export", required=False)
    parser.add_argument("--config", help="Path to projection config JSON", required=False)
    parser.add_argument("--out", help="Path to output JSON file", required=True)
    args = parser.parse_args()
    
    raw_records = []
    
    if args.csv:
        csv_path = Path(args.csv)
        if csv_path.exists():
            if detect_source_type(str(csv_path)) == "csv":
                records = extract_from_csv(str(csv_path))
                for r in records:
                    raw_records.append(normalize_record(r))
        else:
            print(f"Warning: CSV file not found at {csv_path}. Skipping.")
            
    if args.notes:
        notes_dir = Path(args.notes)
        if notes_dir.exists() and notes_dir.is_dir():
            for txt_file in notes_dir.glob("*.txt"):
                if detect_source_type(str(txt_file)) == "txt":
                    record = extract_from_txt(str(txt_file))
                    if record:
                        raw_records.append(normalize_record(record))
        else:
            print(f"Warning: Notes directory not found or invalid at {notes_dir}. Skipping.")

    if args.ats_json:
        ats_path = Path(args.ats_json)
        if ats_path.exists():
            if detect_source_type(str(ats_path)) == "ats_json":
                records = extract_from_ats_json(str(ats_path))
                for r in records:
                    raw_records.append(normalize_record(r))
        else:
            print(f"Warning: ATS JSON file not found at {ats_path}. Skipping.")

    if args.linkedin_json:
        li_path = Path(args.linkedin_json)
        if li_path.exists():
            if detect_source_type(str(li_path)) == "linkedin_json":
                records = extract_from_linkedin_json(str(li_path))
                for r in records:
                    raw_records.append(normalize_record(r))
        else:
            print(f"Warning: LinkedIn JSON file not found at {li_path}. Skipping.")
            
    if args.github_json:
        gh_path = Path(args.github_json)
        if gh_path.exists():
            records = extract_from_github_json(str(gh_path))
            for r in records:
                raw_records.append(normalize_record(r))
        else:
            print(f"Warning: GitHub JSON file not found at {gh_path}. Skipping.")
            
    if not raw_records:
        print("Warning: No records were extracted. Proceeding with empty output.")
            
    # Merge
    merged_records = merge_records(raw_records)
    
    # Confidence
    confident_records = compute_confidence(merged_records)
    
    # Config
    config = {}
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            print(f"Warning: Config file not found at {config_path}. Using default.")
    else:
        # Default config
        config = {
            "include_confidence": True,
            "include_provenance": True
        }
            
    # Project & Validate
    final_output = []
    for record in confident_records:
        try:
            projected = project(record, config)
            
            # Clean up internal tracking fields AFTER projection has read them
            if "_confidences" in record:
                record.pop("_confidences")
            
            validate_output(projected, config)
            final_output.append(projected)
        except Exception as e:
            print(f"Error processing candidate {record.get('full_name')}: {e}")
            
    # Output
    out_json = json.dumps(final_output, indent=2)
    print(out_json)
    
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(out_json)
        
if __name__ == "__main__":
    main()
