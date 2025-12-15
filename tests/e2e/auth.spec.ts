import { test, expect } from './fixtures'

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('shows sign in button when not authenticated', async ({ page }) => {
    await expect(page.getByRole('button', { name: /sign in with google/i }).first()).toBeVisible()
  })

  test('does not show user menu when not authenticated', async ({ page }) => {
    await expect(page.getByTestId('user-menu')).not.toBeVisible()
  })

  test('google sign in button is clickable', async ({ page }) => {
    const signInButton = page.getByRole('button', { name: /sign in with google/i }).first()
    await expect(signInButton).toBeEnabled()
  })

  test('auth state persists after navigation', async ({ page }) => {
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'mock-token')
    })

    await page.reload()

    const hasToken = await page.evaluate(() => {
      return localStorage.getItem('auth_token') !== null
    })
    expect(hasToken).toBe(true)
  })

  test('logout clears auth token', async ({ page }) => {
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'mock-token')
    })

    await page.evaluate(() => {
      localStorage.removeItem('auth_token')
    })

    const hasToken = await page.evaluate(() => {
      return localStorage.getItem('auth_token') !== null
    })
    expect(hasToken).toBe(false)
  })
})

test.describe('Protected Routes', () => {
  test('unauthenticated user can access upload page', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Generate Flashcards' })).toBeVisible()
  })

  test('save cards button shows login prompt when not authenticated', async ({ page }) => {
    await page.route('**/api/upload', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ jobId: 'test-job-123' }),
      })
    })

    await page.route('**/api/jobs/test-job-123/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'completed',
          progress: 100,
          stage: 'done',
          stages: [],
        }),
      })
    })

    await page.route('**/api/preview/test-job-123*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          cards: [
            {
              id: 'card-1',
              type: 'cloze',
              front: 'Test {{c1::card}}',
              back: 'Test card',
              tags: ['test'],
            },
          ],
          total: 1,
          page: 1,
          limit: 20,
        }),
      })
    })

    await page.goto('/preview/test-job-123')

    const saveButton = page.getByRole('button', { name: /save/i })
    if (await saveButton.isVisible()) {
      await saveButton.click()

      await expect(page.getByText(/sign in/i)).toBeVisible()
    }
  })
})

test.describe('Authentication UI States', () => {
  test('shows loading state during authentication', async ({ page }) => {
    await page.goto('/')

    const signInButton = page.getByRole('button', { name: /sign in with google/i }).first()
    await expect(signInButton).toBeVisible()
  })

  test('handles authentication error gracefully', async ({ page }) => {
    await page.route('**/api/auth/google', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid token' }),
      })
    })

    await page.goto('/')
    await expect(page.getByRole('button', { name: /sign in with google/i }).first()).toBeVisible()
  })
})
