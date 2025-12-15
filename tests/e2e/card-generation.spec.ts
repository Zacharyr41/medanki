import { test, expect } from '@playwright/test'
import * as path from 'path'

const FIXTURES_DIR = path.join(__dirname, 'fixtures')

test.describe('Card Generation E2E', () => {
  test('generates cards from First Aid endocrine PDF', async ({ page }) => {
    const pdfPath = path.join(FIXTURES_DIR, 'First-Aid-endocrine-system.pdf')

    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Generate Flashcards' })).toBeVisible()

    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(pdfPath)

    await expect(page.getByText('First-Aid-endocrine-system.pdf')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Generate Cards' })).toBeEnabled()

    const examSelect = page.getByLabel('Exam')
    await examSelect.selectOption('USMLE Step 1')

    await page.getByRole('button', { name: 'Generate Cards' }).click()

    await expect(page).toHaveURL(/\/processing\//, { timeout: 10000 })

    await expect(page).toHaveURL(/\/download\//, { timeout: 120000 })

    await expect(page.getByText(/\d+.*cards?/i)).toBeVisible({ timeout: 10000 })

    const downloadButton = page.getByRole('button', { name: /download/i })
    await expect(downloadButton).toBeVisible({ timeout: 10000 })

    const downloadPromise = page.waitForEvent('download')
    await downloadButton.click()
    const download = await downloadPromise

    expect(download.suggestedFilename()).toMatch(/\.apkg$/)
  })
})
