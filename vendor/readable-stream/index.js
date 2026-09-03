// Delegates to Node's built-in 'stream' module, which exposes the same
// Readable/Writable/Duplex/Transform/PassThrough API this package normally
// polyfills. Sufficient for jszip's Node-only usage in build-deck.js.
module.exports = require('stream');
