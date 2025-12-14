interface ChipProps {
  label: string
  variant?: 'default' | 'primary' | 'success'
  onRemove?: () => void
  testId?: string
}

export function Chip({ label, variant = 'default', onRemove, testId }: ChipProps) {
  const variantStyles = {
    default: 'bg-gray-100 text-gray-800',
    primary: 'bg-blue-100 text-blue-800',
    success: 'bg-green-100 text-green-800',
  }

  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center px-2 py-1 rounded-full text-sm ${variantStyles[variant]}`}
    >
      {label}
      {onRemove && (
        <button
          onClick={onRemove}
          className="ml-1 hover:text-red-600"
          aria-label={`Remove ${label}`}
        >
          ×
        </button>
      )}
    </span>
  )
}
