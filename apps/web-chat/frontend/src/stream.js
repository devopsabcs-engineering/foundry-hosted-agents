import { createParser } from 'eventsource-parser';

export async function consumeResponse(body, onEvent) {
  let completed = false;
  const parser = createParser({
    onEvent(event) {
      const payload = JSON.parse(event.data);
      if (payload.type === 'error') {
        throw new Error(`${payload.text} Reference: ${payload.requestId}`);
      }
      if (payload.type === 'done') completed = true;
      onEvent(payload);
    },
    onError(error) { throw error; },
  });
  const reader = body.getReader();
  const decoder = new TextDecoder();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      parser.feed(decoder.decode(value, { stream: true }));
    }
    parser.feed(decoder.decode());
    if (!completed) throw new Error('The response was interrupted. Try again.');
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}