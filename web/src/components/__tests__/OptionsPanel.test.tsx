import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { OptionsPanel, type GenerationOptions } from '../OptionsPanel'

const defaultOptions: GenerationOptions = {
  exam: 'USMLE Step 1',
  cardTypes: { cloze: true, vignette: true },
  maxCards: 20,
}

describe('OptionsPanel', () => {
  it('renders exam select', () => {
    render(<OptionsPanel options={defaultOptions} onChange={vi.fn()} />)
    expect(screen.getByLabelText(/exam/i)).toBeInTheDocument()
  })

  it('has exam options', () => {
    render(<OptionsPanel options={defaultOptions} onChange={vi.fn()} />)

    const select = screen.getByLabelText(/exam/i)
    expect(select).toBeInTheDocument()

    expect(screen.getByRole('option', { name: /mcat/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /usmle step 1/i })).toBeInTheDocument()
  })

  it('renders card type checkboxes', () => {
    render(<OptionsPanel options={defaultOptions} onChange={vi.fn()} />)

    expect(screen.getByLabelText(/cloze/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/vignette/i)).toBeInTheDocument()
  })

  it('renders max cards input', () => {
    render(<OptionsPanel options={defaultOptions} onChange={vi.fn()} />)

    const input = screen.getByLabelText(/max.*cards/i)
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('type', 'number')
  })

  it('calls onChange with updated options', async () => {
    const onChange = vi.fn()
    render(<OptionsPanel options={defaultOptions} onChange={onChange} />)

    const select = screen.getByLabelText(/exam/i)
    await userEvent.selectOptions(select, 'MCAT')

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ exam: 'MCAT' })
    )
  })
})
