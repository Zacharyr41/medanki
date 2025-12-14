import { test, expect } from './fixtures'

test.describe('Full User Journey', () => {
  test('complete flow: upload -> processing -> preview -> download', async ({ page, sampleMdPath }) => {
    await page.route('**/api/upload', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ jobId: 'e2e-job-001' }),
      })
    })

    await page.addInitScript(() => {
      const originalWebSocket = window.WebSocket
      let messageIndex = 0
      const messages = [
        { type: 'progress', progress: 10, stage: 'parsing', details: { message: 'Parsing document...' } },
        { type: 'progress', progress: 30, stage: 'chunking', details: { message: 'Chunking content...' } },
        { type: 'progress', progress: 50, stage: 'embedding', details: { message: 'Generating embeddings...' } },
        { type: 'progress', progress: 70, stage: 'generating', details: { message: 'Creating flashcards...' } },
        { type: 'progress', progress: 90, stage: 'packaging', details: { message: 'Building deck...' } },
        { type: 'progress', progress: 100, stage: 'complete', details: {} },
        { type: 'complete', result: { deckId: 'e2e-deck-001', cardCount: 20 } },
      ]

      window.WebSocket = class MockWebSocket extends originalWebSocket {
        constructor(url: string) {
          super(url)
          const sendMessages = () => {
            if (messageIndex < messages.length) {
              this.dispatchEvent(
                new MessageEvent('message', {
                  data: JSON.stringify(messages[messageIndex]),
                })
              )
              messageIndex++
              setTimeout(sendMessages, 300)
            }
          }
          setTimeout(sendMessages, 100)
        }
      } as typeof WebSocket
    })

    await page.route('**/api/decks/*', async (route) => {
      if (route.request().url().includes('/download')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/octet-stream',
          headers: {
            'Content-Disposition': 'attachment; filename="medical-notes.apkg"',
          },
          body: Buffer.from('mock apkg deck content'),
        })
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'e2e-deck-001',
            name: 'Medical Notes',
            cardCount: 20,
            cards: [
              { id: '1', type: 'cloze', front: 'ACS includes {{c1::unstable angina}}...', back: 'unstable angina' },
              { id: '2', type: 'vignette', front: 'A patient presents with chest pain...', back: 'STEMI' },
              { id: '3', type: 'cloze', front: '{{c1::Aspirin}} 325mg is given...', back: 'Aspirin' },
            ],
            statistics: {
              clozeCount: 12,
              vignetteCount: 8,
            },
          }),
        })
      }
    })

    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Generate Flashcards' })).toBeVisible()

    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(sampleMdPath)
    await expect(page.getByText('sample.md')).toBeVisible()

    const examSelect = page.getByLabel('Exam')
    await examSelect.selectOption('USMLE Step 1')

    await page.getByRole('button', { name: 'Generate Cards' }).click()

    await expect(page).toHaveURL(/\/processing\/e2e-job-001/, { timeout: 10000 })

    await expect(page).toHaveURL(/\/download\/e2e-deck-001/, { timeout: 30000 })

    await expect(page.getByText(/20|cards/i)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/cloze|vignette/i).first()).toBeVisible()

    const downloadButton = page.getByRole('button', { name: /download/i })
    await expect(downloadButton).toBeVisible({ timeout: 10000 })

    const downloadPromise = page.waitForEvent('download')
    await downloadButton.click()
    const download = await downloadPromise

    expect(download.suggestedFilename()).toMatch(/\.apkg$/)

    const uploadLink = page.getByRole('link', { name: /upload.*another|new|start/i })
    if (await uploadLink.isVisible()) {
      await uploadLink.click()
      await expect(page).toHaveURL('/')
      await expect(page.getByRole('heading', { name: 'Generate Flashcards' })).toBeVisible()
    }
  })

  test('handles network errors gracefully', async ({ page, sampleMdPath }) => {
    await page.goto('/')

    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(sampleMdPath)

    await page.route('**/api/upload', async (route) => {
      await route.abort('failed')
    })

    await page.getByRole('button', { name: 'Generate Cards' }).click()

    await expect(page.getByText(/failed|error|try again/i)).toBeVisible({ timeout: 10000 })
  })

  test('validates file before upload', async ({ page, tempDir }) => {
    const fs = await import('fs')
    const path = await import('path')
    const invalidPath = path.join(tempDir, 'invalid.txt')
    fs.writeFileSync(invalidPath, 'This is not a valid file type')

    await page.goto('/')

    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(invalidPath)

    await expect(page.getByText(/unsupported|invalid|type/i)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Generate Cards' })).toBeDisabled()
  })
})
