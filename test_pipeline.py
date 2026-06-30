import unittest
from etl.merge import merge_records
from etl.confidence import compute_confidence
from etl.project import project
from etl.validate import validate_output, EMAIL_RE, E164_RE
from etl.normalize import normalize_phone
from etl.extract import extract_from_txt, extract_from_ats_json

class TestPipeline(unittest.TestCase):
    
    def test_merge_conflict_csv_wins(self):
        records = [
            {
                "_source_type": "csv",
                "_source_file": "data.csv",
                "name": "Aditi",
                "phone": "+919876543210"
            },
            {
                "_source_type": "txt",
                "_source_file": "notes.txt",
                "name": "Aditi",
                "phone": "+919876500000"
            }
        ]
        
        merged = merge_records(records)
        self.assertEqual(len(merged), 1)
        aditi = merged[0]
        
        # CSV wins
        self.assertEqual(aditi["phones"], ["+919876543210"])
        
        # Verify provenance recorded the conflict
        phone_prov = next((p for p in aditi["provenance"] if p["field"] == "phones"), None)
        self.assertIsNotNone(phone_prov)
        self.assertEqual(phone_prov["method"], "csv_wins")
        
    def test_missing_source_handled_gracefully(self):
        # A candidate only found in TXT
        records = [
            {
                "_source_type": "txt",
                "_source_file": "notes.txt",
                "name": "Rahul",
                "phone": "+919123456789"
            }
        ]
        merged = merge_records(records)
        self.assertEqual(len(merged), 1)
        rahul = merged[0]
        self.assertEqual(rahul["full_name"], "Rahul")
        self.assertEqual(rahul["phones"], ["+919123456789"])
        
    def test_confidence_scores(self):
        records = [
            {
                "_source_type": "csv",
                "_source_file": "data.csv",
                "name": "Aditi",
                "phone": "+919876543210"
            },
            {
                "_source_type": "txt",
                "_source_file": "notes.txt",
                "name": "Aditi",
                "phone": "+919876500000"  # Disagree on phone
            }
        ]
        merged = merge_records(records)
        confident = compute_confidence(merged)
        aditi = confident[0]
        
        # Disagree -> 0.4 for phone
        # Agree -> 0.95 for name
        self.assertEqual(aditi["_confidences"]["full_name"], 0.95)
        self.assertEqual(aditi["_confidences"]["phones"], 0.4)
        
    def test_projection_default_schema_validation(self):
        canonical = {
            "candidate_id": "123",
            "full_name": "Vikram",
            "emails": ["vikram@example.in"],
            "phones": ["+919988776655"],
            "skills": []
        }
        
        config = {
            "include_confidence": False,
            "include_provenance": False
        }
        
        projected = project(canonical, config)
        
        # Should contain full name, valid types
        self.assertEqual(projected["full_name"], "Vikram")
        
        # Validate output
        self.assertTrue(validate_output(projected))

    def test_normalize_phone_rejects_unparseable_instead_of_fabricating(self):
        """Regression test: a 7-digit number like '2345678' has no reliable
        area code and must return None, not a guessed +-prefixed string."""
        self.assertIsNone(normalize_phone("234-5678"))
        # A genuine 10-digit Indian number should still normalize correctly.
        self.assertEqual(normalize_phone("98765 43210"), "+919876543210")
        self.assertIsNone(normalize_phone(""))

    def test_extract_email_excludes_trailing_sentence_punctuation(self):
        """Regression test: 'Contact: karan@patel.in. Python and JS.' must not
        capture the sentence-ending period as part of the email."""
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "w") as f:
                f.write("Karan Patel. Contact: karan@patel.in. Python and JavaScript.")
            record = extract_from_txt(path)
            self.assertEqual(record["email"], "karan@patel.in")
        finally:
            os.remove(path)

    def test_validate_output_catches_malformed_email_and_phone(self):
        """validate_output must reject format-invalid strings even when the
        Python type (str) is technically correct."""
        with self.assertRaises(ValueError):
            validate_output({"primary_email": "karan@patel.in."})
        with self.assertRaises(ValueError):
            validate_output({"primary_phone": "+91234"})
        # Valid values should pass without raising.
        self.assertTrue(validate_output({"primary_email": "karan@patel.in", "primary_phone": "+919898989898"}))

    def test_ats_extraction(self):
        import tempfile, json, os
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump([{
                    "full_name": "Test User",
                    "contact_phone": "9998887776",
                    "expertise": ["Python"]
                }], f)
            records = extract_from_ats_json(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["name"], "Test User")
            self.assertEqual(records[0]["phone"], "9998887776")
        finally:
            os.remove(path)

    def test_ats_malformed_json_does_not_crash(self):
        import tempfile, os
        from etl.detect import detect_source_type
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                f.write("this is not json")
            self.assertIsNone(detect_source_type(path))
            records = extract_from_ats_json(path)
            self.assertEqual(len(records), 0)
        finally:
            os.remove(path)

    def test_ats_json_only_candidate_merge(self):
        records = [
            {
                "_source_type": "ats_json",
                "_source_file": "ats.json",
                "name": "Sneha",
                "phone": "+919998887776",
                "skills": ["DevOps"]
            }
        ]
        merged = merge_records(records)
        self.assertEqual(len(merged), 1)
        sneha = merged[0]
        self.assertEqual(sneha["full_name"], "Sneha")
        self.assertEqual(sneha["phones"], ["+919998887776"])
        self.assertEqual(len(sneha["skills"]), 1)

    def test_three_source_agree_confidence(self):
        records = [
            {"_source_type": "csv", "_source_file": "csv", "name": "Aditi", "phone": "+919876543210"},
            {"_source_type": "txt", "_source_file": "txt", "name": "Aditi", "phone": "+919876543210"},
            {"_source_type": "ats_json", "_source_file": "ats", "name": "Aditi", "phone": "+919876543210"}
        ]
        merged = merge_records(records)
        confident = compute_confidence(merged)
        aditi = confident[0]
        self.assertEqual(aditi["_confidences"]["phones"], 0.97)
        phone_prov = next((p for p in aditi["provenance"] if p["field"] == "phones"), None)
        self.assertIn("csv", phone_prov["source"])
        self.assertIn("txt", phone_prov["source"])
        self.assertIn("ats", phone_prov["source"])
        
    def test_three_source_disagree_priority(self):
        records = [
            {"_source_type": "csv", "_source_file": "csv", "name": "Aditi", "phone": "+919876543210"},
            {"_source_type": "ats_json", "_source_file": "ats", "name": "Aditi", "phone": "+910000000000"}
        ]
        merged = merge_records(records)
        confident = compute_confidence(merged)
        aditi = confident[0]
        self.assertEqual(aditi["phones"], ["+919876543210"])
        self.assertEqual(aditi["_confidences"]["phones"], 0.4)
        phone_prov = next((p for p in aditi["provenance"] if p["field"] == "phones"), None)
        self.assertEqual(phone_prov["method"], "csv_wins")

    # --- New tests for Indian phone extraction and years_experience ---
    
    def test_indian_phone_5_5_grouping(self):
        """Indian phone numbers with 5-5 digit grouping (e.g., 98989 89898)
        must be extracted correctly from free text."""
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "w") as f:
                f.write("Priya Kapoor. Contact: +91 98989 89898, priya@test.in.")
            record = extract_from_txt(path)
            self.assertIsNotNone(record["phone"])
            self.assertIn("98989", record["phone"])
        finally:
            os.remove(path)
    
    def test_years_experience_extraction(self):
        """Extract years of experience from recruiter notes."""
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "w") as f:
                f.write("Ravi Kumar has 8 years of experience. Python expert.")
            record = extract_from_txt(path)
            self.assertEqual(record["years_experience"], 8)
        finally:
            os.remove(path)

    def test_years_experience_not_fabricated_when_absent(self):
        """years_experience must be None when not mentioned in notes."""
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "w") as f:
                f.write("Amit Joshi is a developer. Knows JavaScript.")
            record = extract_from_txt(path)
            self.assertIsNone(record["years_experience"])
        finally:
            os.remove(path)

    def test_config_projection_with_field_mapping(self):
        """Test the projection layer with custom field mapping, on_missing,
        and include_confidence to verify the _confidences pop-ordering fix."""
        canonical = {
            "candidate_id": "abc123",
            "full_name": "Priya Shah",
            "emails": ["priya@example.in"],
            "phones": ["+919876543210"],
            "skills": [
                {"name": "Python", "confidence": 0.7, "sources": ["ats.json"]},
                {"name": "ML", "confidence": 0.5, "sources": ["notes.txt"]}
            ],
            "years_experience": 3,
            "overall_confidence": 0.65,
            "_confidences": {
                "full_name": 0.7,
                "emails": 0.7,
                "phones": 0.7,
                "skills": 0.6,
                "years_experience": 0.5
            }
        }
        config = {
            "fields": [
                {"path": "name", "from": "full_name"},
                {"path": "primary_email", "from": "emails[0]"},
                {"path": "phone", "from": "phones[0]", "normalize": "E164"},
                {"path": "skills", "from": "skills[].name", "normalize": "canonical"}
            ],
            "include_confidence": True,
            "include_provenance": False,
            "on_missing": "omit"
        }
        projected = project(canonical, config)
        
        # Field mapping works
        self.assertEqual(projected["name"], "Priya Shah")
        self.assertEqual(projected["primary_email"], "priya@example.in")
        
        # Per-field confidence injected (verifies _confidences pop-ordering fix)
        self.assertEqual(projected["name_confidence"], 0.7)
        self.assertEqual(projected["primary_email_confidence"], 0.7)
        
        # Skills normalized to canonical names list
        self.assertIsInstance(projected["skills"], list)
        self.assertIn("Python", projected["skills"])
        
        # Overall confidence present
        self.assertEqual(projected["overall_confidence"], 0.65)

    def test_gold_profile_aditi_sharma(self):
        """Gold-profile comparison: trace Aditi Sharma through the full pipeline
        with all 3 sources and verify the merged record field by field."""
        from etl.normalize import normalize_record
        
        csv_record = normalize_record({
            "_source_type": "csv",
            "_source_file": "recruiters.csv",
            "name": "Aditi Sharma",
            "email": "aditi@example.in",
            "phone": "9876543210",
            "current_company": "Infosys",
            "title": "Software Engineer"
        })
        
        txt_record = normalize_record({
            "_source_type": "txt",
            "_source_file": "notes/aditi_sharma.txt",
            "name": "Aditi Sharma",
            "email": "aditi@example.in",
            "phone": "+91 98765 43210",
            "skills": ["Machine Learning", "JavaScript"]
        })
        
        ats_record = normalize_record({
            "_source_type": "ats_json",
            "_source_file": "ats_export.json",
            "name": "Aditi Sharma",
            "email": "aditi.sharma@example.in",
            "phone": "9876543210",
            "current_company": "Infosys",
            "title": "Senior Software Engineer",
            "skills": ["Machine Learning", "Python"]
        })
        
        merged = merge_records([csv_record, txt_record, ats_record])
        confident = compute_confidence(merged)
        
        aditi = confident[0]
        
        # Identity
        self.assertEqual(aditi["full_name"], "Aditi Sharma")
        self.assertIsNotNone(aditi["candidate_id"])
        
        # CSV wins on email (conflict: csv has aditi@example.in, ats has aditi.sharma@example.in)
        self.assertEqual(aditi["emails"], ["aditi@example.in"])
        
        # All 3 sources agree on phone after normalization
        self.assertEqual(aditi["phones"], ["+919876543210"])
        
        # Skills merged from txt and ats_json (3 unique skills)
        skill_names = [s["name"] for s in aditi["skills"]]
        self.assertIn("Machine Learning", skill_names)
        self.assertIn("JavaScript", skill_names)
        self.assertIn("Python", skill_names)
        
        # Machine Learning in 2 sources -> 0.95 confidence
        ml_skill = next(s for s in aditi["skills"] if s["name"] == "Machine Learning")
        self.assertEqual(ml_skill["confidence"], 0.95)
        
        # JavaScript in 1 source (txt) -> 0.5
        js_skill = next(s for s in aditi["skills"] if s["name"] == "JavaScript")
        self.assertEqual(js_skill["confidence"], 0.5)
        
        # Python in 1 source (ats_json, structured) -> 0.7
        py_skill = next(s for s in aditi["skills"] if s["name"] == "Python")
        self.assertEqual(py_skill["confidence"], 0.7)
        
        # Experience from CSV (structured priority)
        self.assertEqual(len(aditi["experience"]), 1)
        self.assertEqual(aditi["experience"][0]["company"], "Infosys")
        
        # Provenance tracks all sources
        name_prov = next(p for p in aditi["provenance"] if p["field"] == "full_name")
        self.assertEqual(name_prov["method"], "agreed")
        
        email_prov = next(p for p in aditi["provenance"] if p["field"] == "emails")
        self.assertEqual(email_prov["method"], "csv_wins")
        
        # Overall confidence is a reasonable number
        self.assertIsNotNone(aditi["overall_confidence"])
        self.assertGreater(aditi["overall_confidence"], 0.0)
        self.assertLessEqual(aditi["overall_confidence"], 1.0)

    # --- LinkedIn JSON tests ---

    def test_linkedin_extraction(self):
        """Extract from LinkedIn JSON with firstName/lastName, positions, educations."""
        import tempfile, json, os
        from etl.extract import extract_from_linkedin_json
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump([{
                    "firstName": "Priya",
                    "lastName": "Kapoor",
                    "emailAddress": "priya@test.in",
                    "phoneNumbers": ["+919876500000"],
                    "positions": [{
                        "companyName": "Zomato",
                        "title": "Backend Engineer",
                        "startDate": {"month": 3, "year": 2021},
                        "endDate": {"month": 12, "year": 2023}
                    }],
                    "educations": [{
                        "schoolName": "BITS Pilani",
                        "degreeName": "B.E",
                        "fieldOfStudy": "CS",
                        "endDate": {"year": 2020}
                    }],
                    "skills": ["Java", "Python"],
                    "headline": "Backend Engineer at Zomato",
                    "locationName": "Hyderabad, Telangana, India"
                }], f)
            records = extract_from_linkedin_json(path)
            self.assertEqual(len(records), 1)
            r = records[0]
            self.assertEqual(r["_source_type"], "linkedin_json")
            self.assertEqual(r["name"], "Priya Kapoor")
            self.assertEqual(r["email"], "priya@test.in")
            self.assertEqual(r["phone"], "+919876500000")
            self.assertEqual(r["current_company"], "Zomato")
            self.assertEqual(r["title"], "Backend Engineer")
            self.assertEqual(r["start_date"], "2021-03")
            self.assertEqual(r["end_date"], "2023-12")
            self.assertEqual(r["headline"], "Backend Engineer at Zomato")
            self.assertEqual(r["city"], "Hyderabad")
            self.assertEqual(r["country_code"], "IN")
            self.assertEqual(len(r["education"]), 1)
            self.assertEqual(r["education"][0]["school"], "BITS Pilani")
            self.assertEqual(r["education"][0]["grad_year"], 2020)
        finally:
            os.remove(path)

    def test_linkedin_detection(self):
        """detect_source_type should return 'linkedin_json' for LinkedIn exports."""
        import tempfile, json, os
        from etl.detect import detect_source_type
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump([{"firstName": "Test", "lastName": "User"}], f)
            self.assertEqual(detect_source_type(path), "linkedin_json")
        finally:
            os.remove(path)

    def test_four_source_merge(self):
        """A candidate present in all 4 sources should merge correctly with
        all sources tracked in provenance."""
        records = [
            {"_source_type": "csv", "_source_file": "csv", "name": "Aditi", "phone": "+919876543210"},
            {"_source_type": "txt", "_source_file": "txt", "name": "Aditi", "phone": "+919876543210"},
            {"_source_type": "ats_json", "_source_file": "ats", "name": "Aditi", "phone": "+919876543210"},
            {"_source_type": "linkedin_json", "_source_file": "li", "name": "Aditi", "phone": "+919876543210"}
        ]
        merged = merge_records(records)
        confident = compute_confidence(merged)
        aditi = confident[0]
        
        # All 4 agree -> min(0.95 + 0.02*(4-2), 0.99) = min(0.99, 0.99) = 0.99
        self.assertEqual(aditi["_confidences"]["phones"], 0.99)
        
        # Provenance should mention all 4 files
        phone_prov = next(p for p in aditi["provenance"] if p["field"] == "phones")
        self.assertIn("csv", phone_prov["source"])
        self.assertIn("txt", phone_prov["source"])
        self.assertIn("ats", phone_prov["source"])
        self.assertIn("li", phone_prov["source"])
        self.assertEqual(phone_prov["method"], "agreed")

    def test_github_extraction(self):
        """Extract from GitHub JSON with login, bio, html_url."""
        import tempfile, json, os
        from etl.extract import extract_from_github_json
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump([{
                    "login": "octocat",
                    "name": "Monalisa Octocat",
                    "company": "@GitHub",
                    "bio": "Building the future of software",
                    "location": "San Francisco, CA",
                    "html_url": "https://github.com/octocat"
                }], f)
            records = extract_from_github_json(path)
            self.assertEqual(len(records), 1)
            r = records[0]
            self.assertEqual(r["_source_type"], "github_json")
            self.assertEqual(r["name"], "Monalisa Octocat")
            self.assertEqual(r["current_company"], "GitHub")
            self.assertEqual(r["headline"], "Building the future of software")
            self.assertEqual(r["city"], "San Francisco")
            self.assertEqual(r["github_url"], "https://github.com/octocat")
        finally:
            os.remove(path)

if __name__ == '__main__':
    unittest.main()
