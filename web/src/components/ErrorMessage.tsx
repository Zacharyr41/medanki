interface ErrorMessageProps {
  message: string
  onDismiss?: () => void
}

export function ErrorMessage({ message, onDismiss }: ErrorMessageProps) {
  return (
    <div className="error-banner" role="alert">
      <p>{message}</p>
      {onDismiss && (
        <button
          type="button"
          className="dismiss-button"
          onClick={onDismiss}
          aria-label="Dismiss error"
        >
          &times;
        </button>
      )}
    </div>
  )
}
