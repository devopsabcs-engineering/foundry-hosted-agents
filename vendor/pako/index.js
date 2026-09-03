'use strict';
// jszip only calls pako.deflateRaw(data, { level }) and pako.inflateRaw(data).
// Node's native zlib provides the same raw-deflate codec pako reimplements in pure JS,
// so we delegate to it directly instead of shipping a JS port.
const zlib = require('zlib');

function toBuffer(data) {
  return Buffer.isBuffer(data) ? data : Buffer.from(data);
}

exports.deflateRaw = function deflateRaw(data, options) {
  const opts = {};
  if (options && typeof options.level === 'number') opts.level = options.level;
  return new Uint8Array(zlib.deflateRawSync(toBuffer(data), opts));
};

exports.inflateRaw = function inflateRaw(data) {
  return new Uint8Array(zlib.inflateRawSync(toBuffer(data)));
};

exports.deflate = function deflate(data, options) {
  const opts = {};
  if (options && typeof options.level === 'number') opts.level = options.level;
  return new Uint8Array(zlib.deflateSync(toBuffer(data), opts));
};

exports.inflate = function inflate(data) {
  return new Uint8Array(zlib.inflateSync(toBuffer(data)));
};
