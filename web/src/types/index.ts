export interface Atom {
  element: string
  x: number
  y: number
  z: number
}

export interface Lattice {
  a: number
  b: number
  c: number
  alpha: number
  beta: number
  gamma: number
}

export interface MaterialListItem {
  material_id: string
  formula: string
  space_group: string
  topology: string
  verified: boolean
}

export interface Material {
  material_id: string
  formula: string
  space_group: string
  topology: string
  verified: boolean
  elements: string[]
  cif_file: string
  directory: string
  cif_data: {
    atom_sites: Atom[]
    lattice: Lattice
    formula: string
    space_group: string | null
  }
}

export interface TopologyTheory {
  prototype_id: string
  input_main_shifts: string[]
  expanded_modes: string[]
  expanded_shifts: string[]
  reference_grid: string
}

export interface PrototypeCrystallography {
  ideal_space_group: string
  space_group_number: number
  crystal_system: string
  is_neutral: boolean
  wyckoff_signature: Record<string, string>
}

export interface RealCompound {
  formula: string
  mineral_name: string
  source_id: string
  rmsd_to_ideal: number
  properties: Record<string, unknown>
}

export interface PrototypeListItem {
  id: string
  prototype_id: string
  crystal_system: string
  ideal_space_group: string
  space_group_number: number
  is_neutral: boolean
  expanded_modes: string
  reference_grid: string
  raw_materials_count: number
  verified_materials_count: number
  real_compounds_count: number
}

export interface Prototype {
  id: string
  topology_theory: TopologyTheory
  prototype_crystallography: PrototypeCrystallography
  real_compounds: RealCompound[]
  material_count: number
  raw_materials?: MaterialListItem[]
  verified_materials?: MaterialListItem[]
}

export interface ClassificationTopologyEntry {
  prototype_id: string
  crystal_system: string
  ideal_space_group: string
  expanded_modes: string[]
  materials_count: number
  verified_count: number
}

export interface ClassificationResponse {
  by_topology: Record<string, ClassificationTopologyEntry>
  by_element: Record<string, MaterialListItem[]>
}

export interface GenerateParams {
  x_element: string
  o_element: string
  m_element: string
  t_element: string
  b_element: string
  target_xo_distance: number
  nx: number
  ny: number
  layer_modes: string[]
  layer_alphas: number[]
  stack_sequence: string
  layer_angles: number[]
  layer_dxs: number[]
  layer_dys: number[]
  enable_t: boolean
  enable_b: boolean
  allow_non_neutral: boolean
}

export interface GenerateResult {
  success: boolean
  formula: string
  lattice: Lattice
  atom_sites: Atom[]
  atom_counts: {
    x_count: number
    o_count: number
    m_count: number
    t_count: number
    b_count: number
  }
  space_group: {
    symbol: string
    number: number
    crystal_system: string
  }
  topology: {
    base_length: number
    exact_flag: boolean
    expanded_modes: string[]
    expanded_shifts: string[]
    expanded_zs: number[]
    main_shift_sequence: string[]
    reference_grid: string
  }
}

export interface LayerAtomData {
  element: string
  fx: number
  fy: number
}

export interface LayerData {
  mode: string
  shift: string
  z: number
  theta: number
  dx: number
  dy: number
  grid_x: number
  grid_y: number
  atoms: LayerAtomData[]
}

export interface CoordinationNeighbor {
  element: string
  dx: number
  dy: number
  dz: number
  distance: number
}

export interface CoordinationEnvironment {
  cn: number
  center: { element: string; x: number; y: number; z: number }
  neighbors: CoordinationNeighbor[]
}

export interface PrimitiveCellData {
  atom_sites: Atom[]
  lattice: Lattice
  formula: string
  space_group: string
  space_group_number: number
  unique_sites: { element: string; x: number; y: number; z: number }[]
  is_neutral: boolean
}

export interface GenerateFullResult {
  structure: {
    success: boolean
    formula: string
    lattice: Lattice
    atom_sites: Atom[]
    atom_counts: { x_count: number; o_count: number; m_count: number; t_count: number; b_count: number }
    space_group: { symbol: string; number: number; crystal_system: string }
    topology: {
      base_length: number
      exact_flag: boolean
      expanded_modes: string[]
      expanded_shifts: string[]
      expanded_zs: number[]
      main_shift_sequence: string[]
      reference_grid: string
    }
  }
  layer_data: LayerData[]
  primitive: PrimitiveCellData
  coordination: { environments: CoordinationEnvironment[] }
  prototype: {
    topology_theory: {
      prototype_id: string
      input_main_shifts: string[]
      expanded_modes: string[]
      expanded_shifts: string[]
      reference_grid: string
    }
    prototype_crystallography: {
      ideal_space_group: string
      space_group_number: number
      crystal_system: string
      is_neutral: boolean
      wyckoff_signature: Record<string, string>
    }
  }
  wyckoff_signature: Record<string, string>
}

export interface LatticeTypeInfo {
  mode: string
  description: string
  base_length_formula: string
  is_main_layer: boolean
  is_x_layer: boolean
  is_m_layer: boolean
}

export interface Stats {
  total_materials: number
  unique_elements: number
  unique_formulas: number
  unique_space_groups: number
  unique_topologies: number
  raw_materials: number
  verified_materials: number
  topology_stats: Record<string, {
    total: number
    raw: number
    verified: number
  }>
  space_group_stats: Record<string, number>
  element_counts: Record<string, number>
}
