import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { TopicInput } from '../TopicInput'

describe('TopicInput', () => {
  it('renders textarea', () => {
    render(<TopicInput value="" onChange={vi.fn()} />)

    expect(screen.getByTestId('topic-input')).toBeInTheDocument()
  })

  it('shows placeholder text', () => {
    render(<TopicInput value="" onChange={vi.fn()} />)

    expect(screen.getByPlaceholderText(/describe.*topics.*want.*study/i)).toBeInTheDocument()
  })

  it('displays current value', () => {
    render(<TopicInput value="Learn about cardiology" onChange={vi.fn()} />)

    expect(screen.getByDisplayValue('Learn about cardiology')).toBeInTheDocument()
  })

  it('calls onChange when typing', async () => {
    const onChange = vi.fn()
    render(<TopicInput value="" onChange={onChange} />)

    const textarea = screen.getByTestId('topic-input')
    await userEvent.type(textarea, 'Test input')

    expect(onChange).toHaveBeenCalled()
  })

  it('shows character count', () => {
    render(<TopicInput value="Hello world" onChange={vi.fn()} />)

    expect(screen.getByTestId('char-count')).toHaveTextContent('11')
  })

  it('shows character limit', () => {
    render(<TopicInput value="" onChange={vi.fn()} maxLength={2000} />)

    expect(screen.getByText('/ 2000')).toBeInTheDocument()
  })

  it('enforces max length', async () => {
    const onChange = vi.fn()
    render(<TopicInput value="" onChange={onChange} maxLength={10} />)

    const textarea = screen.getByTestId('topic-input')
    await userEvent.type(textarea, 'This is a very long text that exceeds the limit')

    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0]
    expect(lastCall.length).toBeLessThanOrEqual(10)
  })

  it('uses default max length of 2000', () => {
    render(<TopicInput value="" onChange={vi.fn()} />)

    expect(screen.getByText('/ 2000')).toBeInTheDocument()
  })

  it('allows custom max length', () => {
    render(<TopicInput value="" onChange={vi.fn()} maxLength={500} />)

    expect(screen.getByText('/ 500')).toBeInTheDocument()
  })
})
