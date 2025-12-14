# Frequently Asked Questions

## General Questions

### What is MedAnki?

MedAnki is an AI-powered tool that converts medical study materials (PDFs, Markdown files) into high-quality Anki flashcards, automatically tagged against MCAT and USMLE content outlines.

### How does it differ from regular Anki?

MedAnki generates cards from your source material. Anki is the spaced repetition software where you study those cards. MedAnki creates .apkg files that you import into Anki.

### Is my data secure?

Your uploaded files are processed and not stored permanently. Generated cards are not retained after your session ends.

### What exams does MedAnki support?

- MCAT
- USMLE Step 1
- USMLE Step 2

The exam selection affects tagging and card style but you can use generated cards for any purpose.

## File Questions

### What file formats are supported?

- PDF (.pdf)
- Markdown (.md)

### What's the maximum file size?

50MB per file.

### Can I process multiple files at once?

Yes, using the CLI. The web interface currently processes one file at a time.

### Why won't my PDF upload?

Common causes:
- File exceeds 50MB
- File is corrupted
- File is password-protected
- Browser blocking the upload

### How should I format my Markdown files?

Use standard CommonMark syntax:
- Headers (##, ###) for organization
- Paragraphs for content
- Lists for related items
- Tables for structured data

## Card Generation Questions

### How many cards will be generated?

Depends on your content and settings:
- `max_cards` setting controls cards per chunk
- Longer content produces more chunks
- Complex content may produce more cards

### Why are some cards low quality?

Card quality depends on source material quality. Best results come from:
- Clear, well-written source text
- Explicit statements of facts
- Well-organized content

### Can I control what topics get cards?

Not directly. MedAnki processes all content in your file. To focus on specific topics, upload only that content.

### How long does generation take?

Typical times:
- 1-5 pages: 30 seconds - 1 minute
- 5-20 pages: 1-3 minutes
- 20+ pages: 3-10 minutes

Times vary based on content complexity and server load.

### Why did generation fail?

Common causes:
- File couldn't be parsed
- Content was too short or unclear
- Server timeout for very large files
- Network issues

Try again with a smaller or simpler file.

## Card Type Questions

### When should I use cloze vs. vignette cards?

**Use cloze for:**
- Memorizing facts
- Learning terminology
- Numerical values
- Quick recall practice

**Use vignette for:**
- Clinical reasoning
- Applying knowledge
- USMLE-style practice
- Differential diagnosis

### Can I generate only one card type?

Yes. Uncheck the card type you don't want before generating.

### Why do vignettes take longer to generate?

Vignettes are more complex:
- Require clinical context creation
- Need plausible distractors
- Include explanations
- Follow USMLE formatting

## Anki Questions

### How do I import the .apkg file?

1. Open Anki
2. File → Import
3. Select the .apkg file
4. Click Import

### Where do my cards appear in Anki?

In a new deck named after your file or "MedAnki" if batch processed.

### How do I find specific cards?

Use Anki's Browse feature:
- Press B or click Browse
- Search by tag, deck, or content
- Filter by card type

### Can I edit cards after importing?

Yes. In Anki:
1. Browse → Select card
2. Press E to edit
3. Modify text, add media, change tags
4. Close editor to save

### Will updates overwrite my edits?

No. Each import creates new notes. Your edits to existing cards are preserved.

## Troubleshooting

### Generation hangs at a certain percentage

- Wait up to 5 minutes before refreshing
- Large files may take longer at certain stages
- If stuck, try a smaller file

### Cards have formatting issues

- Check source file formatting
- Complex tables may not convert well
- Special characters might display incorrectly

### Tags aren't appearing in Anki

- Ensure you imported the .apkg file
- Check Anki's tag sidebar
- Try clicking "Check Database" in Anki

### Downloaded file won't open

- Ensure you have Anki installed
- Try downloading again
- Check for corrupted download

## Performance Tips

### For best generation quality

1. Use well-organized source material
2. Include context with facts
3. Use clear, explicit language
4. Keep files focused (one topic/chapter)

### For fastest processing

1. Use smaller files (under 10 pages)
2. Choose one card type
3. Set lower max cards
4. Use Markdown instead of PDF

### For optimal Anki study

1. Review cards shortly after generating
2. Suspend low-quality cards
3. Edit for personal learning style
4. Use tags for focused study

## Getting Help

### I found a bug

Please report issues at the MedAnki repository with:
- What you were doing
- What you expected
- What happened instead
- Browser/OS information

### I have a feature request

Open an issue on the repository describing:
- The feature you'd like
- Why it would be useful
- How you envision it working

### I need more help

- Check the [User Guide](./getting-started.md)
- Review the [Tutorials](../tutorials/README.md)
- Search existing issues on the repository
