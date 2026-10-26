import { useEffect, useRef } from 'react'
import { flushSync, mount, unmount } from 'svelte'
import matterVizStyles from 'matterviz/app.css?inline'
import MatterVizMount from './MatterVizMount.svelte'
import type { ViewerAdapterProps } from './types'

export default function MatterVizAdapter({ cifText, size }: ViewerAdapterProps) {
  const hostRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const host = hostRef.current
    if (!host) return

    // Svelte's injected component styles follow the mount anchor into this root.
    // The Vite Svelte plugin must use compilerOptions.css = 'injected'.
    const shadow = host.shadowRoot ?? host.attachShadow({ mode: 'open' })
    const styles = document.createElement('style')
    styles.textContent = `${matterVizStyles}\n:host { display:block; color-scheme:light; font-family:system-ui,sans-serif; } * { box-sizing:border-box; } .matterviz-mount { width:100%; height:100%; overflow:hidden; }`
    const target = document.createElement('div')
    target.className = 'matterviz-mount'
    shadow.replaceChildren(styles, target)

    let instance: Record<string, unknown> | undefined
    try {
      // Flush the initial effects so synchronous setup errors are visible too.
      flushSync(() => {
        instance = mount(MatterVizMount, { target, props: { cifText } })
      })
    } catch (error) {
      if (instance) {
        void unmount(instance, { outro: false })
        instance = undefined
      }
      target.replaceChildren()
      const message = document.createElement('div')
      message.setAttribute('role', 'alert')
      message.style.cssText = 'padding:16px;color:#b91c1c;overflow:auto'
      message.textContent = `MatterViz could not render this CIF: ${error instanceof Error ? error.message : String(error)}`
      target.append(message)
    }

    return () => {
      // No outro: Svelte destroys Threlte's renderer, geometry and event effects
      // before the next CIF mounts, including React StrictMode's setup replay.
      if (instance) void unmount(instance, { outro: false })
      target.remove()
      styles.remove()
    }
  }, [cifText])

  return <div ref={hostRef} style={{ width: size, height: size, overflow: 'hidden' }} aria-label="MatterViz crystal structure viewer" />
}
