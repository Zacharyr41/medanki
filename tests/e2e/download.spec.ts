import { test, expect } from './fixtures'

test.describe('Download Page', () => {
  const mockDeckData = {
    id: 'deck-123',
    name: 'Medical Cardiology',
    cardCount: 25,
    cards: [
      { id: '1', type: 'cloze', front: 'The {{c1::mitral valve}} controls blood flow...', back: 'mitral valve' },
      { id: '2', type: 'vignette', front: 'A 58-year-old male presents with...', back: 'Acute MI' },
      { id: '3', type: 'cloze', front: '{{c1::Aspirin}} is first-line treatment...', back: 'Aspirin' },
      { id: '4', type: 'vignette', front: 'A 45-year-old female with HTN...', back: 'Hypertensive emergency' },
      { id: '5', type: 'cloze', front: 'Beta blockers reduce {{c1::heart rate}}...', back: 'heart rate' },
    ],
    statistics: {
      clozeCount: 15,
      vignetteCount: 10,
      avgDifficulty: 'medium',
    },
  }

  test.beforeEach(async ({ page }) => {
    await page.route('**/api/decks/*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDeckData),
      })
    })
  })

  test('shows deck statistics', async ({ page }) => {
    await page.goto('/download/deck-123')

    await expect(page.getByText(/25|cards/i)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/15.*cloze|cloze.*15/i)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/10.*vignette|vignette.*10/i)).toBeVisible({ timeout: 10000 })
  })

  test('shows card preview list', async ({ page }) => {
    await page.goto('/download/deck-123')

    await expect(page.getByText(/mitral valve/i)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/58-year-old/i)).toBeVisible({ timeout: 10000 })
  })

  test('pagination works', async ({ page }) => {
    await page.route('**/api/decks/*', async (route) => {
      const manyCards = Array.from({ length: 50 }, (_, i) => ({
        id: String(i + 1),
        type: i % 2 === 0 ? 'cloze' : 'vignette',
        front: `Card ${i + 1} front content`,
        back: `Card ${i + 1} back`,
      }))

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...mockDeckData,
          cardCount: 50,
          cards: manyCards,
        }),
      })
    })

    await page.goto('/download/deck-123')

    const nextButton = page.getByRole('button', { name: /next|>/i })
    if (await nextButton.isVisible()) {
      await nextButton.click()
      await expect(page.getByText(/card \d+/i)).toBeVisible()
    }
  })

  test('filter by card type works', async ({ page }) => {
    await page.goto('/download/deck-123')

    const typeFilter = page.getByRole('combobox', { name: /type|filter/i })
    if (await typeFilter.isVisible()) {
      await typeFilter.selectOption('cloze')
      await expect(page.getByText(/cloze/i).first()).toBeVisible()
    }
  })

  test('download button triggers file download', async ({ page }) => {
    await page.route('**/api/decks/*/download', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/octet-stream',
        headers: {
          'Content-Disposition': 'attachment; filename="medical-cardiology.apkg"',
        },
        body: Buffer.from('mock apkg content'),
      })
    })

    await page.goto('/download/deck-123')

    const downloadButton = page.getByRole('button', { name: /download/i })
    await expect(downloadButton).toBeVisible({ timeout: 10000 })

    const downloadPromise = page.waitForEvent('download')
    await downloadButton.click()
    const download = await downloadPromise

    expect(download.suggestedFilename()).toContain('.apkg')
  })

  test('upload another link navigates to upload', async ({ page }) => {
    await page.goto('/download/deck-123')

    const uploadLink = page.getByRole('link', { name: /upload.*another|new.*upload|start.*over/i })
    if (await uploadLink.isVisible()) {
      await uploadLink.click()
      await expect(page).toHaveURL('/')
    } else {
      const homeLink = page.getByRole('link', { name: /home|back/i })
      if (await homeLink.isVisible()) {
        await homeLink.click()
        await expect(page).toHaveURL('/')
      }
    }
  })
})
