import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { errorText, french, storedLanguage, translate } from '../src/i18n.js';
import { queriesForLanguage } from '../src/samples.js';

test('all directly referenced UI labels have French translations', () => {
  const source = readFileSync(new URL('../src/main.jsx', import.meta.url), 'utf8');
  for (const [, text] of source.matchAll(/\bt\('([^']+)'\)/g)) {
    assert.ok(french[text], `Missing French translation for ${text}`);
  }
  for (const [english, translated] of Object.entries(french)) {
    assert.equal(translate('en-CA', english), english);
    assert.equal(translate('fr-CA', english), translated);
    assert.ok(translated.trim());
  }
});

test('language persistence rejects unsupported preferences and tolerates blocked storage', () => {
  assert.equal(storedLanguage({ getItem: () => 'fr-CA' }), 'fr-CA');
  assert.equal(storedLanguage({ getItem: () => 'de' }), 'en-CA');
  assert.equal(storedLanguage({ getItem: () => null }), 'en-CA');
  assert.equal(storedLanguage({ getItem() { throw new Error('Denied'); } }), 'en-CA');
});

test('French samples translate titles and prompts without changing technical evidence', () => {
  const originals = queriesForLanguage('en-CA');
  const localized = queriesForLanguage('fr-CA');
  const tokens = [
    ['203.0.113.45', '02:14 UTC', 'CREW-PORTAL-01', 'crew-admin'],
    ['198.51.100.22', 'JDOE-LT-01', 'jdoe'],
    ['OPS-DB-02', 'data_egress_mb_per_hour', '900 MB', '99'],
  ];
  assert.equal(localized.length, originals.length);
  localized.forEach((sample, index) => {
    assert.equal(sample.id, originals[index].id);
    assert.deepEqual(sample.tools, originals[index].tools);
    assert.notEqual(sample.title, originals[index].title);
    assert.notEqual(sample.prompt, originals[index].prompt);
    for (const token of tokens[index]) assert.ok(sample.prompt.includes(token), token);
  });
  assert.deepEqual(queriesForLanguage('en-CA'), originals);
});

test('localized errors preserve correlation IDs and hide unknown upstream details', () => {
  const identifier = '00000000-0000-0000-0000-000000000001';
  const message = `The service is temporarily unavailable. Reference: ${identifier}`;
  assert.equal(errorText('en-CA', message), message);
  assert.ok(errorText('fr-CA', message).endsWith(identifier));
  assert.match(errorText('fr-CA', message), /temporairement indisponible/);
  assert.equal(errorText('fr-CA', 'Secret upstream details'), french['The request could not complete. Try again.']);
});