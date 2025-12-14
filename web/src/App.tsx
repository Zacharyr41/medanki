import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from './components/Layout'

const queryClient = new QueryClient()

function UploadPage() {
  return <div>Upload Page</div>
}

function ProcessingPage() {
  return <div>Processing Page</div>
}

function DownloadPage() {
  return <div>Download Page</div>
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<UploadPage />} />
            <Route path="/processing/:id" element={<ProcessingPage />} />
            <Route path="/download/:id" element={<DownloadPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
