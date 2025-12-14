# Tutorial: Create Your First Deck

**Time:** 10 minutes
**Difficulty:** Beginner

In this tutorial, you'll create a flashcard deck from a sample PDF.

## Prerequisites

- MedAnki running locally or access to hosted version
- Anki installed on your computer

## Step 1: Prepare Your Material

For this tutorial, use any medical PDF you have available, such as:
- A lecture slide deck
- A textbook chapter
- Study notes exported to PDF

Ideal starting material:
- 2-10 pages in length
- Clear, readable text
- Focused on one topic

## Step 2: Open MedAnki

1. Open MedAnki in your browser (http://localhost:5173)
2. You should see the upload interface

## Step 3: Upload Your File

1. Drag your PDF onto the upload area, OR
2. Click the upload area to browse for your file
3. You should see the file name and size displayed

If you see an error:
- Ensure the file is a PDF or Markdown file
- Check that the file is under 50MB

## Step 4: Configure Settings

For your first deck, use these recommended settings:

| Option | Setting | Why |
|--------|---------|-----|
| **Exam** | MCAT or USMLE Step 1 | Matches most basic science content |
| **Card Types** | Both Cloze and Vignette | See both card types in action |
| **Max Cards** | 3 | Manageable output for review |

## Step 5: Generate Cards

1. Click "Generate Flashcards"
2. Watch the progress indicator:
   - **Ingesting** - Extracting text from your file
   - **Chunking** - Breaking into study-sized pieces
   - **Classifying** - Matching to exam topics
   - **Generating** - Creating flashcards with AI
   - **Exporting** - Building Anki deck

Processing time depends on file size and content density.

## Step 6: Preview Your Cards

Once complete, you'll see a preview of generated cards.

**Review for:**
- Factual accuracy
- Card clarity
- Appropriate difficulty

**Example Cloze Card:**
> The {{c1::sinoatrial (SA) node}} is the primary pacemaker of the heart, located in the {{c2::right atrium}}.

**Example Vignette Card:**
> A 45-year-old woman presents with palpitations...
> Which of the following is the most likely diagnosis?

## Step 7: Download Your Deck

1. Click "Download Deck"
2. Save the .apkg file to a known location
3. Note the file name for import

## Step 8: Import to Anki

1. Open Anki
2. Click File → Import
3. Select your downloaded .apkg file
4. Click "Import"
5. You'll see a confirmation of imported cards

## Step 9: Find Your Cards

1. Click "Browse" in Anki
2. Look for your new deck in the left sidebar
3. Click the deck to see all cards
4. Review the cards and their tags

## Step 10: Start Studying!

1. Return to the main Anki screen
2. Click your new deck
3. Click "Study Now"
4. Review your cards!

## What You Learned

- How to upload files to MedAnki
- How to configure generation options
- How to preview and download cards
- How to import into Anki
- How to start studying

## Troubleshooting

### Cards won't generate
- Ensure your file contains readable text
- Check that the file isn't password-protected
- Try a smaller file

### Poor card quality
- Use higher-quality source material
- Increase max cards for more options
- Choose the appropriate exam type

### Import fails in Anki
- Ensure you have the latest Anki version
- Check that the .apkg file downloaded completely
- Try downloading again

## Next Steps

- [Process multiple files at once](./batch-processing.md)
- [Learn to optimize your cards](./optimizing-cards.md)
- [Explore customization options](../user-guide/customization.md)
