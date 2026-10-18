import test from 'node:test';
import assert from 'node:assert/strict';
import {decodeCatalogue} from './stopCatalog.js';
test('decodes signed coordinate deltas and preserves IDs and names',async()=>{
 const m=await decodeCatalogue({version:1,scale:100000,revision:'a',rows:[['001',-2355000,-4673000,'Casa'],['002',5,-9,'Trabalho']]});
 assert.deepEqual(m.get('002'),{id:'002',lat:-23.54995,lon:-46.73009,name:'Trabalho'});
});
test('rejects incompatible versions and invalid coordinates',async()=>{
 await assert.rejects(decodeCatalogue({version:2}));
 await assert.rejects(decodeCatalogue({version:1,scale:100000,revision:'a',rows:[['x',9100000,0,'x']]}));
});
