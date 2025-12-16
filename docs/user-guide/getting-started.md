# Getting Started with MedAnki

MedAnki converts your medical study materials into high-quality Anki flashcards, automatically tagged against MCAT and USMLE taxonomies.

## Quick Start (5 minutes)

### 1. Access MedAnki

**Web Interface:** Navigate to http://localhost:5173 (or your deployed URL)

**CLI:** Install with `pip install medanki-cli`

### 2. Choose Your Input Method

MedAnki offers two ways to generate flashcards:

**Option A: Upload a File**
- Drag and drop or click to browse
- Supported formats: PDF, Markdown, TXT, DOCX

**Option B: Describe Topics**
- Click "Describe Topics" tab
- Enter what you want to study (e.g., "cardiac electrophysiology")
- Great for learning new topics without existing materials

### 3. Configure Options

- **Target Exam:** Choose MCAT or USMLE Step 1
- **Card Types:** Cloze deletions, clinical vignettes, or both
- **Total Cards:** How many cards to generate (1-100, default 20)

### 4. Generate and Download

Click "Generate Flashcards" and wait for processing. You'll see:
- Real-time progress updates
- Stage-by-stage breakdown
- Estimated time remaining

Once complete, preview your cards and download the .apkg file.

## Card Preview Features

After generation completes, you can preview and filter your cards:

### Filtering Cards

Use the **Type Filter** dropdown to view specific card types:
- **All Types:** Shows all generated cards
- **Cloze:** Fill-in-the-blank style cards
- **Vignette:** Clinical case-based questions
- **Basic Q&A:** Simple question and answer format

The filter dropdown remains visible even when no cards match your selection, allowing you to easily switch between filters.

### Understanding Card Tags

Each card displays taxonomy tags showing which topic it covers:
- **MCAT cards:** Show the foundational concept and content category (e.g., "Structure and function of proteins")
- **USMLE cards:** Show the organ system and topic (e.g., "Biochemistry and Molecular Biology")

Tags help you identify which exam topics each card addresses, making it easier to organize your study.

### 5. Import to Anki

1. Open Anki
2. File → Import
3. Select your downloaded .apkg file
4. Cards appear in your deck!

## What's Next?

- [Topic-Based Generation](./topic-input.md)
- [Supported File Formats](./file-formats.md)
- [Understanding Card Types](./card-types.md)
- [Customizing Generation](./customization.md)
- [CLI Usage](./cli-guide.md)
