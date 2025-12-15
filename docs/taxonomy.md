# Taxonomy and Classification

MedAnki uses a hierarchical taxonomy system to classify medical content into MCAT and USMLE topics. This enables organized study decks aligned with standardized exam content.

## MCAT Structure

The MCAT taxonomy follows the official AAMC content categories:

### Biological and Biochemical Foundations (1)

```
1A: Structure and function of proteins and their constituent amino acids
1B: Transmission of genetic information
1C: Transmission of heritable information and its expression
1D: Principles of bioenergetics and fuel molecule metabolism
1E: Assemblies of molecules, cells, and groups of cells
```

### Chemical and Physical Foundations (2)

```
2A: Atomic and molecular structure
2B: Chemical kinetics and equilibrium
2C: Thermodynamics and kinetics
2D: Electrochemistry
2E: Structure, function, and reactivity of biologically relevant molecules
```

### Psychological, Social, and Biological Foundations (3)

```
3A: Sensing the environment
3B: Making sense of the environment
3C: Responding to the world
```

### Critical Analysis and Reasoning Skills (4)

```
4A: Comprehension
4B: Reasoning within the text
4C: Reasoning beyond the text
```

## USMLE Structure

The USMLE taxonomy aligns with Step 1, Step 2, and Step 3 content:

### Step 1 - Basic Sciences

```
Organ Systems:
├── Cardiovascular
├── Respiratory
├── Gastrointestinal
├── Renal/Urinary
├── Reproductive
├── Endocrine
├── Musculoskeletal
├── Nervous System
├── Hematologic/Lymphatic
└── Skin/Connective Tissue

Disciplines:
├── Anatomy
├── Physiology
├── Biochemistry
├── Pharmacology
├── Pathology
├── Microbiology
└── Immunology
```

### Step 2 CK - Clinical Knowledge

```
├── Internal Medicine
├── Surgery
├── Pediatrics
├── Obstetrics/Gynecology
├── Psychiatry
├── Emergency Medicine
└── Preventive Medicine
```

## How Classification Works

### 1. Hybrid Search

The ClassificationService uses hybrid search combining:
- **Semantic similarity**: Vector embeddings capture meaning
- **Keyword matching**: BM25-style term frequency

```python
results = vector_store.hybrid_search(
    query=chunk.text,
    alpha=0.5  # Balance between semantic and keyword
)
```

### 2. Topic Matching

Each chunk is compared against pre-indexed topic descriptions:

```python
@dataclass
class TopicMatch:
    topic_id: str      # e.g., "1A", "Cardiovascular"
    topic_name: str    # Human-readable name
    confidence: float  # 0.0 to 1.0
    exam_type: str     # "mcat" or "usmle"
```

### 3. Threshold Filtering

Results pass through dual thresholds:

```python
BASE_THRESHOLD = 0.65      # Minimum confidence
RELATIVE_THRESHOLD = 0.80  # Must be within 80% of top score

def apply_thresholds(matches):
    top_score = matches[0].confidence
    dynamic_threshold = max(BASE_THRESHOLD, top_score * RELATIVE_THRESHOLD)
    return [m for m in matches if m.confidence >= dynamic_threshold]
```

This allows multi-topic classification while maintaining quality.

### 4. Exam Type Detection

When not specified, the system auto-detects the primary exam type:

```python
def detect_primary_exam(chunk):
    mcat_score = max_score(search_mcat_topics(chunk.text))
    usmle_score = max_score(search_usmle_topics(chunk.text))
    return "usmle" if usmle_score >= mcat_score else "mcat"
```

## Tag Format

### MCAT Tags

Format: `#MCAT::Category::Subcategory`

Examples:
```
#MCAT::Biology::Cell_Biology
#MCAT::Chemistry::Organic_Chemistry
#MCAT::Psychology::Learning_and_Memory
#MCAT::1A::Amino_Acids
```

### USMLE Tags

Format: `#AK_{Step}_v12::System::Topic`

Examples:
```
#AK_Step1_v12::Cardiovascular::Heart_Failure
#AK_Step1_v12::Pharmacology::Antibiotics
#AK_Step2_v12::Surgery::Trauma
```

### Source Tags

Format: `#Source::MedAnki::DocumentName`

Example:
```
#Source::MedAnki::First_Aid_2024
```

## Customizing Taxonomies

### Adding Custom Topics

1. Create a taxonomy JSON file:

```json
{
  "id": "custom",
  "name": "Custom Medical Topics",
  "topics": [
    {
      "id": "custom_cardio",
      "name": "Advanced Cardiology",
      "description": "Heart failure, arrhythmias, interventional procedures",
      "keywords": ["ejection fraction", "ablation", "PCI"]
    },
    {
      "id": "custom_neuro",
      "name": "Neuroimaging",
      "description": "MRI, CT, interpretation of brain imaging",
      "keywords": ["T1", "T2", "FLAIR", "diffusion weighted"]
    }
  ]
}
```

2. Load the custom taxonomy:

```python
taxonomy_service.load_taxonomy("custom", "path/to/custom.json")
```

3. Index topics in vector store:

```python
for topic in custom_taxonomy["topics"]:
    vector_store.index_topic(
        topic_id=topic["id"],
        text=f"{topic['name']}: {topic['description']}",
        metadata={"exam_type": "custom"}
    )
```

### Adjusting Classification Thresholds

For different content types, adjust thresholds:

```python
# Stricter classification (fewer, more confident tags)
classifier = ClassificationService(
    taxonomy_service=taxonomy,
    vector_store=vectors,
    base_threshold=0.75,
    relative_threshold=0.90
)

# More permissive (more multi-topic cards)
classifier = ClassificationService(
    taxonomy_service=taxonomy,
    vector_store=vectors,
    base_threshold=0.55,
    relative_threshold=0.70
)
```

### Custom Tag Builders

Extend TagBuilder for custom formats:

```python
class CustomTagBuilder(TagBuilder):
    def build_custom_tag(self, category: str, topic: str) -> str:
        sanitized_cat = self.sanitize(category)
        sanitized_topic = self.sanitize(topic)
        return f"#Custom::{sanitized_cat}::{sanitized_topic}"
```

## Best Practices

1. **Consistent Naming**: Use standardized topic names across documents
2. **Hierarchical Tags**: Leverage Anki's `::` hierarchy for drill-down study
3. **Multi-Topic Cards**: Allow cards to have multiple relevant topics
4. **Regular Updates**: Refresh topic embeddings when taxonomy changes
5. **Quality Checks**: Review low-confidence classifications manually

## Database Schema

The taxonomy system uses SQLite with a closure table pattern for efficient hierarchy queries.

### Core Tables

```sql
-- Exam definitions (MCAT, USMLE_STEP1, etc.)
exams (id, name, version, source_url, created_at)

-- Taxonomy nodes with parent references
taxonomy_nodes (
    id, exam_id, node_type, code, title, description,
    percentage_min, percentage_max, parent_id, sort_order,
    metadata, created_at, updated_at
)

-- Closure table for hierarchy queries
taxonomy_edges (ancestor_id, descendant_id, depth)

-- Associated keywords for search
keywords (id, node_id, keyword, keyword_type, weight, source)

-- System × Discipline mappings (USMLE)
cross_classifications (
    id, primary_node_id, secondary_node_id,
    relationship_type, weight
)
```

### NodeType Enumeration

```python
class NodeType(str, Enum):
    FOUNDATIONAL_CONCEPT = "foundational_concept"  # MCAT FC1-FC10
    CONTENT_CATEGORY = "content_category"          # MCAT 1A, 2B, etc.
    TOPIC = "topic"                                # Leaf-level topics
    SUBTOPIC = "subtopic"                          # Sub-topics
    ORGAN_SYSTEM = "organ_system"                  # USMLE systems
    DISCIPLINE = "discipline"                      # USMLE disciplines
    SECTION = "section"                            # Generic section
```

### Closure Table Operations

The closure table enables efficient hierarchy queries:

```python
# Get all ancestors (root to parent)
ancestors = await service.get_ancestors(node_id)

# Get all descendants with optional depth limit
descendants = await service.get_descendants(node_id, max_depth=2)

# Get full path as string
path = await service.get_path(node_id)  # "FC1 > 1A > Amino Acids"
```

### Resource Mappings

External resources (First Aid, Pathoma, etc.) can be mapped to taxonomy nodes:

```sql
-- Resource definitions
resources (id, name, resource_type, version, anking_tag_prefix, metadata)

-- Resource sections (chapters, pages)
resource_sections (
    id, resource_id, title, section_type, code,
    parent_id, page_start, page_end, duration_seconds, sort_order
)

-- Node-to-section mappings
resource_mappings (id, node_id, section_id, relevance_score, is_primary)
```

### AnKing Tag Integration

The taxonomy supports AnKing-style hierarchical tags:

```sql
anking_tags (id, tag_path, resource, note_count, parent_tag_path)
```

Generate AnKing-compatible tags:

```python
tag = await service.generate_anking_tag("SYS3A")
# Returns: "#AK_Step1_v12::Cardiovascular::Cardiac_Anatomy_and_Physiology"
```

### MeSH Vocabulary Integration

MeSH concepts can be linked to taxonomy nodes for synonym expansion:

```sql
-- Cached MeSH concepts
mesh_concepts (mesh_id, name, tree_numbers, scope_note, synonyms, fetched_at)

-- Node-to-MeSH mappings
mesh_mappings (id, node_id, mesh_id, match_score)
```
