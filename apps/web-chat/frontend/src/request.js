export function messageRequest(previous, conversation, text, language = 'en-CA') {
  if (previous?.conversation === conversation && previous.text === text && previous.language === language) return previous;
  return { conversation, text, language, key: crypto.randomUUID() };
}