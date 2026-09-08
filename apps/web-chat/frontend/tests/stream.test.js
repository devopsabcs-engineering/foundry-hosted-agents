import { test } from 'node:test';
import assert from 'node:assert/strict';
import { consumeResponse } from '../src/stream.js';

function stream(text) {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream({
    start(controller) {
      for (const byte of bytes) controller.enqueue(new Uint8Array([byte]));
      controller.close();
    },
  });
}

test('parses split UTF-8 and ignores heartbeat comments', async () => {
  const events = [];
  await consumeResponse(stream(': keepalive\n\ndata: {"type":"answer","text":"caf\u00e9"}\n\ndata: {"type":"done"}\n\n'), event => events.push(event));
  assert.equal(events[0].text, 'caf\u00e9');
  assert.equal(events.length, 2);
});

test('rejects truncation without completion', async () => {
  await assert.rejects(consumeResponse(stream('data: {"type":"status"}\n\n'), () => {}), /interrupted/);
});

test('surfaces safe server error with correlation reference', async () => {
  await assert.rejects(consumeResponse(stream('data: {"type":"error","text":"Unavailable","requestId":"123"}\n\n'), () => {}), /Unavailable.*123/);
});