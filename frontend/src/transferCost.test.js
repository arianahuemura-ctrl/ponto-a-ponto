import test from 'node:test';
import assert from 'node:assert/strict';
import {transferCostLabel,withinTransferPolicy} from './transferCost.js';

test('expressa terços exatos sem confundir custo com trocas físicas',()=>{
  assert.equal(transferCostLabel({transfer_cost_units:1,transfers:1}),'⅓');
  assert.equal(transferCostLabel({transfer_cost_units:4,transfers:2}),'1⅓');
  assert.equal(transferCostLabel({transfer_cost_units:12,transfers:12}),'4');
  assert.equal(transferCostLabel({transfers:0}),'0');
});
test('descarta seleção anterior quando um novo mínimo reduz o limite',()=>{
  const policy={maximum_allowed:4/3};
  assert.equal(withinTransferPolicy({transfer_cost_units:4},policy),true);
  assert.equal(withinTransferPolicy({transfer_cost_units:5},policy),false);
  assert.equal(withinTransferPolicy({transfers:2},policy),false);
  assert.equal(withinTransferPolicy(null,policy),true);
});
