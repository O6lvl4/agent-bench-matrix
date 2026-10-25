import test from 'node:test';
import assert from 'node:assert/strict';
import { computeMemory, electricity, candidateFit } from '../docs/cost.js';
const profile = { artifact: {bytes: 4 * 2**30}, config: {layers:32,kv_heads:8,head_dim:128}, runtime: ['llama.cpp CUDA', 'llama.cpp Metal'] };

test('weights use bytes/GiB and KV uses both K and V with f16', () => {
  const m = computeMemory(profile,4096);
  assert.equal(m.weightsGiB,4);
  assert.equal(m.kvGiB,0.5);
  assert.equal(m.runtimeGiB,2);
  assert.equal(m.minimumGiB,6.5*1.1);
  assert.equal(m.roomyGiB,6.5*1.25);
});
test('doubling context doubles KV, not weight allocation', () => {
  const a=computeMemory(profile,4096), b=computeMemory(profile,8192);
  assert.equal(b.kvGiB,a.kvGiB*2);
  assert.equal(b.weightsGiB,a.weightsGiB);
});
test('invalid model configuration produces no estimate', () => {
  assert.equal(computeMemory({},4096),null);
  assert.equal(computeMemory({...profile,artifact:{bytes:NaN}},4096),null);
});
test('fits one device only; computer OS reserve reduces usable memory', () => {
  const hw={memory_gib:8,reserve_gib:0,kind:'gpu',runtime:'llama.cpp CUDA'};
  assert.equal(candidateFit(profile,hw,4096).minimum,true);
  assert.equal(candidateFit(profile,hw,4096).roomy,false);
  const computer={...hw,kind:'computer',reserve_gib:2};
  assert.equal(candidateFit(profile,computer,4096).minimum,false);
});
test('incompatible runtime is not a local candidate', () => {
  assert.equal(candidateFit(profile,{memory_gib:80,reserve_gib:0,runtime:'unverified'},4096).compatible,false);
});
test('electricity is user assumption, zero valid and nonfinite invalid', () => {
  assert.equal(electricity(300,2,30,31),558);
  assert.equal(electricity(0,2,30,31),0);
  assert.equal(electricity(-1,2,30,31),null);
  assert.equal(electricity(Infinity,2,30,31),null);
});
