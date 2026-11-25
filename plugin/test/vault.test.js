import test from 'node:test';import assert from 'node:assert/strict';import {protectWith} from '../vault.js';
test('no plaintext fallback for unavailable keys or Linux basic_text',()=>{assert.throws(()=>protectWith(undefined).check());assert.throws(()=>protectWith({isEncryptionAvailable:()=>true,getSelectedStorageBackend:()=>'basic_text'},'linux').seal('dummy'));});
