# Topic Taxonomy and Tagging

MedAnki automatically classifies your content against official exam outlines, making it easy to organize and track your studying.

## How Tagging Works

When you upload content, MedAnki:

1. **Analyzes content** - Identifies medical concepts and terminology
2. **Matches to taxonomy** - Maps content to exam-specific topic areas
3. **Applies tags** - Each card receives relevant topic tags
4. **Exports with tags** - Tags transfer to Anki for organization

## MCAT Content Outline

Cards are tagged against the AAMC MCAT content outline:

### Biological and Biochemical Foundations (Bio/Biochem)
- Structure and function of proteins
- Transmission of genetic information
- Cell biology and metabolism
- Organ systems

### Chemical and Physical Foundations (Chem/Phys)
- Atomic and molecular structure
- Thermodynamics and kinetics
- Fluids and circuits
- Light and sound

### Psychological, Social, and Biological Foundations (Psych/Soc)
- Perception and cognition
- Behavior and learning
- Social processes
- Attitude and identity

### Critical Analysis and Reasoning Skills (CARS)
- Comprehension
- Reasoning within text
- Reasoning beyond text

## USMLE Content Outline

Cards are tagged against USMLE Step 1 and Step 2 outlines:

### Step 1 Topics

**Basic Sciences:**
- Anatomy
- Behavioral sciences
- Biochemistry
- Microbiology
- Pathology
- Pharmacology
- Physiology

**Organ Systems:**
- Cardiovascular
- Endocrine
- Gastrointestinal
- Hematologic/Lymphoreticular
- Musculoskeletal
- Nervous System
- Renal/Urinary
- Reproductive
- Respiratory
- Skin/Subcutaneous

### Step 2 Topics

**Task Categories:**
- Health Maintenance
- Diagnosis
- Prognosis
- Treatment/Management

**Patient Age Groups:**
- Newborn
- Infancy
- Childhood
- Adolescence
- Adult
- Geriatric

**Clinical Settings:**
- Ambulatory
- Emergency
- Inpatient

## Using Tags in Anki

### Viewing Tags

After importing your deck:
1. Open Anki
2. Click "Browse"
3. View tag hierarchy in left sidebar

### Studying by Tag

Create filtered decks for targeted study:

1. Tools → Create Filtered Deck
2. Search: `tag:cardiovascular`
3. Name your deck
4. Study!

### Tag Hierarchy

Tags are hierarchical:
```
medanki::usmle::pathology::cardiovascular::heart_failure
```

This allows filtering at any level:
- All MedAnki cards: `tag:medanki`
- All pathology: `tag:medanki::usmle::pathology`
- Specific topic: `tag:medanki::usmle::pathology::cardiovascular`

### Combining Tags

Search for multiple tags:
```
tag:cardiovascular AND tag:pharmacology
```

Study cards covering cardiovascular pharmacology.

## Tracking Progress

### By Topic

Use Anki's statistics to track:
- Cards studied per topic
- Retention rates by subject
- Weak areas needing review

### Study Recommendations

1. **Identify weak areas** - Sort by lowest retention
2. **Focus study** - Create filtered decks for weak topics
3. **Balance coverage** - Ensure all topics receive attention
4. **Track improvement** - Monitor retention over time

## Tag Accuracy

### What affects tagging accuracy:

**Improves accuracy:**
- Clear, explicit content
- Standard medical terminology
- Well-organized source material

**May reduce accuracy:**
- Abbreviations without context
- Highly specialized content
- Interdisciplinary topics

### Reviewing tags

After generation:
1. Preview cards before downloading
2. Check topic assignments
3. Report any obvious misclassifications

### Manual tag editing

In Anki, you can:
- Add missing tags
- Remove incorrect tags
- Create custom tag hierarchies

## Best Practices

1. **Organize source material** - Clear structure helps classification
2. **Use standard terminology** - Helps accurate topic matching
3. **Review periodically** - Adjust tags as needed in Anki
4. **Leverage hierarchy** - Study broad topics or specific areas
5. **Track weak areas** - Use tags to identify study priorities
