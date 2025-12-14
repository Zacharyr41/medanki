import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from './components/Layout'
import { UploadPage } from './pages/UploadPage'
import { ProcessingPage } from './pages/ProcessingPage'
import { DownloadPage } from './pages/DownloadPage'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<UploadPage />} />
            <Route path="/processing/:id" element={<ProcessingPage />} />
            <Route path="/download/:jobId" element={<DownloadPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
