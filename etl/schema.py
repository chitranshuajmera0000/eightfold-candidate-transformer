"""
Defines the canonical output schema for the pipeline.
"""
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Location:
    city: Optional[str]
    region: Optional[str]
    country: Optional[str]

@dataclass
class Links:
    linkedin: Optional[str]
    github: Optional[str]
    portfolio: Optional[str]
    other: List[str]

@dataclass
class Skill:
    name: str
    confidence: Optional[float]
    sources: List[str]

@dataclass
class Experience:
    company: str
    title: str
    start: Optional[str]
    end: Optional[str]
    summary: Optional[str]

@dataclass
class Education:
    institution: str
    degree: str
    field: str
    end_year: Optional[int]

@dataclass
class Provenance:
    field: str
    source: str
    method: str

@dataclass
class CanonicalRecord:
    candidate_id: str
    full_name: str
    emails: List[str]
    phones: List[str]
    location: Optional[Location]
    links: Optional[Links]
    headline: Optional[str]
    years_experience: Optional[float]
    skills: List[Skill]
    experience: List[Experience]
    education: List[Education]
    provenance: List[Provenance]
    overall_confidence: Optional[float]
