declare module '@materialsproject/mp-react-components' {
  import type { ComponentType, ReactNode } from 'react'

  export interface CrystalToolkitSceneProps {
    /** Scene JSON produced by `crystal_toolkit`'s `get_structure_scene(...).to_json()`. */
    data?: unknown
    /** Fixed square size in px, or a CSS length such as "100%". Defaults to 500. */
    sceneSize?: number | string
    className?: string
    /** Upstream settings panel (first child) and legend (second child). */
    children?: ReactNode
    showControls?: boolean
    showExpandButton?: boolean
    showImageButton?: boolean
    showExportButton?: boolean
    showPositionButton?: boolean
    fileOptions?: string[]
    [key: string]: unknown
  }

  export const CrystalToolkitScene: ComponentType<CrystalToolkitSceneProps>
}
