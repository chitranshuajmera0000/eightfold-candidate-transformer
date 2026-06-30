# Multi-Source Candidate Data Transformer
**Technical Design – Eightfold Engineering Intern Assignment**

## Pipeline Overview
The pipeline follows a highly modular, seven-stage sequential architecture. Each stage is an isolated function to ensure the system remains deterministic and explainable:

**Detect → Extract → Normalize → Merge → Confidence → Project → Validate**

* **Detect**: Identifies source type by file extension or structure (CSV, ATS JSON, LinkedIn JSON, GitHub JSON, Free-text Notes).
* **Extract**: Parses raw fields into an intermediate dictionary. Uses direct column mapping for CSV, schema mapping for JSON APIs, and robust regex extraction (incorporating look-aheads and exclusion patterns) for `.txt` files.
* **Normalize**: Standardizes formats independent of source. Phones format to `E.164`, dates to `YYYY-MM`, and skill names collapse into a canonical vocabulary via lookup dict.
* **Merge**: Matches records across sources by a normalized `full_name` (case-insensitive, whitespace-trimmed) acting as the primary join key.
* **Confidence**: Scores each field using a fixed, deterministic rule engine, then averages populated field scores into an `overall_confidence`.
* **Project**: Reshapes the internal canonical record into the requested custom output via a generic, configuration-driven function.
* **Validate**: Strictly type-checks and regex-validates the projected output against the requested schema before emitting.

## Canonical Schema & Normalization
The internal canonical record separates identity, contact, and professional-history cleanly: `(candidate_id, full_name, emails[], phones[], location, links, headline, years_experience, skills[], experience[], education[], provenance[], overall_confidence)`.
* **Phones**: Normalized strictly to `E.164`. As this pipeline is tailored for Indian candidate datasets, ambiguous 10-digit phone numbers default to the `+91` country code.
* **Location**: Standardized into a strictly-typed `{city, region, country}` object, where `country` explicitly enforces ISO-3166 alpha-2 abbreviations (e.g. `IN` for India) rather than full strings.
* **Dates**: Normalized universally to the `YYYY-MM` format.
* **Skills Schema**: Normalized via a canonical alias dictionary (e.g. "ML" → "Machine Learning"). Beyond renaming, the schema for skills is highly structured: `[{name, confidence, sources[]}]`. Rather than treating skills as a flat array of strings, each individual skill object actively tracks all source file paths that corroborated it, which directly drives its isolated confidence score.
* **Links**: Extracted rigorously even from unstructured text (e.g. portfolio URLs lacking `https://` prefixes are safely caught and rebuilt).

## Merge & Confidence Policy
**Match Key**: Normalized `full_name`.
**Conflict Rule**: When sources disagree, structured data (e.g. ATS JSON or CSV) wins over values inferred from unstructured prose. Regardless of the winner, **both** values are retained in the `provenance` array with their selection method marked, ensuring human reviewers can audit the decision.

**Confidence Formula (per field & per individual skill):**
* Single structured source → 0.70
* Single unstructured source (regex) → 0.50
* Two sources corroborating the exact value (or the exact skill) → 0.95
* Conflicting sources (for scalar fields) → 0.40 (provenance retains the trail)
* Missing from all sources → field is `null`, excluded from average

For arrays like `skills`, every single skill computes its own confidence based on the number of `sources[]` that detected it. The pipeline then averages those individual skill confidences to produce a single `skills_confidence` metric. 

Finally, the `overall_confidence` is the mean of all populated field scores. This explicitly rewards cross-source agreement while penalizing extraction uncertainty, fulfilling the principle that "wrong-but-confident is worse than honestly-empty."

## Runtime Config / Projection Layer
The canonical record and output schema are strictly separated: `project(record, config) -> output`.
The config controls:
1. Field subset selection and renaming via a `from` path (e.g. mapping `"primary_email"` from `"emails[0]"`).
2. Per-field normalization overrides (e.g. `"normalize": "E164"`).
3. Toggling of confidence/provenance inclusion.
4. Missing-value behavior (`null`, `omit`, `error`).
New output shapes require zero code changes—only a new config schema.

## Edge Cases Handled (and Scope Cuts)
* **Missing/Garbage Source**: Pipeline logs a warning and gracefully degrades to whatever sources are available; it never crashes on an absent file.
* **Malformed CSV Row / JSON Object**: Skipped individually with a logged error; does not abort the batch.
* **Un-prefixed URLs in Text**: Portfolio links in text notes lacking `http://` or `www.` are successfully extracted using negative-lookbehind regex to avoid confusing them with email domains.
* **Out of scope (Time-boxed)**: Fuzzy name matching (exact match only); multi-language extraction.
