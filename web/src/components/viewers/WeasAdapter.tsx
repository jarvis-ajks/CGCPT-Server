import MolWeasIframe from './MolWeasIframe'
import entryUrl from './WeasFrame.ts?worker&url'
import type { ViewerAdapterProps } from './types'

export default function WeasAdapter(props: ViewerAdapterProps) {
  return <MolWeasIframe {...props} entryUrl={entryUrl} label="WEAS" />
}
