import { useState, useMemo } from 'react'
import type {
  ExamType,
  FoundationalConcept,
  TaxonomyCategory,
  TaxonomySearchResult,
} from '../types'

const mcatData = {
  exam: 'MCAT' as const,
  version: '2024',
  foundational_concepts: [
    { id: 'FC1', title: 'Biomolecules have unique properties', keywords: ['biomolecules'], categories: [
      { id: '1A', title: 'Structure and function of proteins', keywords: ['proteins', 'amino acids'] },
      { id: '1B', title: 'Transmission of genetic information', keywords: ['DNA', 'RNA', 'transcription'] },
      { id: '1C', title: 'Transmission of heritable information', keywords: ['genetics', 'heredity'] },
      { id: '1D', title: 'Principles of bioenergetics and fuel molecule metabolism', keywords: ['metabolism', 'glycolysis', 'ATP'] },
    ]},
    { id: 'FC2', title: 'Highly organized assemblies of molecules', keywords: ['cells', 'organs'], categories: [
      { id: '2A', title: 'Assemblies of molecules and cells', keywords: ['cell biology'] },
      { id: '2B', title: 'Prokaryotes and viruses', keywords: ['bacteria', 'viruses'] },
      { id: '2C', title: 'Cell division and differentiation', keywords: ['mitosis', 'cell cycle'] },
    ]},
    { id: 'FC3', title: 'Complex systems sense environments', keywords: ['tissues', 'organs'], categories: [] },
    { id: 'FC4', title: 'Complex organisms transport materials', keywords: ['transport'], categories: [] },
    { id: 'FC5', title: 'Chemical interactions and reactions', keywords: ['chemistry'], categories: [] },
    { id: 'FC6', title: 'Factors influence perception and cognition', keywords: ['perception'], categories: [] },
    { id: 'FC7', title: 'Factors influence behavior', keywords: ['behavior'], categories: [] },
    { id: 'FC8', title: 'Factors influence social interaction', keywords: ['social'], categories: [] },
    { id: 'FC9', title: 'Cultural differences influence well-being', keywords: ['culture'], categories: [] },
    { id: 'FC10', title: 'Social stratification influences well-being', keywords: ['stratification'], categories: [] },
  ]
}

const usmleData = {
  exam: 'USMLE' as const,
  version: '2024',
  systems: [
    { id: 'SYS1', title: 'General Principles', keywords: ['biochemistry'], topics: [] },
    { id: 'SYS2', title: 'Blood and Lymphoreticular System', keywords: ['hematology'], topics: [] },
    { id: 'SYS3', title: 'Cardiovascular System', keywords: ['cardiovascular'], topics: [] },
  ]
}

type ViewState =
  | { type: 'exam-selection' }
  | { type: 'mcat-fc-list' }
  | { type: 'mcat-categories'; fc: FoundationalConcept }
  | { type: 'mcat-topic'; fc: FoundationalConcept; category: TaxonomyCategory }
  | { type: 'usmle-systems' }

interface BreadcrumbItem {
  label: string
  onClick: () => void
}

export function TaxonomyBrowserPage() {
  const [view, setView] = useState<ViewState>({ type: 'exam-selection' })
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<TaxonomySearchResult[]>([])
  const [showSearchResults, setShowSearchResults] = useState(false)

  const mcat = mcatData
  const usmle = usmleData

  const breadcrumbs = useMemo((): BreadcrumbItem[] => {
    const items: BreadcrumbItem[] = []

    if (view.type === 'mcat-fc-list') {
      items.push({ label: 'MCAT', onClick: () => setView({ type: 'mcat-fc-list' }) })
    } else if (view.type === 'mcat-categories') {
      items.push({ label: 'MCAT', onClick: () => setView({ type: 'mcat-fc-list' }) })
      items.push({
        label: view.fc.id,
        onClick: () => setView({ type: 'mcat-categories', fc: view.fc }),
      })
    } else if (view.type === 'mcat-topic') {
      items.push({ label: 'MCAT', onClick: () => setView({ type: 'mcat-fc-list' }) })
      items.push({
        label: view.fc.id,
        onClick: () => setView({ type: 'mcat-categories', fc: view.fc }),
      })
      items.push({
        label: view.category.id,
        onClick: () => setView({ type: 'mcat-topic', fc: view.fc, category: view.category }),
      })
    } else if (view.type === 'usmle-systems') {
      items.push({ label: 'USMLE', onClick: () => setView({ type: 'usmle-systems' }) })
    }

    return items
  }, [view])

  const handleSearch = (query: string) => {
    setSearchQuery(query)
    if (!query.trim()) {
      setSearchResults([])
      setShowSearchResults(false)
      return
    }

    const results: TaxonomySearchResult[] = []
    const lowerQuery = query.toLowerCase()

    for (const fc of mcat.foundational_concepts) {
      if (fc.title.toLowerCase().includes(lowerQuery) || fc.keywords.some(k => k.toLowerCase().includes(lowerQuery))) {
        results.push({
          id: fc.id,
          title: fc.title,
          path: ['MCAT', fc.id],
          type: 'foundational_concept',
        })
      }

      for (const cat of fc.categories) {
        if (cat.title.toLowerCase().includes(lowerQuery) || cat.keywords.some(k => k.toLowerCase().includes(lowerQuery))) {
          results.push({
            id: cat.id,
            title: cat.title,
            path: ['MCAT', fc.id, cat.id],
            type: 'content_category',
          })
        }
      }
    }

    setSearchResults(results)
    setShowSearchResults(true)
  }

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    handleSearch(searchQuery)
  }

  const handleExamSelect = (exam: ExamType) => {
    if (exam === 'MCAT') {
      setView({ type: 'mcat-fc-list' })
    } else {
      setView({ type: 'usmle-systems' })
    }
    setShowSearchResults(false)
    setSearchQuery('')
  }

  const handleFCSelect = (fc: FoundationalConcept) => {
    setView({ type: 'mcat-categories', fc })
  }

  const handleCategorySelect = (fc: FoundationalConcept, category: TaxonomyCategory) => {
    setView({ type: 'mcat-topic', fc, category })
  }

  return (
    <div className="taxonomy-browser">
      <h1>Taxonomy Browser</h1>

      {view.type === 'exam-selection' ? (
        <div className="exam-selection">
          <button
            data-testid="exam-mcat"
            className="exam-card"
            onClick={() => handleExamSelect('MCAT')}
          >
            <h2>MCAT</h2>
            <p>Medical College Admission Test</p>
          </button>
          <button
            data-testid="exam-usmle"
            className="exam-card"
            onClick={() => handleExamSelect('USMLE')}
          >
            <h2>USMLE</h2>
            <p>United States Medical Licensing Examination</p>
          </button>
        </div>
      ) : (
        <>
          {breadcrumbs.length > 0 && (
            <nav data-testid="breadcrumb" className="breadcrumb">
              {breadcrumbs.map((item, index) => (
                <span key={index}>
                  {index > 0 && <span className="breadcrumb-separator"> / </span>}
                  {index === breadcrumbs.length - 1 ? (
                    <span>{item.label}</span>
                  ) : (
                    <a href="#" onClick={(e) => { e.preventDefault(); item.onClick(); }}>
                      {item.label}
                    </a>
                  )}
                </span>
              ))}
            </nav>
          )}

          <form onSubmit={handleSearchSubmit} className="taxonomy-search-form">
            <input
              type="text"
              data-testid="taxonomy-search"
              className="taxonomy-search-input"
              placeholder="Search taxonomy..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </form>

          {showSearchResults && (
            <div data-testid="search-results" className="search-results">
              <h3>Search Results ({searchResults.length})</h3>
              {searchResults.map((result, index) => (
                <div
                  key={result.id + index}
                  data-testid={`search-result-${index}`}
                  className="search-result-item"
                >
                  <span className="search-result-path">{result.path.join(' > ')}</span>
                  <span className="search-result-title">{result.title}</span>
                </div>
              ))}
            </div>
          )}

          {!showSearchResults && view.type === 'mcat-fc-list' && (
            <>
              <h2>MCAT</h2>
              <div data-testid="fc-list" className="fc-list">
                {mcat.foundational_concepts.map((fc, index) => (
                  <button
                    key={fc.id}
                    data-testid={`fc-item-${index}`}
                    className="fc-item"
                    onClick={() => handleFCSelect(fc)}
                  >
                    <span className="fc-id">{fc.id}</span>
                    <span className="fc-title">{fc.title}</span>
                  </button>
                ))}
              </div>
            </>
          )}

          {!showSearchResults && view.type === 'mcat-categories' && (
            <>
              <h2>{view.fc.id}: {view.fc.title}</h2>
              <div data-testid="content-categories" className="content-categories">
                {view.fc.categories.map((cat, index) => (
                  <button
                    key={cat.id}
                    data-testid={`category-${index}`}
                    className="category-item"
                    onClick={() => handleCategorySelect(view.fc, cat)}
                  >
                    <span className="category-id">{cat.id}</span>
                    <span className="category-title">{cat.title}</span>
                  </button>
                ))}
              </div>
            </>
          )}

          {!showSearchResults && view.type === 'mcat-topic' && (
            <div data-testid="topic-details" className="topic-details">
              <h2 data-testid="topic-title">{view.category.id}: {view.category.title}</h2>
              <div data-testid="topic-subtopics" className="topic-subtopics">
                <h3>Keywords</h3>
                <ul>
                  {view.category.keywords.map((keyword, index) => (
                    <li key={index}>{keyword}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {!showSearchResults && view.type === 'usmle-systems' && (
            <>
              <h2>USMLE</h2>
              <div data-testid="system-list" className="system-list">
                {usmle.systems.map((system, index) => (
                  <div key={system.id} data-testid={`system-item-${index}`} className="system-item">
                    <span className="system-id">{system.id}</span>
                    <span className="system-title">{system.title}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
