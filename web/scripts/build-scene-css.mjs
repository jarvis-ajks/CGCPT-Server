/**
 * Regenerates the scoped stylesheet used by the Materials Project viewer.
 *
 * The upstream package ships the scene components as `.css`/`.less` sources but
 * its published `dist` bundle contains no CSS, and the components are written
 * against Bulma (see the mp-react-components README). To use the upstream
 * Crystal Toolkit styles without letting Bulma's global styles leak into
 * the CGCPT Tailwind UI, this script prefixes every selector with
 * `.cgcpt-scene` and writes a single vendored stylesheet.
 *
 * Usage (from web/): node scripts/build-scene-css.mjs
 */
import fs from 'node:fs'
import path from 'node:path'
import postcss from 'postcss'
import prefixSelector from 'postcss-prefix-selector'

const webRoot = path.resolve(import.meta.dirname, '..')
const pkgRoot = path.join(webRoot, 'node_modules/@materialsproject/mp-react-components')
const pkgVersion = JSON.parse(fs.readFileSync(path.join(pkgRoot, 'package.json'), 'utf8')).version
const bulmaVersion = JSON.parse(
  fs.readFileSync(path.join(webRoot, 'node_modules/bulma/package.json'), 'utf8'),
).version

const sources = [
  ['bulma', path.join(webRoot, 'node_modules/bulma/css/bulma.min.css')],
  ['ButtonBar', path.join(pkgRoot, 'src/components/data-display/ButtonBar/ButtonBar.css')],
  ['Enlargeable', path.join(pkgRoot, 'src/components/data-display/Enlargeable/Enlargeable.css')],
  ['ModalCloseButton', path.join(pkgRoot, 'src/components/data-display/Modal/ModalCloseButton/ModalCloseButton.css')],
  ['Tooltip', path.join(pkgRoot, 'src/components/data-display/Tooltip/Tooltip.css')],
  ['RangeSlider', path.join(pkgRoot, 'src/components/data-entry/RangeSlider/RangeSlider.css')],
  ['CrystalToolkitScene', path.join(pkgRoot, 'src/components/crystal-toolkit/CrystalToolkitScene/CrystalToolkitScene.less')],
]

const SCOPE = '.cgcpt-scene'

const base = `
/* Bulma resets these on <html>/<body>; mirror what the viewer inherits. */
${SCOPE} {
  box-sizing: border-box;
  background: #fff;
  color: #4a4a4a;
  font-family: BlinkMacSystemFont, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 16px;
  font-weight: 400;
  line-height: 1.5;
}
${SCOPE} *,
${SCOPE} *::before,
${SCOPE} *::after {
  box-sizing: inherit;
}
`

const render = async (label, file) => {
  const css = fs.readFileSync(file, 'utf8')
  const result = await postcss([
    prefixSelector({
      prefix: SCOPE,
      // Keyframe steps are not selectors and must not be rewritten.
      exclude: [/^from$/, /^to$/, /^\d+%$/],
    }),
  ]).process(css, { from: file })
  return `/* ${label} */\n${result.css}\n`
}

const parts = []
for (const [label, file] of sources) {
  parts.push(await render(label, file))
}

const header = `/*
 * GENERATED FILE - do not edit by hand.
 * Source: @materialsproject/mp-react-components ${pkgVersion} + Bulma ${bulmaVersion},
 * prefixed with ${SCOPE}. Regenerate with: node scripts/build-scene-css.mjs
 */
`

const out = path.join(webRoot, 'src/components/mp/scene-vendor.css')
fs.writeFileSync(out, `${header}${base}\n${parts.join('\n')}`)
console.log(`wrote ${path.relative(webRoot, out)} (${fs.statSync(out).size} bytes)`)
