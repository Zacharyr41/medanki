from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from medanki.generation.vignette import VignetteGenerator
from medanki.models.cards import VignetteCard

if TYPE_CHECKING:
    pass


class TestVignetteCardStructure:
    @pytest.fixture
    def mock_llm_client(self) -> MagicMock:
        client = MagicMock()
        client.generate_structured = AsyncMock()
        return client

    @pytest.fixture
    def generator(self, mock_llm_client: MagicMock) -> VignetteGenerator:
        return VignetteGenerator(llm_client=mock_llm_client)

    @pytest.mark.asyncio
    async def test_generates_vignette_cards(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="A 45-year-old male presents with chest pain.",
                    question="What is the most likely diagnosis?",
                    options=[
                        MagicMock(letter="A", text="Myocardial infarction"),
                        MagicMock(letter="B", text="Pulmonary embolism"),
                        MagicMock(letter="C", text="Aortic dissection"),
                        MagicMock(letter="D", text="Pericarditis"),
                        MagicMock(letter="E", text="Costochondritis"),
                    ],
                    answer="A",
                    explanation="The presentation is classic for MI.",
                )
            ]
        )

        cards = await generator.generate(
            content="Cardiology content about chest pain",
            source_chunk_id=uuid4(),
        )

        assert isinstance(cards, list)
        assert len(cards) > 0
        assert all(isinstance(card, VignetteCard) for card in cards)

    @pytest.mark.asyncio
    async def test_has_clinical_stem(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="A 55-year-old woman with diabetes presents with acute onset dyspnea.",
                    question="What is the next best step?",
                    options=[
                        MagicMock(letter="A", text="ECG"),
                        MagicMock(letter="B", text="Chest X-ray"),
                        MagicMock(letter="C", text="D-dimer"),
                        MagicMock(letter="D", text="Troponin"),
                        MagicMock(letter="E", text="BNP"),
                    ],
                    answer="A",
                    explanation="ECG is the first step in dyspnea workup.",
                )
            ]
        )

        cards = await generator.generate(
            content="Dyspnea evaluation",
            source_chunk_id=uuid4(),
        )

        assert cards[0].stem
        assert len(cards[0].stem) > 20

    @pytest.mark.asyncio
    async def test_has_question(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="A 30-year-old male presents with fever.",
                    question="What is the most likely diagnosis?",
                    options=[
                        MagicMock(letter="A", text="Pneumonia"),
                        MagicMock(letter="B", text="URI"),
                        MagicMock(letter="C", text="Influenza"),
                        MagicMock(letter="D", text="COVID-19"),
                        MagicMock(letter="E", text="Bronchitis"),
                    ],
                    answer="C",
                    explanation="Influenza is common during flu season.",
                )
            ]
        )

        cards = await generator.generate(
            content="Infectious diseases",
            source_chunk_id=uuid4(),
        )

        assert cards[0].question
        assert "?" in cards[0].question

    @pytest.mark.asyncio
    async def test_has_five_options(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="A 60-year-old presents with hypertension.",
                    question="What is the first-line treatment?",
                    options=[
                        MagicMock(letter="A", text="Lisinopril"),
                        MagicMock(letter="B", text="Metoprolol"),
                        MagicMock(letter="C", text="Amlodipine"),
                        MagicMock(letter="D", text="Hydrochlorothiazide"),
                        MagicMock(letter="E", text="Losartan"),
                    ],
                    answer="A",
                    explanation="ACE inhibitors are first-line.",
                )
            ]
        )

        cards = await generator.generate(
            content="Hypertension treatment",
            source_chunk_id=uuid4(),
        )

        assert len(cards[0].options) == 5
        expected_letters = ["A", "B", "C", "D", "E"]
        actual_letters = [opt.letter for opt in cards[0].options]
        assert actual_letters == expected_letters

    @pytest.mark.asyncio
    async def test_has_correct_answer(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="A patient presents with symptoms.",
                    question="What is the diagnosis?",
                    options=[
                        MagicMock(letter="A", text="Disease A"),
                        MagicMock(letter="B", text="Disease B"),
                        MagicMock(letter="C", text="Disease C"),
                        MagicMock(letter="D", text="Disease D"),
                        MagicMock(letter="E", text="Disease E"),
                    ],
                    answer="B",
                    explanation="Disease B is correct.",
                )
            ]
        )

        cards = await generator.generate(
            content="Medical content",
            source_chunk_id=uuid4(),
        )

        assert cards[0].answer in ["A", "B", "C", "D", "E"]

    @pytest.mark.asyncio
    async def test_has_explanation(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="Clinical presentation.",
                    question="What is the mechanism?",
                    options=[
                        MagicMock(letter="A", text="Mechanism A"),
                        MagicMock(letter="B", text="Mechanism B"),
                        MagicMock(letter="C", text="Mechanism C"),
                        MagicMock(letter="D", text="Mechanism D"),
                        MagicMock(letter="E", text="Mechanism E"),
                    ],
                    answer="A",
                    explanation="The mechanism involves specific pathophysiology that explains the clinical findings.",
                )
            ]
        )

        cards = await generator.generate(
            content="Pathophysiology content",
            source_chunk_id=uuid4(),
        )

        assert cards[0].explanation
        assert len(cards[0].explanation) > 10


class TestClinicalRealism:
    @pytest.fixture
    def mock_llm_client(self) -> MagicMock:
        client = MagicMock()
        client.generate_structured = AsyncMock()
        return client

    @pytest.fixture
    def generator(self, mock_llm_client: MagicMock) -> VignetteGenerator:
        return VignetteGenerator(llm_client=mock_llm_client)

    @pytest.mark.asyncio
    async def test_includes_demographics(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="A 52-year-old female smoker presents with chronic cough.",
                    question="What is the most likely diagnosis?",
                    options=[
                        MagicMock(letter="A", text="COPD"),
                        MagicMock(letter="B", text="Asthma"),
                        MagicMock(letter="C", text="Lung cancer"),
                        MagicMock(letter="D", text="Bronchiectasis"),
                        MagicMock(letter="E", text="Tuberculosis"),
                    ],
                    answer="A",
                    explanation="COPD is common in smokers.",
                )
            ]
        )

        cards = await generator.generate(
            content="Pulmonology content",
            source_chunk_id=uuid4(),
        )

        stem = cards[0].stem.lower()
        has_age = any(char.isdigit() for char in cards[0].stem)
        has_sex = "male" in stem or "female" in stem or "woman" in stem or "man" in stem
        assert has_age, "Stem should include patient age"
        assert has_sex, "Stem should include patient sex"

    @pytest.mark.asyncio
    async def test_includes_relevant_history(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="A 65-year-old male with a history of diabetes and hypertension presents with crushing chest pain radiating to the left arm. He denies recent trauma.",
                    question="What is the most likely diagnosis?",
                    options=[
                        MagicMock(letter="A", text="STEMI"),
                        MagicMock(letter="B", text="NSTEMI"),
                        MagicMock(letter="C", text="Unstable angina"),
                        MagicMock(letter="D", text="Stable angina"),
                        MagicMock(letter="E", text="GERD"),
                    ],
                    answer="A",
                    explanation="Classic STEMI presentation with risk factors.",
                )
            ]
        )

        cards = await generator.generate(
            content="Cardiology emergency",
            source_chunk_id=uuid4(),
        )

        stem = cards[0].stem.lower()
        has_history = "history" in stem or "diabetes" in stem or "hypertension" in stem
        assert has_history, "Stem should include relevant medical history"

    @pytest.mark.asyncio
    async def test_includes_physical_exam(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="A 45-year-old male presents with abdominal pain. On examination, there is rebound tenderness in the right lower quadrant.",
                    question="What is the most likely diagnosis?",
                    options=[
                        MagicMock(letter="A", text="Appendicitis"),
                        MagicMock(letter="B", text="Cholecystitis"),
                        MagicMock(letter="C", text="Pancreatitis"),
                        MagicMock(letter="D", text="Diverticulitis"),
                        MagicMock(letter="E", text="Gastritis"),
                    ],
                    answer="A",
                    explanation="RLQ tenderness with rebound is classic for appendicitis.",
                )
            ]
        )

        cards = await generator.generate(
            content="Acute abdomen",
            source_chunk_id=uuid4(),
        )

        stem = cards[0].stem.lower()
        has_exam = "examination" in stem or "exam" in stem or "tenderness" in stem or "auscultation" in stem
        assert has_exam, "Stem should include physical examination findings when appropriate"

    @pytest.mark.asyncio
    async def test_includes_lab_values(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="A 58-year-old diabetic presents with fatigue. Labs show: Hemoglobin 8.5 g/dL, MCV 110 fL, serum B12 150 pg/mL.",
                    question="What is the most likely cause of anemia?",
                    options=[
                        MagicMock(letter="A", text="B12 deficiency"),
                        MagicMock(letter="B", text="Iron deficiency"),
                        MagicMock(letter="C", text="Folate deficiency"),
                        MagicMock(letter="D", text="Chronic disease"),
                        MagicMock(letter="E", text="Hemolysis"),
                    ],
                    answer="A",
                    explanation="Low B12 with macrocytic anemia indicates B12 deficiency.",
                )
            ]
        )

        cards = await generator.generate(
            content="Hematology labs",
            source_chunk_id=uuid4(),
        )

        stem = cards[0].stem
        has_units = "g/dL" in stem or "mg/dL" in stem or "mL" in stem or "fL" in stem
        assert has_units, "Lab values should include units"

    @pytest.mark.asyncio
    async def test_distractor_quality(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="A 35-year-old presents with palpitations and weight loss.",
                    question="What is the most likely diagnosis?",
                    options=[
                        MagicMock(letter="A", text="Hyperthyroidism"),
                        MagicMock(letter="B", text="Pheochromocytoma"),
                        MagicMock(letter="C", text="Anxiety disorder"),
                        MagicMock(letter="D", text="Atrial fibrillation"),
                        MagicMock(letter="E", text="Carcinoid syndrome"),
                    ],
                    answer="A",
                    explanation="Palpitations and weight loss are classic for hyperthyroidism.",
                )
            ]
        )

        cards = await generator.generate(
            content="Endocrinology",
            source_chunk_id=uuid4(),
        )

        options = cards[0].options
        option_texts = [opt.text for opt in options]
        assert len(set(option_texts)) == 5, "All options should be unique"
        for opt in options:
            assert len(opt.text) >= 3, "Distractor options should be substantive"


class TestUSMLEStyle:
    @pytest.fixture
    def mock_llm_client(self) -> MagicMock:
        client = MagicMock()
        client.generate_structured = AsyncMock()
        return client

    @pytest.fixture
    def generator(self, mock_llm_client: MagicMock) -> VignetteGenerator:
        return VignetteGenerator(llm_client=mock_llm_client)

    @pytest.mark.asyncio
    async def test_asks_next_step(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="A 70-year-old presents to the ED with chest pain.",
                    question="What is the next best step in management?",
                    options=[
                        MagicMock(letter="A", text="ECG"),
                        MagicMock(letter="B", text="Troponin"),
                        MagicMock(letter="C", text="CT angiography"),
                        MagicMock(letter="D", text="Echocardiogram"),
                        MagicMock(letter="E", text="Stress test"),
                    ],
                    answer="A",
                    explanation="ECG is always first in chest pain evaluation.",
                )
            ]
        )

        cards = await generator.generate(
            content="Emergency cardiology",
            source_chunk_id=uuid4(),
            question_type="next_step",
        )

        question = cards[0].question.lower()
        assert "next" in question or "step" in question or "management" in question

    @pytest.mark.asyncio
    async def test_asks_diagnosis(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="A 25-year-old presents with joint pain and butterfly rash.",
                    question="What is the most likely diagnosis?",
                    options=[
                        MagicMock(letter="A", text="SLE"),
                        MagicMock(letter="B", text="Rheumatoid arthritis"),
                        MagicMock(letter="C", text="Dermatomyositis"),
                        MagicMock(letter="D", text="Scleroderma"),
                        MagicMock(letter="E", text="Sjogren syndrome"),
                    ],
                    answer="A",
                    explanation="Butterfly rash with joint pain is pathognomonic for SLE.",
                )
            ]
        )

        cards = await generator.generate(
            content="Rheumatology",
            source_chunk_id=uuid4(),
            question_type="diagnosis",
        )

        question = cards[0].question.lower()
        assert "diagnosis" in question or "likely" in question

    @pytest.mark.asyncio
    async def test_asks_mechanism(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="A patient on warfarin develops bleeding after starting fluconazole.",
                    question="What is the mechanism of this drug interaction?",
                    options=[
                        MagicMock(letter="A", text="CYP450 inhibition"),
                        MagicMock(letter="B", text="CYP450 induction"),
                        MagicMock(letter="C", text="Protein displacement"),
                        MagicMock(letter="D", text="Renal competition"),
                        MagicMock(letter="E", text="GI absorption"),
                    ],
                    answer="A",
                    explanation="Fluconazole inhibits CYP2C9, increasing warfarin levels.",
                )
            ]
        )

        cards = await generator.generate(
            content="Pharmacology interactions",
            source_chunk_id=uuid4(),
            question_type="mechanism",
        )

        question = cards[0].question.lower()
        assert "mechanism" in question or "how" in question or "why" in question

    @pytest.mark.asyncio
    async def test_appropriate_difficulty(
        self, generator: VignetteGenerator, mock_llm_client: MagicMock
    ) -> None:
        mock_llm_client.generate_structured.return_value = MagicMock(
            cards=[
                MagicMock(
                    stem="A 40-year-old presents with symptoms.",
                    question="What is the diagnosis?",
                    options=[
                        MagicMock(letter="A", text="Condition A"),
                        MagicMock(letter="B", text="Condition B"),
                        MagicMock(letter="C", text="Condition C"),
                        MagicMock(letter="D", text="Condition D"),
                        MagicMock(letter="E", text="Condition E"),
                    ],
                    answer="A",
                    explanation="Detailed explanation.",
                )
            ]
        )

        cards = await generator.generate(
            content="Medical content",
            source_chunk_id=uuid4(),
            difficulty="step1",
        )

        assert len(cards) > 0
