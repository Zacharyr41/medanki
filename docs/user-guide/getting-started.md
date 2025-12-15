# Getting Started with MedAnki

MedAnki converts your medical study materials into high-quality Anki flashcards, automatically tagged against MCAT and USMLE taxonomies.

## Quick Start (5 minutes)

### 1. Access MedAnki

**Web Interface:** Navigate to http://localhost:5173 (or your deployed URL)

**CLI:** Install with `pip install medanki-cli`

### 2. Upload Your First File

Supported formats:
- **PDF:** Textbooks, lecture slides, study guides
- **Markdown:** Notes, summaries
- **TXT:** Plain text files
- **DOCX:** Word documents

Simply drag and drop your file onto the upload area, or click to browse.

### 3. Configure Options

- **Target Exam:** Choose MCAT or USMLE Step 1
- **Card Types:** Cloze deletions, clinical vignettes, or both
- **Max Cards per Chunk:** How many cards to generate per content section (1-50)

### 4. Generate and Download

Click "Generate Flashcards" and wait for processing. You'll see:
- Real-time progress updates
- Stage-by-stage breakdown
- Estimated time remaining

Once complete, preview your cards and download the .apkg file.

### 5. Import to Anki

1. Open Anki
2. File → Import
3. Select your downloaded .apkg file
4. Cards appear in your deck!

## What's Next?

- [Supported File Formats](./file-formats.md)
- [Understanding Card Types](./card-types.md)
- [Customizing Generation](./customization.md)
- [CLI Usage](./cli-guide.md)
