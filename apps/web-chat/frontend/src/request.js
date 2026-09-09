export function messageRequest(previous, conversation, text) {
  if (previous?.conversation === conversation && previous.text === text) return previous;
  return { conversation, text, key: crypto.randomUUID() };
}