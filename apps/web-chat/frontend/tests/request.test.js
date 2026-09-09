import { test } from 'node:test';
import assert from 'node:assert/strict';
import { messageRequest } from '../src/request.js';

test('retries reuse keys only for matching conversation and text', () => {
  const original = messageRequest(null, 'first', 'Hello');
  assert.equal(messageRequest(original, 'first', 'Hello'), original);
  assert.notEqual(messageRequest(original, 'second', 'Hello').key, original.key);
  assert.notEqual(messageRequest(original, 'first', 'Changed').key, original.key);
  assert.notEqual(messageRequest(null, 'first', 'Hello').key, original.key);
});