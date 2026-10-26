import MolWeasIframe from './MolWeasIframe'
import entryUrl from './ThreeDmolFrame.ts?worker&url'
import type { ViewerAdapterProps } from './types'

export default function ThreeDmolAdapter(props: ViewerAdapterProps) {
  return <MolWeasIframe {...props} entryUrl={entryUrl} label="3Dmol.js" />
}
