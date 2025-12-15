# Topic-Based Card Generation

MedAnki now supports generating flashcards directly from topic descriptions, without needing to upload a file. This is perfect for studying specific concepts or topics you want to learn.

## How It Works

Instead of uploading lecture notes or textbooks, you can simply describe what you want to study. MedAnki uses AI to generate relevant, high-quality flashcards based on your topic description.

## Using Topic Input

### 1. Select Input Mode

On the upload page, you'll see two tabs:
- **Upload File** - Traditional file-based generation
- **Describe Topics** - Free-form topic description

Click "Describe Topics" to switch to topic input mode.

### 2. Describe Your Topic

Enter a description of what you want to study. Be as specific or broad as you like:

**Examples:**
- "I want to study cardiac electrophysiology, focusing on action potentials and arrhythmias"
- "Help me learn pharmacology of beta blockers"
- "Study the renin-angiotensin-aldosterone system"
- "Learn about renal physiology for USMLE Step 1"

**Tips for better results:**
- Include the specific topic or system you're studying
- Mention key concepts you want to cover
- Specify your target exam if relevant
- Be descriptive but concise (max 2000 characters)

### 3. Configure Options

- **Target Exam:** Choose MCAT or USMLE Step 1 to tailor card content and difficulty
- **Card Types:** Select cloze deletions, clinical vignettes, or both
- **Total Cards:** Set how many cards to generate (1-100, default 20)

### 4. Generate Cards

Click "Generate Flashcards" to start generation. Topic-based generation is typically faster than file-based since it skips document ingestion and chunking.

## Topic vs File Input

| Feature | File Upload | Topic Description |
|---------|-------------|-------------------|
| Source Material | Your uploaded documents | AI-generated content |
| Processing Time | Longer (ingestion + chunking) | Faster (direct generation) |
| Content Accuracy | Based on your specific materials | General medical knowledge |
| Best For | Studying specific lecture content | Learning new topics |
| Customization | Tied to uploaded content | Flexible topic scope |

## When to Use Topic Input

Topic input is ideal when:
- You want to learn a new topic from scratch
- You don't have specific study materials
- You want a quick review of a subject
- You're exploring concepts before deep diving

File upload is better when:
- You have specific lecture notes or textbooks
- You want cards based on exact wording from your materials
- You need to study content from a specific course

## Total Cards Setting

The "Total Cards" option (1-100) controls the total number of cards generated:

- **For topic input:** This is the exact number of cards requested
- **For file upload:** Cards are distributed across content chunks

Lower values (5-10) are good for focused review; higher values (50-100) provide comprehensive coverage.
