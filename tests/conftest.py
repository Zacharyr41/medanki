"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock

import pytest


class ExamType(str, Enum):
    MCAT = "mcat"
    USMLE_STEP1 = "usmle_step1"
    USMLE_STEP2 = "usmle_step2"


class ContentType(str, Enum):
    PDF_TEXTBOOK = "pdf_textbook"
    PDF_SLIDES = "pdf_slides"
    PDF_NOTES = "pdf_notes"
    AUDIO_LECTURE = "audio_lecture"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"


class CardType(str, Enum):
    CLOZE = "cloze"
    VIGNETTE = "vignette"
    BASIC_QA = "basic_qa"


class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID_SCHEMA = "invalid_schema"
    INVALID_MEDICAL = "invalid_medical"
    HALLUCINATION_DETECTED = "hallucination_detected"
    DUPLICATE = "duplicate"


@dataclass
class Section:
    title: str
    level: int
    start_char: int
    end_char: int
    page_number: Optional[int] = None


@dataclass
class MedicalEntity:
    text: str
    label: str
    start: int
    end: int
    cui: Optional[str] = None
    confidence: float = 1.0


@dataclass
class Document:
    id: str
    source_path: str
    content_type: ContentType
    raw_text: str
    sections: List[Section] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    extracted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Chunk:
    id: str
    document_id: str
    text: str
    start_char: int
    end_char: int
    token_count: int
    page_number: Optional[int] = None
    section_path: List[str] = field(default_factory=list)
    entities: List[MedicalEntity] = field(default_factory=list)
    embedding: Optional[List[float]] = None


@dataclass
class ClozeCard:
    id: str
    text: str
    extra: str = ""
    source_chunk_id: str = ""
    tags: List[str] = field(default_factory=list)
    difficulty: str = "medium"

    CLOZE_PATTERN = re.compile(r"\{\{c\d+::([^}]+)\}\}")
    MAX_ANSWER_WORDS = 4

    def validate(self) -> tuple[bool, list[str]]:
        issues = []
        deletions = self.CLOZE_PATTERN.findall(self.text)
        if not deletions:
            issues.append("Missing cloze deletion syntax")
        for answer in deletions:
            if len(answer.split()) > self.MAX_ANSWER_WORDS:
                issues.append(f"Answer too long: {answer}")
        return len(issues) == 0, issues


@dataclass
class VignetteCard:
    id: str
    front: str
    answer: str
    explanation: str
    distinguishing_feature: Optional[str] = None
    source_chunk_id: str = ""
    tags: List[str] = field(default_factory=list)


@pytest.fixture
def sample_document() -> Document:
    return Document(
        id="doc_001",
        source_path="/data/lecture_01.pdf",
        content_type=ContentType.PDF_SLIDES,
        raw_text="Sample medical content about cardiovascular system.",
        sections=[
            Section(title="Introduction", level=1, start_char=0, end_char=50)
        ],
        metadata={"page_count": 10}
    )


@pytest.fixture
def sample_chunk() -> Chunk:
    return Chunk(
        id="chunk_001",
        document_id="doc_001",
        text="The cardiac cycle consists of systole and diastole phases.",
        start_char=0,
        end_char=57,
        token_count=12,
        page_number=1,
        section_path=["Cardiovascular", "Physiology"]
    )


@pytest.fixture
def sample_medical_text() -> str:
    return """
    Congestive heart failure (CHF) is a chronic progressive condition
    that affects the pumping power of the heart muscles. The left ventricle
    is unable to pump blood efficiently to meet the body's needs.

    Treatment includes ACE inhibitors such as lisinopril, beta-blockers
    like metoprolol, and diuretics including furosemide.
    """


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    client = AsyncMock()
    client.generate.return_value = "Generated response"
    return client


@pytest.fixture
def sample_long_document() -> Document:
    """A document with 2000+ tokens for chunking tests."""
    long_text = """
# Cardiovascular System Overview

The cardiovascular system is responsible for transporting blood throughout the body.
It consists of the heart, blood vessels, and blood. The heart is a muscular organ that
pumps blood through the circulatory system.

## Heart Anatomy

The heart has four chambers: two atria and two ventricles. The right atrium receives
deoxygenated blood from the body through the superior and inferior vena cava. This blood
then flows into the right ventricle, which pumps it to the lungs for oxygenation.

The left atrium receives oxygenated blood from the lungs through the pulmonary veins.
This blood flows into the left ventricle, which is the strongest chamber and pumps blood
to the entire body through the aorta.

## Cardiac Cycle

The cardiac cycle consists of two main phases: systole and diastole. During systole,
the ventricles contract and pump blood out of the heart. During diastole, the ventricles
relax and fill with blood from the atria.

The cardiac cycle is controlled by the heart's electrical conduction system, which
includes the sinoatrial (SA) node, atrioventricular (AV) node, bundle of His, and
Purkinje fibers. The SA node, located in the right atrium, is the heart's natural
pacemaker and initiates each heartbeat.

## Blood Pressure Regulation

Blood pressure is the force of blood against the walls of arteries. It is measured
in millimeters of mercury (mmHg) and expressed as systolic over diastolic pressure.
Normal blood pressure is typically around 120/80 mmHg.

Blood pressure is regulated by several mechanisms including the renin-angiotensin-
aldosterone system (RAAS), baroreceptor reflexes, and hormonal factors such as
antidiuretic hormone (ADH) and atrial natriuretic peptide (ANP).

## Common Cardiovascular Conditions

### Hypertension

Hypertension, or high blood pressure, is defined as a sustained elevation in blood
pressure above 140/90 mmHg. It is a major risk factor for cardiovascular disease,
stroke, and kidney disease. Treatment options include lifestyle modifications and
medications such as ACE inhibitors, beta-blockers, calcium channel blockers, and
diuretics.

### Coronary Artery Disease

Coronary artery disease (CAD) is caused by atherosclerosis, the buildup of plaque
in the coronary arteries. This can lead to angina (chest pain) or myocardial
infarction (heart attack). Risk factors include smoking, diabetes, hyperlipidemia,
and family history.

### Heart Failure

Heart failure occurs when the heart cannot pump enough blood to meet the body's
needs. It can be classified as systolic (reduced ejection fraction) or diastolic
(preserved ejection fraction). Symptoms include dyspnea, fatigue, and peripheral
edema.

## Diagnostic Tests

Common diagnostic tests for cardiovascular conditions include electrocardiogram
(ECG/EKG), echocardiogram, stress testing, cardiac catheterization, and various
blood tests including cardiac enzymes such as troponin and BNP.

## Pharmacological Treatments

### ACE Inhibitors

ACE inhibitors such as lisinopril and enalapril work by blocking the conversion of
angiotensin I to angiotensin II. They are used to treat hypertension and heart failure.

### Beta-Blockers

Beta-blockers such as metoprolol and atenolol reduce heart rate and blood pressure
by blocking the effects of adrenaline. They are used for hypertension, angina, and
post-myocardial infarction management.

### Anticoagulants

Anticoagulants such as warfarin and heparin prevent blood clot formation. They are
used in conditions such as atrial fibrillation, deep vein thrombosis, and mechanical
heart valves.

## Conclusion

Understanding the cardiovascular system is essential for medical practice. Regular
monitoring and appropriate treatment of cardiovascular conditions can significantly
reduce morbidity and mortality associated with these diseases.
"""
    return Document(
        id="doc_long_001",
        source_path="/data/cardio_overview.pdf",
        content_type=ContentType.PDF_TEXTBOOK,
        raw_text=long_text,
        sections=[
            Section(title="Cardiovascular System Overview", level=1, start_char=0, end_char=200),
            Section(title="Heart Anatomy", level=2, start_char=201, end_char=600),
            Section(title="Cardiac Cycle", level=2, start_char=601, end_char=1000),
            Section(title="Blood Pressure Regulation", level=2, start_char=1001, end_char=1400),
            Section(title="Common Cardiovascular Conditions", level=2, start_char=1401, end_char=2500),
            Section(title="Diagnostic Tests", level=2, start_char=2501, end_char=2800),
            Section(title="Pharmacological Treatments", level=2, start_char=2801, end_char=3500),
        ],
        metadata={"page_count": 5}
    )


@pytest.fixture
def empty_document() -> Document:
    """An empty document for edge case testing."""
    return Document(
        id="doc_empty",
        source_path="/data/empty.pdf",
        content_type=ContentType.PDF_TEXTBOOK,
        raw_text="",
        sections=[],
        metadata={}
    )


@pytest.fixture
def document_with_sections() -> Document:
    """A document with clear section boundaries."""
    text = """# Introduction

This is the introduction section with some basic content about the topic.

# Methods

The methodology section describes how the study was conducted. Multiple paragraphs
provide details about the approach taken.

## Data Collection

Data was collected from various sources including clinical records and patient surveys.

## Analysis

Statistical analysis was performed using standard methods.

# Results

The results section presents the findings of the study.

# Discussion

This section discusses the implications of the results.

# Conclusion

Final conclusions and recommendations are presented here.
"""
    return Document(
        id="doc_sections",
        source_path="/data/study.pdf",
        content_type=ContentType.PDF_TEXTBOOK,
        raw_text=text,
        sections=[
            Section(title="Introduction", level=1, start_char=0, end_char=80),
            Section(title="Methods", level=1, start_char=81, end_char=300),
            Section(title="Data Collection", level=2, start_char=150, end_char=250),
            Section(title="Analysis", level=2, start_char=251, end_char=300),
            Section(title="Results", level=1, start_char=301, end_char=380),
            Section(title="Discussion", level=1, start_char=381, end_char=450),
            Section(title="Conclusion", level=1, start_char=451, end_char=520),
        ],
        metadata={}
    )


@pytest.fixture
def medical_text_with_lab_values() -> Document:
    """Document containing lab values that should not be split."""
    text = """
Patient presents with the following lab results:

Serum sodium: 140 mEq/L (normal range: 136-145 mEq/L)
Serum potassium: 4.2 mEq/L (normal range: 3.5-5.0 mEq/L)
Blood glucose: 5.2 mg/dL (fasting, normal range: 70-100 mg/dL)
Hemoglobin A1c: 6.5% (diabetic threshold: >6.5%)
Creatinine: 1.1 mg/dL (normal range: 0.7-1.3 mg/dL)
BUN: 18 mg/dL (normal range: 7-20 mg/dL)
Total cholesterol: 220 mg/dL (desirable: <200 mg/dL)
LDL cholesterol: 140 mg/dL (optimal: <100 mg/dL)
HDL cholesterol: 45 mg/dL (low: <40 mg/dL)
Triglycerides: 175 mg/dL (normal: <150 mg/dL)

Complete blood count shows:
WBC: 7.5 x10^9/L
RBC: 4.8 x10^12/L
Hemoglobin: 14.2 g/dL
Hematocrit: 42%
Platelets: 250 x10^9/L

Additional metabolic panel results include calcium at 9.5 mg/dL and phosphorus
at 3.5 mg/dL. Liver function tests show AST at 25 U/L and ALT at 30 U/L.
"""
    return Document(
        id="doc_labs",
        source_path="/data/lab_results.pdf",
        content_type=ContentType.PDF_NOTES,
        raw_text=text,
        sections=[],
        metadata={}
    )


@pytest.fixture
def medical_text_with_drugs() -> Document:
    """Document containing drug doses that should not be split."""
    text = """
Current Medications:

1. Metoprolol 25mg twice daily for rate control
2. Lisinopril 10mg once daily for blood pressure
3. Atorvastatin 40mg at bedtime for hyperlipidemia
4. Aspirin 81mg daily for cardiovascular protection
5. Metformin 500mg twice daily for diabetes
6. Omeprazole 20mg once daily for GERD
7. Furosemide 40mg once daily for fluid management
8. Warfarin 5mg daily (dose adjusted based on INR)
9. Amlodipine 5mg once daily for additional BP control
10. Gabapentin 300mg three times daily for neuropathy

The patient has been on metoprolol 25mg for the past 6 months with good heart rate
control. Blood pressure remains slightly elevated despite lisinopril 10mg, so we may
consider increasing to 20mg or adding a second agent.

Previous trials of carvedilol 12.5mg were discontinued due to fatigue. The patient
tolerated labetalol 100mg well but switched to metoprolol for convenience.
"""
    return Document(
        id="doc_drugs",
        source_path="/data/medications.pdf",
        content_type=ContentType.PDF_NOTES,
        raw_text=text,
        sections=[],
        metadata={}
    )


@pytest.fixture
def medical_text_with_anatomy() -> Document:
    """Document containing anatomical terms that should not be split."""
    text = """
Cardiac Catheterization Report:

The left anterior descending artery shows 70% stenosis in the proximal segment.
The right coronary artery has mild diffuse disease with no significant stenosis.
The left circumflex artery is patent with good flow.

Additional findings:
- The left main coronary artery is normal
- The right posterior descending artery has minor plaque
- Left ventricular function is preserved with EF 55%
- The left anterior descending artery supplies a large territory

The patient's symptoms are consistent with disease in the left anterior descending
artery territory. The right coronary artery and left circumflex do not appear to be
the culprit vessels.

Recommendation: PCI to the left anterior descending artery with drug-eluting stent.
Post-procedure, the left anterior descending artery showed excellent flow with
no residual stenosis.
"""
    return Document(
        id="doc_anatomy",
        source_path="/data/cath_report.pdf",
        content_type=ContentType.PDF_NOTES,
        raw_text=text,
        sections=[],
        metadata={}
    )
