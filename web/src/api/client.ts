import type { Material, MaterialListItem, PrototypeListItem, Prototype, GenerateParams, GenerateResult, GenerateFullResult, Stats, ClassificationResponse, LayerData, PrimitiveCellData, CoordinationEnvironment, LatticeTypeInfo } from '../types'

const BASE = '/CGCPT/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json()
}

export async function fetchPrototypes(): Promise<{ prototypes: PrototypeListItem[]; total: number }> {
  return request('/prototypes')
}

export async function fetchPrototype(id: string): Promise<Prototype> {
  return request<Prototype>(`/prototypes/${encodeURIComponent(id)}`)
}

export async function fetchMaterials(params?: Record<string, string>): Promise<{ materials: MaterialListItem[]; total: number; page: number; per_page: number; total_pages: number }> {
  const query = params ? '?' + new URLSearchParams(params).toString() : ''
  return request(`/materials${query}`)
}

export async function fetchMaterial(id: string): Promise<Material> {
  return request<Material>(`/materials/${encodeURIComponent(id)}`)
}

export async function generateStructure(params: GenerateParams): Promise<GenerateResult> {
  return request<GenerateResult>('/generate', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

export async function generateFull(params: GenerateParams): Promise<GenerateFullResult> {
  return request<GenerateFullResult>('/generate/full', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

export async function fetchLayerData(params: GenerateParams): Promise<{ layer_data: LayerData[] }> {
  return request('/generate/layer-data', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

export async function fetchPrimitive(params: GenerateParams): Promise<{ supercell: unknown; primitive: PrimitiveCellData }> {
  return request('/generate/primitive', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

export async function fetchCoordination(params: GenerateParams & { cutoff_radius?: number }): Promise<{ environments: CoordinationEnvironment[] }> {
  return request('/generate/coordination', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

export async function fetchCifContent(materialId: string): Promise<string> {
  const res = await fetch(`${BASE}/materials/${encodeURIComponent(materialId)}/cif`)
  return res.text()
}

export async function fetchLatticeTypes(): Promise<LatticeTypeInfo[]> {
  return request('/lattice-types')
}

export async function fetchClassifications(): Promise<ClassificationResponse> {
  return request('/classifications')
}

export async function searchMaterials(query: string): Promise<{ results: MaterialListItem[]; total: number; query: string }> {
  return request(`/search?q=${encodeURIComponent(query)}`)
}

export async function fetchStats(): Promise<Stats> {
  return request<Stats>('/stats')
}

export async function fetchElements(): Promise<string[]> {
  return request<string[]>('/elements')
}

export interface ImportPreviewResult {
  filename: string
  material_id: string
  formula: string
  space_group: string
  elements: string[]
  n_atoms: number
  lattice: { a?: number; b?: number; c?: number; alpha?: number; beta?: number; gamma?: number }
  existing: boolean
  suggested_topology: string | null
  confidence: number
  assigned_topology: string
  cif_preview: string
  error?: string
}

export interface ImportPreviewResponse {
  success: boolean
  results: ImportPreviewResult[]
  available_topologies: string[]
  total_files: number
  parsed: number
  errors: number
}

export async function previewImportFiles(files: File[], topology?: string): Promise<ImportPreviewResponse> {
  const formData = new FormData()
  files.forEach(f => formData.append('files', f))
  if (topology) formData.append('topology', topology)
  const res = await fetch(`${BASE}/import/preview`, { method: 'POST', body: formData })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json()
}

export interface ImportItem {
  material_id: string
  topology: string
  cif_content: string
  formula: string
  space_group: string
  elements: string[]
}

export interface ImportResponse {
  success: boolean
  imported: Array<{ material_id: string; topology: string; path: string }>
  skipped: string[]
  errors: Array<{ material_id: string; reason: string }>
  total_new: number
  total_materials_now: number
  error?: string
}

export async function importMaterials(items: ImportItem[]): Promise<ImportResponse> {
  return request<ImportResponse>('/import', {
    method: 'POST',
    body: JSON.stringify({ items }),
  })
}
