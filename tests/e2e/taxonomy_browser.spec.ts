import { test, expect } from './fixtures'

test.describe('Taxonomy Browser', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/taxonomy')
  })

  test('should display exam selection', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Taxonomy Browser' })).toBeVisible()
    await expect(page.getByTestId('exam-mcat')).toBeVisible()
    await expect(page.getByTestId('exam-usmle')).toBeVisible()
  })

  test('should navigate MCAT hierarchy', async ({ page }) => {
    await page.getByTestId('exam-mcat').click()

    await expect(page.getByRole('heading', { name: 'MCAT' })).toBeVisible()
    await expect(page.getByTestId('fc-list')).toBeVisible()

    const foundationalConcepts = page.getByTestId('fc-list').locator('[data-testid^="fc-item-"]')
    await expect(foundationalConcepts).toHaveCount(10)

    await foundationalConcepts.first().click()

    await expect(page.getByTestId('content-categories')).toBeVisible()
  })

  test('should navigate USMLE hierarchy', async ({ page }) => {
    await page.getByTestId('exam-usmle').click()

    await expect(page.getByRole('heading', { name: 'USMLE' })).toBeVisible()
    await expect(page.getByTestId('system-list')).toBeVisible()
  })

  test('should search taxonomy', async ({ page }) => {
    await page.getByTestId('exam-mcat').click()

    const searchInput = page.getByTestId('taxonomy-search')
    await expect(searchInput).toBeVisible()

    await searchInput.fill('glycolysis')
    await searchInput.press('Enter')

    await expect(page.getByTestId('search-results')).toBeVisible()
    const results = page.getByTestId('search-results').locator('[data-testid^="search-result-"]')
    await expect(results.first()).toBeVisible()
  })

  test('should show breadcrumb navigation', async ({ page }) => {
    await page.getByTestId('exam-mcat').click()

    const breadcrumb = page.getByTestId('breadcrumb')
    await expect(breadcrumb).toBeVisible()
    await expect(breadcrumb).toContainText('MCAT')

    const foundationalConcepts = page.getByTestId('fc-list').locator('[data-testid^="fc-item-"]')
    await foundationalConcepts.first().click()

    await expect(breadcrumb).toContainText('FC1')
  })

  test('should allow going back via breadcrumb', async ({ page }) => {
    await page.getByTestId('exam-mcat').click()
    const foundationalConcepts = page.getByTestId('fc-list').locator('[data-testid^="fc-item-"]')
    await foundationalConcepts.first().click()

    const breadcrumbHome = page.getByTestId('breadcrumb').getByRole('link', { name: 'MCAT' })
    await breadcrumbHome.click()

    await expect(page.getByTestId('fc-list')).toBeVisible()
  })

  test('should display topic details', async ({ page }) => {
    await page.getByTestId('exam-mcat').click()

    const foundationalConcepts = page.getByTestId('fc-list').locator('[data-testid^="fc-item-"]')
    await foundationalConcepts.first().click()

    const categories = page.getByTestId('content-categories').locator('[data-testid^="category-"]')
    await categories.first().click()

    await expect(page.getByTestId('topic-details')).toBeVisible()
    await expect(page.getByTestId('topic-title')).toBeVisible()
    await expect(page.getByTestId('topic-subtopics')).toBeVisible()
  })
})
