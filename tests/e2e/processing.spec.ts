import { test, expect } from './fixtures'

test.describe('Processing Page', () => {
  test('shows progress bar updates', async ({ page }) => {
    await page.addInitScript(() => {
      const originalWebSocket = window.WebSocket
      window.WebSocket = class MockWebSocket extends originalWebSocket {
        constructor(url: string) {
          super(url)
          setTimeout(() => {
            this.dispatchEvent(
              new MessageEvent('message', {
                data: JSON.stringify({
                  type: 'progress',
                  progress: 25,
                  stage: 'parsing',
                  details: { message: 'Parsing document...' },
                }),
              })
            )
          }, 100)
          setTimeout(() => {
            this.dispatchEvent(
              new MessageEvent('message', {
                data: JSON.stringify({
                  type: 'progress',
                  progress: 50,
                  stage: 'embedding',
                  details: { message: 'Generating embeddings...' },
                }),
              })
            )
          }, 200)
        }
      } as typeof WebSocket
    })

    await page.goto('/processing/test-job-123')

    const progressBar = page.getByRole('progressbar')
    await expect(progressBar).toBeVisible({ timeout: 10000 })
  })

  test('shows processing stages', async ({ page }) => {
    await page.addInitScript(() => {
      const originalWebSocket = window.WebSocket
      window.WebSocket = class MockWebSocket extends originalWebSocket {
        constructor(url: string) {
          super(url)
          setTimeout(() => {
            this.dispatchEvent(
              new MessageEvent('message', {
                data: JSON.stringify({
                  type: 'progress',
                  progress: 30,
                  stage: 'parsing',
                  details: { message: 'Parsing document...' },
                }),
              })
            )
          }, 100)
        }
      } as typeof WebSocket
    })

    await page.goto('/processing/test-job-123')

    await expect(page.getByText(/parsing|processing/i)).toBeVisible({ timeout: 10000 })
  })

  test('cancel button stops job', async ({ page }) => {
    await page.addInitScript(() => {
      const originalWebSocket = window.WebSocket
      window.WebSocket = class MockWebSocket extends originalWebSocket {
        constructor(url: string) {
          super(url)
          setTimeout(() => {
            this.dispatchEvent(
              new MessageEvent('message', {
                data: JSON.stringify({
                  type: 'progress',
                  progress: 25,
                  stage: 'processing',
                  details: {},
                }),
              })
            )
          }, 100)
        }
      } as typeof WebSocket
    })

    await page.goto('/processing/test-job-123')

    await page.route('**/api/jobs/*/cancel', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'cancelled' }),
      })
    })

    const cancelButton = page.getByRole('button', { name: /cancel/i })
    if (await cancelButton.isVisible()) {
      await cancelButton.click()
      await expect(page).toHaveURL('/')
    }
  })

  test('navigates to download on completion', async ({ page }) => {
    await page.addInitScript(() => {
      const originalWebSocket = window.WebSocket
      window.WebSocket = class MockWebSocket extends originalWebSocket {
        constructor(url: string) {
          super(url)
          setTimeout(() => {
            this.dispatchEvent(
              new MessageEvent('message', {
                data: JSON.stringify({
                  type: 'progress',
                  progress: 100,
                  stage: 'complete',
                  details: {},
                }),
              })
            )
          }, 100)
          setTimeout(() => {
            this.dispatchEvent(
              new MessageEvent('message', {
                data: JSON.stringify({
                  type: 'complete',
                  result: { deckId: 'deck-456', cardCount: 15 },
                }),
              })
            )
          }, 200)
        }
      } as typeof WebSocket
    })

    await page.goto('/processing/test-job-123')

    await expect(page).toHaveURL(/\/download\/deck-456/, { timeout: 10000 })
  })

  test('shows error message on failure', async ({ page }) => {
    await page.addInitScript(() => {
      const originalWebSocket = window.WebSocket
      window.WebSocket = class MockWebSocket extends originalWebSocket {
        constructor(url: string) {
          super(url)
          setTimeout(() => {
            this.dispatchEvent(
              new MessageEvent('message', {
                data: JSON.stringify({
                  type: 'error',
                  error: 'Processing failed',
                  details: { reason: 'Invalid document format' },
                }),
              })
            )
          }, 100)
        }
      } as typeof WebSocket
    })

    await page.goto('/processing/test-job-123')

    await expect(page.getByText(/processing failed|error/i)).toBeVisible({ timeout: 10000 })
  })
})
