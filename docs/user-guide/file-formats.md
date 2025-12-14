# Supported File Formats

MedAnki supports multiple file formats for maximum flexibility with your study materials.

## PDF Files

**Best for:** Textbooks, lecture slides, study guides, published materials

### Supported Features
- Text extraction from native PDFs
- OCR for scanned documents
- Multi-column layout detection
- Table content extraction

### Best Practices
- Use native PDF files (not scanned images) when possible for best text quality
- Ensure text is selectable in your PDF reader
- Split very large files (>100 pages) into smaller sections for better processing

### File Size Limit
Maximum file size: **50MB**

### Common Issues

| Issue | Solution |
|-------|----------|
| Text appears garbled | PDF may use non-standard fonts; try re-exporting from source |
| Missing content | Scanned PDFs may need OCR; ensure quality scan |
| Tables not extracted | Complex tables may be simplified; review generated cards |

## Markdown Files

**Best for:** Personal notes, summaries, organized content

### Supported Features
- Full CommonMark syntax
- Headers for content organization
- Lists and bullet points
- Code blocks (for biochemistry pathways, etc.)
- Tables
- Bold/italic emphasis

### Best Practices
- Use headers (##, ###) to organize content by topic
- Keep paragraphs focused on single concepts
- Use bullet points for lists of related items
- Include context with your notes (don't assume prior knowledge)

### Example Structure

```markdown
## Cardiovascular System

### Cardiac Cycle

The cardiac cycle consists of two main phases:
- **Systole:** Ventricular contraction, blood ejection
- **Diastole:** Ventricular relaxation, filling

### Blood Pressure Regulation

The renin-angiotensin-aldosterone system (RAAS) regulates blood pressure through:
1. Renin release from juxtaglomerular cells
2. Angiotensin II formation
3. Aldosterone secretion
```

## Preparing Files for Best Results

### General Tips

1. **Focus content:** Include only material you want to learn
2. **Provide context:** Ensure content is self-explanatory
3. **Remove distractions:** Remove advertisements, page numbers, headers/footers if possible
4. **Organize logically:** Group related concepts together

### Content Length Guidelines

| Content Type | Recommended Length |
|--------------|-------------------|
| Single topic | 1-3 pages |
| Chapter review | 5-15 pages |
| Course summary | 20-50 pages |

Longer files will be automatically chunked into smaller sections for processing.

## Troubleshooting

### PDF won't upload
- Check file size (max 50MB)
- Ensure file extension is `.pdf`
- Try re-saving from original source

### Markdown formatting issues
- Use standard CommonMark syntax
- Avoid HTML embedded in Markdown
- Ensure file extension is `.md`

### Poor card quality
- Provide more context in source material
- Use clearer, more explicit language
- Break complex topics into smaller sections
