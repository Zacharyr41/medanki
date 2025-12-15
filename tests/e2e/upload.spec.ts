import { test, expect } from './fixtures'

test.describe('Upload Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('page loads with correct elements', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Generate Flashcards' })).toBeVisible()
    await expect(page.getByTestId('dropzone')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Generate Cards' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Generate Cards' })).toBeDisabled()
  })

  test('can drop PDF file', async ({ page, samplePdfPath }) => {
    const dropzone = page.getByTestId('dropzone')

    const dataTransfer = await page.evaluateHandle(() => new DataTransfer())
    const buffer = await test.step('read file', async () => {
      const fs = await import('fs')
      return fs.readFileSync(samplePdfPath)
    })

    await page.evaluate(
      async ({ dataTransfer, buffer }) => {
        const file = new File([new Uint8Array(buffer)], 'sample.pdf', { type: 'application/pdf' })
        dataTransfer.items.add(file)
      },
      { dataTransfer: dataTransfer as unknown as DataTransfer, buffer: Array.from(buffer) }
    )

    await dropzone.dispatchEvent('drop', { dataTransfer })

    await expect(page.getByText('sample.pdf')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Generate Cards' })).toBeEnabled()
  })

  test('can select file via input', async ({ page, sampleMdPath }) => {
    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(sampleMdPath)

    await expect(page.getByText('sample.md')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Generate Cards' })).toBeEnabled()
  })

  test('can change exam option', async ({ page }) => {
    const examSelect = page.getByLabel('Exam')
    await expect(examSelect).toHaveValue('USMLE Step 1')

    await examSelect.selectOption('MCAT')
    await expect(examSelect).toHaveValue('MCAT')

    await examSelect.selectOption('USMLE Step 1')
    await expect(examSelect).toHaveValue('USMLE Step 1')
  })

  test('can toggle card types', async ({ page }) => {
    const clozeCheckbox = page.getByRole('checkbox', { name: 'Cloze' })
    const vignetteCheckbox = page.getByRole('checkbox', { name: 'Vignette' })

    await expect(clozeCheckbox).toBeChecked()
    await expect(vignetteCheckbox).toBeChecked()

    await clozeCheckbox.uncheck()
    await expect(clozeCheckbox).not.toBeChecked()

    await vignetteCheckbox.uncheck()
    await expect(vignetteCheckbox).not.toBeChecked()

    await clozeCheckbox.check()
    await expect(clozeCheckbox).toBeChecked()
  })

  test('can change max cards', async ({ page }) => {
    const maxCardsInput = page.getByLabel('Max Cards per Chunk')
    await expect(maxCardsInput).toHaveValue('10')

    await maxCardsInput.fill('25')
    await expect(maxCardsInput).toHaveValue('25')
  })

  test('submit navigates to processing', async ({ page, sampleMdPath }) => {
    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(sampleMdPath)

    await page.route('**/api/upload', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ jobId: 'test-job-123' }),
      })
    })

    await page.getByRole('button', { name: 'Generate Cards' }).click()

    await expect(page).toHaveURL(/\/processing\/test-job-123/)
  })

  test('shows error on upload failure', async ({ page, sampleMdPath }) => {
    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(sampleMdPath)

    await page.route('**/api/upload', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Server error' }),
      })
    })

    await page.getByRole('button', { name: 'Generate Cards' }).click()

    await expect(page.getByText('Upload failed')).toBeVisible()
  })
})
