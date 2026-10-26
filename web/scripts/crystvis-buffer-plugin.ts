import type { Plugin } from 'vite'

// load-bmfont is an indirect dependency of crystvis-js. Its browser entry and
// binary-header helper assume Browserify supplies Buffer, including at module
// evaluation time. Inject a lexical import into those CommonJS modules only;
// never assign Buffer to window/globalThis or change any other viewer's realm.
// Register a fresh instance in BOTH Vite's plugins and
// optimizeDeps.rolldownOptions.plugins so dev and production agree.
export function crystvisBufferPlugin(): Plugin {
  return {
    name: 'crystvis-local-buffer',
    enforce: 'pre',
    transform(source, id) {
      if (!/[\\/]node_modules[\\/]load-bmfont[\\/](?:browser\.js|lib[\\/]is-binary\.js)(?:\?.*)?$/.test(id)) {
        return null
      }
      return {
        // Keep CommonJS syntax so dependency conversion can discover and bundle
        // the explicitly selected browser Buffer package (not Node's builtin).
        code: `var Buffer = require('buffer/').Buffer;\n${source}`,
        map: null,
      }
    },
  }
}
