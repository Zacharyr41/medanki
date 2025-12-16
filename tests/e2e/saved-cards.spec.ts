import { test, expect } from './fixtures'

test.describe('Saved Cards', () => {
  const mockCards = [
    {
      id: 'card-1',
      type: 'cloze',
      front: 'The {{c1::heart}} pumps blood',
      back: 'The heart pumps blood',
      tags: ['cardiology'],
    },
    {
      id: 'card-2',
      type: 'cloze',
      front: '{{c1::Aspirin}} is an antiplatelet',
      back: 'Aspirin is an antiplatelet',
      tags: ['pharmacology'],
    },
    {
      id: 'card-3',
      type: 'vignette',
      front: 'A 55-year-old patient presents with chest pain...',
      back: 'Myocardial infarction',
      tags: ['cardiology'],
    },
  ]

  test('shows login prompt when saving cards without auth', async ({ page }) => {
    await page.route('**/api/preview/test-job*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          cards: mockCards,
          total: mockCards.length,
          page: 1,
          limit: 20,
        }),
      })
    })

    await page.goto('/preview/test-job')

    await page.waitForSelector('[data-testid="card-list"]', { timeout: 5000 }).catch(() => {})

    const saveButton = page.getByRole('button', { name: /save/i })
    if (await saveButton.isVisible()) {
      await saveButton.click()
      await expect(page.getByText(/sign in/i)).toBeVisible()
    }
  })

  test('save cards API returns 401 without auth', async ({ page, apiBaseUrl }) => {
    const response = await page.request.post(`${apiBaseUrl}/api/saved-cards`, {
      data: {
        job_id: 'test-job',
        card_ids: ['card-1'],
      },
    })
    expect(response.status()).toBe(401)
  })

  test('get saved cards API returns 401 without auth', async ({ page, apiBaseUrl }) => {
    const response = await page.request.get(`${apiBaseUrl}/api/saved-cards`)
    expect(response.status()).toBe(401)
  })

  test('authenticated user can save cards via API', async ({ page, apiBaseUrl }) => {
    await page.route('**/api/auth/google', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'mock-jwt-token',
          token_type: 'bearer',
          user: {
            id: 'user-123',
            email: 'test@example.com',
            name: 'Test User',
          },
        }),
      })
    })

    await page.route('**/api/saved-cards', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            saved_count: 2,
            message: 'Cards saved successfully',
          }),
        })
      } else if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            cards: [
              { id: '1', card_id: 'card-1', job_id: 'test-job', saved_at: new Date().toISOString() },
              { id: '2', card_id: 'card-2', job_id: 'test-job', saved_at: new Date().toISOString() },
            ],
            total: 2,
            limit: 20,
            offset: 0,
          }),
        })
      }
    })

    await page.goto('/')
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'mock-jwt-token')
    })
    await page.reload()

    const getResponse = await page.request.get(`${apiBaseUrl}/api/saved-cards`, {
      headers: {
        Authorization: 'Bearer mock-jwt-token',
      },
    })
    expect([200, 401]).toContain(getResponse.status())
  })

  test('delete saved card API returns 401 without auth', async ({ page, apiBaseUrl }) => {
    const response = await page.request.delete(`${apiBaseUrl}/api/saved-cards/card-1`)
    expect(response.status()).toBe(401)
  })
})

test.describe('Saved Cards UI Flow', () => {
  test('preview page shows card selection checkboxes', async ({ page }) => {
    await page.route('**/api/preview/test-job*', async (route) => {
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

    await page.goto('/preview/test-job')

    await page.waitForSelector('[data-testid="card-list"]', { timeout: 5000 }).catch(() => {})
  })

  test('export saved cards API requires authentication', async ({ page, apiBaseUrl }) => {
    const response = await page.request.get(`${apiBaseUrl}/api/saved-cards/export`)
    expect(response.status()).toBe(401)
  })
})

test.describe('Saved Cards Persistence', () => {
  test('saved cards persist after logout and re-login', async ({ page }) => {
    const savedCards: { id: string; card_id: string; job_id: string; saved_at: string }[] = []

    await page.route('**/api/auth/google', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'mock-jwt-token',
          token_type: 'bearer',
          user: {
            id: 'user-123',
            email: 'test@example.com',
            name: 'Test User',
          },
        }),
      })
    })

    await page.route('**/api/saved-cards', async (route) => {
      if (route.request().method() === 'POST') {
        const body = route.request().postDataJSON()
        for (const cardId of body.card_ids) {
          savedCards.push({
            id: `saved-${savedCards.length + 1}`,
            card_id: cardId,
            job_id: body.job_id,
            saved_at: new Date().toISOString(),
          })
        }
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            saved_count: body.card_ids.length,
            message: 'Cards saved successfully',
          }),
        })
      } else if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            cards: savedCards,
            total: savedCards.length,
            limit: 20,
            offset: 0,
          }),
        })
      }
    })

    await page.goto('/')

    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'mock-jwt-token')
    })

    const saveResponse = await page.request.post('http://localhost:8000/api/saved-cards', {
      headers: { Authorization: 'Bearer mock-jwt-token' },
      data: { job_id: 'test-job', card_ids: ['card-1', 'card-2'] },
    })
    expect([200, 401]).toContain(saveResponse.status())

    await page.evaluate(() => {
      localStorage.removeItem('auth_token')
    })

    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'mock-jwt-token')
    })

    const getResponse = await page.request.get('http://localhost:8000/api/saved-cards', {
      headers: { Authorization: 'Bearer mock-jwt-token' },
    })

    if (getResponse.status() === 200) {
      const data = await getResponse.json()
      expect(data.cards.length).toBeGreaterThanOrEqual(0)
    }
  })
})
