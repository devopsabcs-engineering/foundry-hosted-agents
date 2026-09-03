
/**
 * Node.js implementation of `util.deprecate()`; matches the public
 * `util-deprecate` package's API (used by readable-stream). Warns once per
 * unique message the first time the wrapped function is called.
 */

module.exports = deprecate;

function deprecate(fn, msg) {
  if (process.noDeprecation === true) {
    return fn;
  }

  var warned = false;
  function deprecated() {
    if (!warned) {
      if (process.throwDeprecation) {
        throw new Error(msg);
      } else if (process.traceDeprecation) {
        console.trace(msg);
      } else {
        console.warn(msg);
      }
      warned = true;
    }
    return fn.apply(this, arguments);
  }

  return deprecated;
}
