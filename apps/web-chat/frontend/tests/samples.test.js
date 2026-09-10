import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { sampleQueries } from '../src/samples.js';

test('demo queries exactly match reviewed golden scenarios', () => {
  const dataset = readFileSync(new URL('../../../../eval/golden-dataset.jsonl', import.meta.url), 'utf8')
    .trim().split('\n').map(line => JSON.parse(line));
  assert.equal(sampleQueries.length, 3);
  assert.equal(new Set(sampleQueries.map(sample => sample.id)).size, 3);
  for (const sample of sampleQueries) {
    const scenario = dataset.find(record => record.id === sample.id);
    assert.equal(sample.prompt, scenario.input.messages[0].content);
    assert.ok(sample.prompt.length < 8000);
    assert.ok(sample.tools.length >= 3);
  }
});