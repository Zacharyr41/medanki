# Customizing Generation

MedAnki provides several options to tailor flashcard generation to your learning needs.

## Generation Options

### Target Exam

Choose the exam you're preparing for:

| Exam | Focus | Card Style |
|------|-------|------------|
| **MCAT** | Basic sciences, critical thinking | Shorter vignettes, more cloze cards |
| **USMLE Step 1** | Basic science mechanisms | Pathophysiology-focused vignettes |
| **USMLE Step 2** | Clinical management | Management-focused vignettes |

The selected exam affects:
- Topic classification and tagging
- Vignette complexity and focus
- Question type distribution

### Card Types

**Cloze Only**
- Fast to generate
- Best for memorization-heavy content
- Ideal for biochemistry, pharmacology facts

**Vignette Only**
- More processing time
- Best for clinical content
- Ideal for pathology, clinical medicine

**Both Types**
- Comprehensive coverage
- Mixed learning approach
- Ideal for integrated studying

### Max Cards per Chunk

Controls how many cards are generated for each content section.

| Setting | Use Case |
|---------|----------|
| 1-3 | Quick review, key concepts only |
| 4-6 | Balanced coverage (recommended) |
| 7-10 | Comprehensive, detailed coverage |
| 10+ | Maximum extraction, may include minor details |

**Recommendation:** Start with 3-5 cards per chunk and adjust based on output quality.

## Exam-Specific Recommendations

### MCAT Preparation

```
Exam: MCAT
Card Types: Both
Max Cards: 4-6
```

Focus on:
- Biological and biochemical foundations
- Chemical and physical foundations
- Psychological and social foundations

### USMLE Step 1

```
Exam: USMLE Step 1
Card Types: Both
Max Cards: 5-7
```

Focus on:
- Basic science mechanisms
- Pathophysiology correlations
- First-order pharmacology

### USMLE Step 2

```
Exam: USMLE Step 2
Card Types: Vignette
Max Cards: 3-5
```

Focus on:
- Clinical presentations
- Diagnostic workups
- Management algorithms

## Optimizing for Study Style

### Active Recall Focus

If you prioritize testing yourself:
- Use more cloze cards
- Set higher max cards
- Include vignettes for application

### Clinical Reasoning Focus

If you prioritize clinical thinking:
- Emphasize vignette cards
- Use Step 2 difficulty
- Include mechanism questions

### Efficient Review

If you have limited study time:
- Lower max cards (2-3)
- Focus on high-yield content
- Use cloze for quick review

## Advanced Configuration

### Content Chunking

MedAnki automatically divides your content into chunks for processing. Factors affecting chunking:
- Document structure (headings, sections)
- Content density
- Topic boundaries

**Tip:** Well-organized source material produces better-organized cards.

### Quality vs. Quantity

Higher max cards settings extract more information but may:
- Include lower-yield facts
- Produce some redundant cards
- Take longer to process

Lower max cards settings:
- Focus on key concepts
- Faster processing
- May miss some details

### Topic Tagging

Cards are automatically tagged with:
- Source document
- Content topic
- Exam-specific taxonomy (MCAT/USMLE outline)

Use tags in Anki to:
- Study specific subjects
- Track progress by topic
- Create filtered decks

## Recommended Workflows

### New Topic Learning

1. Upload comprehensive source material
2. Set max cards to 5-7
3. Generate both card types
4. Review and edit in Anki
5. Suspend low-quality cards

### Exam Cramming

1. Upload high-yield review materials
2. Set max cards to 3-4
3. Focus on exam-specific card type
4. Generate and study immediately

### Content Review

1. Upload lecture notes
2. Set max cards to 2-3
3. Generate cloze cards
4. Use for active recall practice
