import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..')
const packages = [
  ['matterviz', 'license'],
  ['matterviz/node_modules/svelte-widgets', 'license'],
  ['svelte', 'LICENSE.md'],
  ['megane-viewer', 'LICENSE'],
  ['cifvis', 'LICENSE.md'],
  ['@ccp-nc/crystvis-js', 'LICENSE'],
  ['3dmol', 'LICENSE'],
  ['weas', 'LICENSE'],
  ['three', 'LICENSE'],
  ['dat.gui', 'LICENSE'],
  ['buffer', 'LICENSE'],
  ['@materialsproject/mp-react-components/node_modules/use-resize-observer', 'LICENSE'],
]
const sections = ['CGCPT browser comparison viewers — upstream license texts.\nMaterials Project remains the default; comparison engines are independent.\nCifVis source (unmodified): https://registry.npmjs.org/cifvis/-/cifvis-0.9.4.tgz\n']
for (const [directory, license] of packages) {
  const base = path.join(root, 'node_modules', directory)
  const metadata = JSON.parse(fs.readFileSync(path.join(base, 'package.json'), 'utf8'))
  sections.push(`${metadata.name} ${metadata.version}\n${'='.repeat(72)}\n${fs.readFileSync(path.join(base, license), 'utf8')}`)
}
sections.push(`WEAS bundled dependency notices\n${fs.readFileSync(path.join(root, 'node_modules/weas/dist/weas.mjs.LICENSE.txt'), 'utf8')}`)
fs.writeFileSync(path.join(root, 'public/viewer-licenses.txt'), sections.join('\n\n'))
console.log('Generated public/viewer-licenses.txt')
