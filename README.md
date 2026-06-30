# Multi-Source Candidate Data Transformer

A robust, deterministic ETL pipeline that transforms messy, unstructured, and conflicting candidate data from multiple sources into a single, clean, highly-configurable canonical JSON profile.

## Features & Supported Sources
This pipeline far exceeds the minimum assignment requirements by fully integrating **five** distinct source types:
* **Structured:** Recruiter CSV Exports, ATS JSON API dumps
* **Unstructured:** LinkedIn JSON API dumps, GitHub JSON API dumps, Unstructured Recruiter Notes (`.txt`)

## Setup & Running the Project

### 1. Requirements
* Python 3.9+
* No external heavy dependencies. The backend relies solely on the standard library.

## Key Deliverables
* **[Technical Design Document (PDF)](docs/Chitranshu_Ajmera_ajmerachitranshu951@gmail.com_Eightfold.pdf)**: The 1-page architecture design, schema mappings, and confidence formula explanation.
* **[Final JSON Output](final_output.json)**: The actual canonical JSON output successfully produced by running the pipeline on all 5 provided sample sources.
* **[Unit Tests & Edge Cases](test_pipeline.py)**: The automated test suite validating the 5 designed edge cases (including a "Gold Profile" end-to-end trace).

### 2. Running the CLI
For Windows users, simply double-click or run the included batch script to execute the pipeline with all sample data instantly:
```cmd
run.bat
```

*(Alternatively, you can run the full python command manually):*
```bash
python main.py \
    --csv sample_data/recruiters.csv \
    --ats-json sample_data/ats_export.json \
    --linkedin-json sample_data/linkedin_export.json \
    --github-json sample_data/github_export.json \
    --notes sample_data/notes \
    --out final_output.json
```

### 3. Running the Web UI (Bonus)
A minimal, highly-polished web dashboard is provided to visually test and inspect the data merges.
1. Run `python app.py`
2. Open `http://localhost:5000` in your browser.
3. Drag and drop the files from `sample_data/` into the respective slots.
4. Click **Run ETL Pipeline** to view the candidate cards and dynamically generated JSON.

### 4. Running the Tests
A suite of unit tests, including a full end-to-end "Gold Profile" trace, is included:
```bash
python -m unittest test_pipeline
```

## Architecture & Design Decisions
* **Configurable Projection Layer:** The core `project.py` engine accepts a runtime config to dynamically map fields, enforce missing-value policies (`null`, `omit`, `error`), and toggle confidence/provenance.
* **Deterministic Confidence:** Conflict resolution calculates confidence deterministically. A field verified by multiple structured sources scores near `1.0`, while conflicting sources penalize the score.
* **Scope Definition (Assumptions):** 
  * Because the target dataset and scope is tailored for Indian hiring data, ambiguous 10-digit phone numbers default to the `+91` E.164 country code rather than US `+1`.
  * Name-matching is exact (case-insensitive, trimmed). Fuzzy matching was descoped.
