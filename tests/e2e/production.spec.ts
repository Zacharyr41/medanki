import { test, expect } from '@playwright/test'
import { config, EXAM_OPTIONS } from './config'

test.describe('Production Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(config.baseUrl)
  })

  test('homepage loads successfully', async ({ page }) => {
    await expect(page).toHaveTitle(/medanki|flashcard/i)
    await expect(page.getByRole('heading', { name: /generate|flashcard/i })).toBeVisible({
      timeout: config.timeout,
    })
  })

  test('upload form renders', async ({ page }) => {
    await expect(page.getByTestId('dropzone')).toBeVisible({ timeout: config.timeout })
    await expect(page.getByRole('button', { name: 'Generate Cards' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Generate Cards' })).toBeDisabled()
  })

  test('exam dropdown has correct options', async ({ page }) => {
    const examSelect = page.getByLabel('Exam')
    await expect(examSelect).toBeVisible({ timeout: config.timeout })

    for (const examOption of EXAM_OPTIONS) {
      const option = page.getByRole('option', { name: examOption })
      await expect(option).toBeAttached()
    }
  })

  test('card type checkboxes render', async ({ page }) => {
    await expect(page.getByRole('checkbox', { name: 'Cloze' })).toBeVisible({
      timeout: config.timeout,
    })
    await expect(page.getByRole('checkbox', { name: 'Vignette' })).toBeVisible()
  })

  test('max cards input renders', async ({ page }) => {
    const input = page.getByLabel(/max.*cards/i)
    await expect(input).toBeVisible({ timeout: config.timeout })
    await expect(input).toHaveAttribute('type', 'number')
  })
})

test.describe('API Health Checks', () => {
  test('API health endpoint responds', async ({ request }) => {
    const response = await request.get(`${config.apiUrl}/api/health`)
    expect(response.ok()).toBeTruthy()
  })

  test('API taxonomy endpoint responds', async ({ request }) => {
    const response = await request.get(`${config.apiUrl}/api/taxonomy/exams`)
    expect(response.ok()).toBeTruthy()
    const data = await response.json()
    expect(data).toHaveProperty('exams')
  })
})

test.describe('Navigation', () => {
  test('taxonomy browser is accessible', async ({ page }) => {
    await page.goto(`${config.baseUrl}/taxonomy`)
    await expect(page.getByRole('heading', { name: /taxonomy|browse/i })).toBeVisible({
      timeout: config.timeout,
    })
  })
})
