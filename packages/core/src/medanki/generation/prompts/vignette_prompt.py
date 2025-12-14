from __future__ import annotations

VIGNETTE_SYSTEM_PROMPT = """You are a medical education expert specializing in creating USMLE-style clinical vignette questions. Generate high-quality multiple choice questions based on the provided medical content.

Guidelines for creating vignettes:
1. Include realistic patient demographics (age, sex)
2. Include pertinent positives AND negatives in the history
3. Include relevant physical examination findings when appropriate
4. Include laboratory values with units when relevant
5. Create 5 answer choices (A through E)
6. All distractors should be plausible but clearly distinguishable from the correct answer
7. Write concise explanations that explain why the correct answer is right and why key distractors are wrong

Question types:
- Diagnosis: "What is the most likely diagnosis?"
- Next Step: "What is the next best step in management?"
- Mechanism: "What is the mechanism of this patient's condition?"
"""

VIGNETTE_FEW_SHOT_EXAMPLES = """
Example 1 (Diagnosis question):
Stem: A 45-year-old female presents with fatigue and weight gain over the past 6 months. She also reports constipation and cold intolerance. Physical examination reveals dry skin, bradycardia (HR 52), and delayed relaxation of deep tendon reflexes. TSH is 15 mU/L (normal 0.5-4.5) and free T4 is 0.4 ng/dL (normal 0.8-1.8).
Question: What is the most likely diagnosis?
Options:
A. Hypothyroidism
B. Hyperthyroidism
C. Euthyroid sick syndrome
D. Subclinical hypothyroidism
E. Hashimoto thyroiditis
Answer: A
Explanation: The constellation of fatigue, weight gain, constipation, cold intolerance, dry skin, bradycardia, and delayed DTRs combined with elevated TSH and low free T4 is classic for primary hypothyroidism.

Example 2 (Next Step question):
Stem: A 68-year-old male with a history of atrial fibrillation on warfarin presents with acute onset of severe abdominal pain out of proportion to exam findings. He rates the pain 10/10 but abdominal examination reveals only mild tenderness without guarding. Lactate is 4.2 mmol/L (normal <2.0).
Question: What is the next best step in management?
Options:
A. CT angiography
B. Exploratory laparotomy
C. Upper endoscopy
D. Colonoscopy
E. Abdominal ultrasound
Answer: A
Explanation: Pain out of proportion to exam with elevated lactate in a patient with atrial fibrillation suggests mesenteric ischemia. CT angiography is the diagnostic study of choice to confirm the diagnosis and plan intervention.

Example 3 (Mechanism question):
Stem: A 55-year-old male with type 2 diabetes started on metformin develops nausea and abdominal discomfort. Labs show pH 7.25, bicarbonate 12 mEq/L, and lactate 8 mmol/L. Serum creatinine is 3.5 mg/dL (baseline 1.0).
Question: What is the mechanism of this patient's condition?
Options:
A. Mitochondrial inhibition
B. Insulin resistance
C. Gluconeogenesis stimulation
D. Beta cell toxicity
E. Hepatic glycogenolysis
Answer: A
Explanation: Metformin-associated lactic acidosis (MALA) occurs due to metformin's inhibition of mitochondrial complex I, impairing oxidative phosphorylation and increasing anaerobic metabolism. This is exacerbated by renal failure, which decreases metformin clearance.
"""

QUESTION_TYPE_TEMPLATES = {
    "diagnosis": "What is the most likely diagnosis?",
    "next_step": "What is the next best step in management?",
    "mechanism": "What is the mechanism of this patient's condition?",
}
