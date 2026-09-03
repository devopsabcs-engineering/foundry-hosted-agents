'use strict';
module.exports = function immediate() {
  return setImmediate.apply(undefined, arguments);
};
