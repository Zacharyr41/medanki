import { test, expect } from './fixtures'

test.describe('Topic Input Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test.describe('Input Mode Selection', () => {
    test('page shows input mode toggle', async ({ page }) => {
      await expect(page.getByRole('tab', { name: 'Upload File' })).toBeVisible()
      await expect(page.getByRole('tab', { name: 'Describe Topics' })).toBeVisible()
    })

    test('file upload mode is selected by default', async ({ page }) => {
      await expect(page.getByRole('tab', { name: 'Upload File' })).toHaveAttribute(
        'aria-selected',
        'true'
      )
      await expect(page.getByTestId('dropzone')).toBeVisible()
    })

    test('can switch to topic description mode', async ({ page }) => {
      await page.getByRole('tab', { name: 'Describe Topics' }).click()

      await expect(page.getByRole('tab', { name: 'Describe Topics' })).toHaveAttribute(
        'aria-selected',
        'true'
      )
      await expect(page.getByTestId('dropzone')).not.toBeVisible()
      await expect(page.getByTestId('topic-input')).toBeVisible()
    })

    test('can switch back to file upload mode', async ({ page }) => {
      await page.getByRole('tab', { name: 'Describe Topics' }).click()
      await page.getByRole('tab', { name: 'Upload File' }).click()

      await expect(page.getByTestId('dropzone')).toBeVisible()
      await expect(page.getByTestId('topic-input')).not.toBeVisible()
    })
  })

  test.describe('Topic Input Component', () => {
    test.beforeEach(async ({ page }) => {
      await page.getByRole('tab', { name: 'Describe Topics' }).click()
    })

    test('shows textarea with placeholder', async ({ page }) => {
      const textarea = page.getByTestId('topic-input')
      await expect(textarea).toBeVisible()
      await expect(textarea).toHaveAttribute(
        'placeholder',
        /describe.*topics.*want.*study/i
      )
    })

    test('can enter topic description', async ({ page }) => {
      const textarea = page.getByTestId('topic-input')
      await textarea.fill('I want to learn about cardiac electrophysiology and arrhythmias')

      await expect(textarea).toHaveValue(
        'I want to learn about cardiac electrophysiology and arrhythmias'
      )
    })

    test('shows character count', async ({ page }) => {
      const textarea = page.getByTestId('topic-input')
      await textarea.fill('Test input')

      await expect(page.getByTestId('char-count')).toContainText('10')
    })

    test('enforces max character limit', async ({ page }) => {
      const textarea = page.getByTestId('topic-input')
      const longText = 'a'.repeat(2100)
      await textarea.fill(longText)

      const value = await textarea.inputValue()
      expect(value.length).toBeLessThanOrEqual(2000)
    })

    test('enables submit button when text is entered', async ({ page }) => {
      const submitButton = page.getByRole('button', { name: 'Generate Cards' })
      await expect(submitButton).toBeDisabled()

      await page.getByTestId('topic-input').fill('Learn about pharmacology')
      await expect(submitButton).toBeEnabled()
    })

    test('disables submit button when text is empty', async ({ page }) => {
      const textarea = page.getByTestId('topic-input')
      const submitButton = page.getByRole('button', { name: 'Generate Cards' })

      await textarea.fill('Some text')
      await expect(submitButton).toBeEnabled()

      await textarea.fill('')
      await expect(submitButton).toBeDisabled()
    })
  })

  test.describe('Total Cards Setting', () => {
    test('shows "Total Cards" label instead of "Max Cards per Chunk"', async ({ page }) => {
      await expect(page.getByLabel('Total Cards')).toBeVisible()
      await expect(page.getByLabel('Max Cards per Chunk')).not.toBeVisible()
    })

    test('has default value of 20', async ({ page }) => {
      const totalCardsInput = page.getByLabel('Total Cards')
      await expect(totalCardsInput).toHaveValue('20')
    })

    test('can change total cards value', async ({ page }) => {
      const totalCardsInput = page.getByLabel('Total Cards')
      await totalCardsInput.fill('50')
      await expect(totalCardsInput).toHaveValue('50')
    })

    test('enforces minimum of 1', async ({ page }) => {
      const totalCardsInput = page.getByLabel('Total Cards')
      await totalCardsInput.fill('0')
      await totalCardsInput.blur()

      const value = await totalCardsInput.inputValue()
      expect(parseInt(value)).toBeGreaterThanOrEqual(1)
    })

    test('enforces maximum of 100', async ({ page }) => {
      const totalCardsInput = page.getByLabel('Total Cards')
      await totalCardsInput.fill('150')
      await totalCardsInput.blur()

      const value = await totalCardsInput.inputValue()
      expect(parseInt(value)).toBeLessThanOrEqual(100)
    })
  })

  test.describe('Topic Submission Flow', () => {
    test.beforeEach(async ({ page }) => {
      await page.getByRole('tab', { name: 'Describe Topics' }).click()
    })

    test('submit with topic text navigates to processing', async ({ page }) => {
      await page.getByTestId('topic-input').fill(
        'I want to study the cardiovascular system, including heart anatomy and blood flow'
      )

      await page.route('**/api/upload', async (route) => {
        const request = route.request()
        const postData = request.postData()

        expect(postData).toContain('topic_text')
        expect(postData).toContain('cardiovascular')

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ job_id: 'topic-job-456', status: 'pending' }),
        })
      })

      await page.getByRole('button', { name: 'Generate Cards' }).click()
      await expect(page).toHaveURL(/\/processing\/topic-job-456/)
    })

    test('sends correct options with topic request', async ({ page }) => {
      await page.getByTestId('topic-input').fill('Study pharmacology basics')
      await page.getByLabel('Exam').selectOption('MCAT')
      await page.getByLabel('Total Cards').fill('30')
      await page.getByRole('checkbox', { name: 'Vignette' }).uncheck()

      let capturedRequest: { exam: string; maxCards: string; cardTypes: string } | null = null

      await page.route('**/api/upload', async (route) => {
        const request = route.request()
        const postData = request.postData() || ''

        const examMatch = postData.match(/exam[^=]*=([^&\r\n]+)/)
        const maxCardsMatch = postData.match(/max_cards[^=]*=([^&\r\n]+)/)
        const cardTypesMatch = postData.match(/card_types[^=]*=([^&\r\n]+)/)

        capturedRequest = {
          exam: examMatch ? decodeURIComponent(examMatch[1]) : '',
          maxCards: maxCardsMatch ? decodeURIComponent(maxCardsMatch[1]) : '',
          cardTypes: cardTypesMatch ? decodeURIComponent(cardTypesMatch[1]) : '',
        }

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ job_id: 'options-job', status: 'pending' }),
        })
      })

      await page.getByRole('button', { name: 'Generate Cards' }).click()

      expect(capturedRequest).not.toBeNull()
      expect(capturedRequest?.exam).toBe('MCAT')
      expect(capturedRequest?.maxCards).toBe('30')
      expect(capturedRequest?.cardTypes).toBe('cloze')
    })

    test('shows error on submission failure', async ({ page }) => {
      await page.getByTestId('topic-input').fill('Generate cards about anatomy')

      await page.route('**/api/upload', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Server error' }),
        })
      })

      await page.getByRole('button', { name: 'Generate Cards' }).click()
      await expect(page.getByText(/upload failed|error/i)).toBeVisible()
    })

    test('shows validation error for empty topic text', async ({ page }) => {
      await page.getByTestId('topic-input').fill('   ')
      await page.getByRole('button', { name: 'Generate Cards' }).click()

      await expect(page.getByRole('button', { name: 'Generate Cards' })).toBeDisabled()
    })
  })

  test.describe('Mode Persistence', () => {
    test('input mode persists file selection when switching modes', async ({
      page,
      sampleMdPath,
    }) => {
      const fileInput = page.getByTestId('file-input')
      await fileInput.setInputFiles(sampleMdPath)
      await expect(page.getByText('sample.md')).toBeVisible()

      await page.getByRole('tab', { name: 'Describe Topics' }).click()
      await page.getByRole('tab', { name: 'Upload File' }).click()

      await expect(page.getByText('sample.md')).toBeVisible()
    })

    test('topic text persists when switching modes', async ({ page }) => {
      await page.getByRole('tab', { name: 'Describe Topics' }).click()
      await page.getByTestId('topic-input').fill('My topic text')

      await page.getByRole('tab', { name: 'Upload File' }).click()
      await page.getByRole('tab', { name: 'Describe Topics' }).click()

      await expect(page.getByTestId('topic-input')).toHaveValue('My topic text')
    })
  })
})
