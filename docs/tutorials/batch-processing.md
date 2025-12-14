# Tutorial: Batch Processing

**Time:** 15 minutes
**Difficulty:** Intermediate

Learn to process multiple files efficiently using the MedAnki CLI.

## Prerequisites

- MedAnki CLI installed (`pip install medanki-cli`)
- Multiple PDF or Markdown files to process
- Anki installed for importing

## Step 1: Install the CLI

```bash
pip install medanki-cli
```

Verify installation:

```bash
medanki --version
```

## Step 2: Organize Your Files

Create a directory structure for your study materials:

```
study-materials/
├── biochemistry/
│   ├── amino-acids.pdf
│   ├── metabolism.pdf
│   └── enzymes.pdf
├── pathology/
│   ├── cardiovascular.pdf
│   └── respiratory.pdf
└── pharmacology/
    ├── autonomic.pdf
    └── cardiac-drugs.pdf
```

## Step 3: Process a Single File

Start with one file to confirm settings:

```bash
medanki generate biochemistry/amino-acids.pdf \
  --exam mcat \
  --card-types cloze,vignette \
  --max-cards 5 \
  --output amino-acids.apkg
```

Review the output before batch processing.

## Step 4: Process a Directory

Process all files in a directory:

```bash
medanki generate biochemistry/ \
  --exam usmle-step1 \
  --card-types both \
  --max-cards 4 \
  --output biochemistry-deck.apkg
```

This combines all files into a single deck.

## Step 5: Process Multiple Directories

Create separate decks for each subject:

```bash
# Create decks for each subject
for subject in biochemistry pathology pharmacology; do
  medanki generate $subject/ \
    --exam usmle-step1 \
    --card-types both \
    --max-cards 4 \
    --output ${subject}-deck.apkg
done
```

## Step 6: Using Configuration Files

Create a config file for consistent settings:

```yaml
# medanki.yaml
exam: usmle-step1
card_types:
  - cloze
  - vignette
max_cards: 5
```

Use the config:

```bash
medanki generate biochemistry/ --config medanki.yaml
```

## Step 7: Parallel Processing

Process multiple files simultaneously:

```bash
medanki generate study-materials/ \
  --parallel 4 \
  --output master-deck.apkg
```

The `--parallel` flag sets concurrent processing threads.

## Step 8: Output Organization

### Single Master Deck

Combine everything:

```bash
medanki generate study-materials/ --output master-deck.apkg
```

### Separate Decks Per Directory

Keep subjects separate:

```bash
medanki generate study-materials/ \
  --split-by-directory \
  --output-dir ./decks/
```

Creates:
```
decks/
├── biochemistry.apkg
├── pathology.apkg
└── pharmacology.apkg
```

### Separate Decks Per File

Maximum granularity:

```bash
medanki generate study-materials/ \
  --split-by-file \
  --output-dir ./decks/
```

## Step 9: Import Multiple Decks

Import all decks to Anki:

**macOS/Linux:**
```bash
for deck in decks/*.apkg; do
  open -a Anki "$deck"
  sleep 2
done
```

**Windows:**
```powershell
Get-ChildItem decks/*.apkg | ForEach-Object {
  Start-Process $_.FullName
  Start-Sleep -Seconds 2
}
```

## Step 10: Verify Imports

1. Open Anki
2. Check deck list for all imported decks
3. Browse cards to verify quality
4. Check tags for organization

## Common Workflows

### Weekly Lecture Processing

```bash
#!/bin/bash
# weekly-process.sh

WEEK=$1
INPUT_DIR="lectures/week-${WEEK}"
OUTPUT="weekly-decks/week-${WEEK}.apkg"

medanki generate "$INPUT_DIR" \
  --exam usmle-step1 \
  --card-types both \
  --max-cards 4 \
  --output "$OUTPUT"

echo "Generated: $OUTPUT"
```

Usage:
```bash
./weekly-process.sh 12
```

### Exam Prep Batch

```bash
#!/bin/bash
# exam-prep.sh

medanki generate high-yield/ \
  --exam usmle-step1 \
  --card-types vignette \
  --max-cards 3 \
  --output step1-vignettes.apkg

medanki generate high-yield/ \
  --exam usmle-step1 \
  --card-types cloze \
  --max-cards 5 \
  --output step1-cloze.apkg
```

## Performance Tips

| Files | Recommended --parallel |
|-------|----------------------|
| 1-5 | 1 (default) |
| 5-20 | 2-3 |
| 20+ | 4 |

Higher parallelism uses more memory and API calls.

## Error Handling

### Resume failed batch

```bash
medanki generate study-materials/ \
  --resume \
  --output master-deck.apkg
```

### Skip problem files

```bash
medanki generate study-materials/ \
  --skip-errors \
  --output master-deck.apkg
```

### Verbose output

```bash
medanki generate study-materials/ \
  --verbose \
  --output master-deck.apkg
```

## Next Steps

- [Optimize your generated cards](./optimizing-cards.md)
- [Learn about card types](../user-guide/card-types.md)
- [Customize generation settings](../user-guide/customization.md)
