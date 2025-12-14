# Card Types

MedAnki generates two types of flashcards optimized for medical education: **Cloze deletions** and **Clinical vignettes**.

## Cloze Deletions

Cloze deletions are fill-in-the-blank style cards that test recall of specific facts.

### Format

```
The {{c1::sinoatrial (SA) node}} is the primary pacemaker of the heart.
```

When studying, this appears as:

**Front:** The [...] is the primary pacemaker of the heart.
**Back:** sinoatrial (SA) node

### Multiple Clozes

Cards can contain multiple cloze deletions:

```
The {{c1::sinoatrial (SA) node}} is located in the {{c2::right atrium}}.
```

This creates two cards from one note, testing each fact independently.

### Validation Rules

MedAnki enforces quality rules for cloze cards:
- **Sequential numbering:** c1, c2, c3... (no gaps)
- **Answer length:** 1-4 words per cloze
- **At least one cloze:** Every card must have a testable element

### Best For

- Basic science facts
- Terminology and definitions
- Numerical values (lab values, dosages)
- Anatomical relationships
- Biochemical pathways

### Example Cards

**Pharmacology:**
> Beta-1 receptors are primarily found in the {{c1::heart}}, while beta-2 receptors are found in the {{c2::lungs}}.

**Biochemistry:**
> Glycolysis produces a net gain of {{c1::2 ATP}} molecules per glucose molecule.

**Anatomy:**
> The {{c1::femoral nerve}} provides motor innervation to the {{c2::quadriceps}}.

## Clinical Vignettes

Clinical vignettes are USMLE-style questions that present patient scenarios and test clinical reasoning.

### Format

A vignette consists of:
1. **Stem:** Patient presentation with demographics, history, and findings
2. **Question:** What is being asked
3. **Options:** Five answer choices (A-E)
4. **Answer:** Correct option letter
5. **Explanation:** Why the answer is correct

### Question Types

MedAnki generates three types of vignette questions:

#### Diagnosis Questions
> "Which of the following is the most likely diagnosis?"

Tests pattern recognition and diagnostic reasoning.

#### Next Step Questions
> "Which of the following is the most appropriate next step in management?"

Tests clinical decision-making and treatment protocols.

#### Mechanism Questions
> "Which of the following mechanisms best explains these findings?"

Tests understanding of pathophysiology.

### Difficulty Levels

- **Step 1:** Basic science correlations, simpler presentations
- **Step 2:** More complex clinical scenarios, management focus

### Validation Rules

- **5 options:** Always A through E
- **Answer length:** 1-4 words per option
- **Plausible distractors:** Wrong answers are realistic but distinguishable
- **Complete explanation:** Every card includes reasoning

### Best For

- Clinical reasoning practice
- Integrating basic science with clinical presentation
- Test preparation (USMLE, COMLEX)
- Differential diagnosis practice

### Example Card

**Stem:**
> A 55-year-old man with a history of hypertension and type 2 diabetes presents with crushing substernal chest pain radiating to his left arm for the past 2 hours. He appears diaphoretic. ECG shows ST-segment elevation in leads V1-V4.

**Question:**
> Which of the following is the most likely diagnosis?

**Options:**
- A. Acute pericarditis
- B. Aortic dissection
- C. Anterior STEMI
- D. Pulmonary embolism
- E. Unstable angina

**Answer:** C

**Explanation:**
> ST-segment elevation in leads V1-V4 indicates anterior wall involvement. The clinical presentation of crushing chest pain with radiation and diaphoresis, combined with cardiac risk factors, is classic for acute myocardial infarction.

## Choosing Card Types

| If you're studying... | Recommended Type |
|----------------------|------------------|
| Basic science facts | Cloze |
| Definitions/terminology | Cloze |
| Clinical presentations | Vignette |
| Treatment protocols | Both |
| Pathophysiology | Both |
| Board exam prep | Both |

## Combining Card Types

You can generate both types simultaneously by selecting both checkboxes. MedAnki will:
1. Generate cloze cards for factual content
2. Generate vignettes for clinically-applicable content
3. Avoid redundant coverage of the same material
