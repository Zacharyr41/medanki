# Tutorial: Optimizing Your Cards

**Time:** 20 minutes
**Difficulty:** Intermediate

Learn to review, edit, and optimize generated flashcards in Anki for maximum study efficiency.

## Prerequisites

- Cards imported into Anki
- Basic familiarity with Anki interface

## Step 1: Initial Review

After importing your deck, do a quick review pass:

1. Open Anki
2. Click "Browse"
3. Select your new deck
4. Scan through cards looking for issues

**Common issues to spot:**
- Factual errors
- Unclear wording
- Overly complex cards
- Duplicate content
- Missing context

## Step 2: Mark Problem Cards

As you review, flag cards that need attention:

1. Select a card
2. Press `Ctrl+K` (Windows) or `Cmd+K` (Mac) to mark
3. Or right-click → Mark Note

Marked cards show a star for easy finding later.

## Step 3: Edit Cloze Cards

### Simplify Overcrowded Cards

**Before:**
> The {{c1::renin-angiotensin-aldosterone system}} (RAAS) is activated by {{c2::decreased renal perfusion}}, causing {{c3::angiotensin II}} release, leading to {{c4::vasoconstriction}} and {{c5::aldosterone}} secretion.

**After (split into 2 cards):**

Card 1:
> The {{c1::renin-angiotensin-aldosterone system}} (RAAS) is activated by {{c2::decreased renal perfusion}}.

Card 2:
> Angiotensin II causes {{c1::vasoconstriction}} and stimulates {{c2::aldosterone}} secretion.

### Fix Vague Deletions

**Before:**
> {{c1::This hormone}} regulates calcium levels.

**After:**
> {{c1::Parathyroid hormone (PTH)}} regulates calcium levels by increasing bone resorption.

### Ensure Answer Specificity

**Before:**
> The heart has {{c1::four}} chambers.

**After:**
> The heart has {{c1::four chambers}}: two atria and two ventricles.

## Step 4: Edit Vignette Cards

### Add Missing Context

If a vignette stem is unclear, expand it:

**Before:**
> A patient presents with chest pain.

**After:**
> A 55-year-old man with hypertension and diabetes presents with crushing substernal chest pain radiating to his left arm for 2 hours.

### Improve Distractors

Ensure wrong answers are plausible but distinguishable:

**Weak distractors:**
- A. Myocardial infarction
- B. Broken leg
- C. Headache

**Strong distractors:**
- A. Myocardial infarction
- B. Pulmonary embolism
- C. Aortic dissection

### Clarify Explanations

Ensure the explanation teaches, not just states the answer:

**Before:**
> C is correct.

**After:**
> C is correct. ST-segment elevation in leads V1-V4 indicates anterior wall involvement. The clinical presentation with risk factors is classic for STEMI. PE would show right heart strain pattern, and dissection typically shows tearing pain with blood pressure differential.

## Step 5: Suspend Low-Quality Cards

For cards that aren't worth fixing:

1. Select the card
2. Press `@` or right-click → Toggle Suspend
3. Suspended cards appear yellow and won't appear in reviews

**When to suspend:**
- Trivial or obvious content
- Duplicate information
- Content you already know well
- Cards requiring major rewriting

## Step 6: Delete Truly Useless Cards

For cards with no value:

1. Select the card(s)
2. Press `Ctrl+Delete` (Windows) or `Cmd+Delete` (Mac)
3. Confirm deletion

**Warning:** Deletion is permanent. When in doubt, suspend instead.

## Step 7: Add Personal Notes

Enhance cards with your own context:

1. Edit the card
2. Add to the Extra field (if available)
3. Include mnemonics, related concepts, or personal connections

**Example addition:**
> *Mnemonic: "RAA System = Really Angry Arteries" - everything constricts*

## Step 8: Reorganize with Tags

### Add Custom Tags

1. Select cards
2. Press `Ctrl+Shift+T` (Windows) or `Cmd+Shift+T` (Mac)
3. Add your tags

**Useful custom tags:**
- `high-yield` - Important for exams
- `confusing` - Need extra review
- `clinical` - Clinically relevant
- `first-aid` - Covered in First Aid

### Create Filtered Decks

Study specific topics:

1. Tools → Create Filtered Deck
2. Enter search: `tag:high-yield -is:suspended`
3. Set card limit
4. Study focused content

## Step 9: Establish a Review Routine

### Initial Pass (Day 1)
1. Review all new cards
2. Suspend obvious duplicates
3. Mark cards needing edits

### Editing Pass (Day 2)
1. Find marked cards: `tag:marked`
2. Edit each card
3. Unmark when fixed

### Ongoing Maintenance
1. Edit cards during reviews when you spot issues
2. Suspend cards that repeatedly cause confusion
3. Add context when you learn related material

## Quality Checklist

Before finishing optimization, verify:

- [ ] No factual errors
- [ ] Each card tests one concept
- [ ] Cloze answers are 1-4 words
- [ ] Vignettes have plausible distractors
- [ ] Explanations are educational
- [ ] Cards are appropriately tagged
- [ ] Duplicates are suspended

## Keyboard Shortcuts Reference

| Action | Windows | Mac |
|--------|---------|-----|
| Edit | E | E |
| Mark | Ctrl+K | Cmd+K |
| Suspend | @ | @ |
| Delete | Ctrl+Del | Cmd+Del |
| Add tag | Ctrl+Shift+T | Cmd+Shift+T |
| Browse | B | B |

## Common Patterns to Fix

### Pattern: Answer Too Long

**Problem:** {{c1::the mitochondria is the powerhouse of the cell}}

**Fix:** The {{c1::mitochondria}} is the powerhouse of the cell.

### Pattern: Missing Context

**Problem:** {{c1::Epinephrine}} is released during stress.

**Fix:** {{c1::Epinephrine}} is released from the adrenal medulla during the fight-or-flight response.

### Pattern: Testing Recall vs. Recognition

**Problem:** Epinephrine is a(n) {{c1::hormone/neurotransmitter}}.

**Fix:** Epinephrine functions as both a {{c1::hormone}} when released from the adrenal medulla and a {{c2::neurotransmitter}} in the sympathetic nervous system.

## Next Steps

- [Learn about card types in depth](../user-guide/card-types.md)
- [Explore taxonomy and tagging](../user-guide/taxonomy.md)
- [Read the FAQ](../user-guide/faq.md)
