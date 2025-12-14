import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StageList } from '../StageList'

describe('StageList', () => {
  it('shows all stages', () => {
    render(
      <StageList
        currentStage="ingesting"
        completedStages={[]}
        stageTimes={{}}
      />
    )

    expect(screen.getByText(/ingesting/i)).toBeInTheDocument()
    expect(screen.getByText(/chunking/i)).toBeInTheDocument()
    expect(screen.getByText(/classifying/i)).toBeInTheDocument()
    expect(screen.getByText(/generating/i)).toBeInTheDocument()
    expect(screen.getByText(/exporting/i)).toBeInTheDocument()
  })

  it('current stage highlighted', () => {
    render(
      <StageList
        currentStage="chunking"
        completedStages={['ingesting']}
        stageTimes={{}}
      />
    )

    const currentStage = screen.getByTestId('stage-chunking')
    expect(currentStage).toHaveClass('text-blue-600')
  })

  it('completed stages checked', () => {
    render(
      <StageList
        currentStage="classifying"
        completedStages={['ingesting', 'chunking']}
        stageTimes={{}}
      />
    )

    const ingestingStage = screen.getByTestId('stage-ingesting')
    const chunkingStage = screen.getByTestId('stage-chunking')

    expect(ingestingStage.querySelector('[data-testid="check-icon"]')).toBeInTheDocument()
    expect(chunkingStage.querySelector('[data-testid="check-icon"]')).toBeInTheDocument()
  })

  it('shows stage duration', () => {
    render(
      <StageList
        currentStage="classifying"
        completedStages={['ingesting', 'chunking']}
        stageTimes={{ ingesting: 5000, chunking: 3000 }}
      />
    )

    expect(screen.getByText('5s')).toBeInTheDocument()
    expect(screen.getByText('3s')).toBeInTheDocument()
  })
})
