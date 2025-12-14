import { Blob } from 'buffer'

// Polyfills for Node environment
class MockFile {
  name: string
  type: string
  content: string[]

  constructor(content: string[], name: string, options?: { type?: string }) {
    this.content = content
    this.name = name
    this.type = options?.type || ''
  }
}

class MockFormData {
  private data = new Map<string, unknown>()

  append(key: string, value: unknown): void {
    this.data.set(key, value)
  }

  get(key: string): unknown {
    return this.data.get(key)
  }

  has(key: string): boolean {
    return this.data.has(key)
  }
}

// @ts-expect-error - Mock File for Node environment
globalThis.File = MockFile
// @ts-expect-error - Mock FormData for Node environment
globalThis.FormData = MockFormData
// @ts-expect-error - Blob for Node environment
globalThis.Blob = Blob
