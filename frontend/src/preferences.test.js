import { test } from "node:test";
import assert from "node:assert/strict";
import { loadPreferences, savePreferences } from "./preferences.js";
test("favoritos e preferência persistem e restauram", () => {
  const store = {
    getItem() {
      return this.value;
    },
    setItem(key, value) {
      this.value = value;
    },
  };
  const value = {
    maxTransfers: 0,
    favorites: [{ id: "1", name: "Casa", lat: -23, lon: -46 }],
  };
  assert.equal(savePreferences(value, store), true);
  assert.deepEqual(loadPreferences(store), value);
});
test("armazenamento indisponível não impede uso", () => {
  const store = {
    getItem() {
      throw Error();
    },
    setItem() {
      throw Error();
    },
  };
  assert.deepEqual(loadPreferences(store).favorites, []);
  assert.equal(savePreferences({}, store), false);
});
test("dados locais inválidos são descartados", () => {
  const store = {
    getItem() {
      return JSON.stringify({
        maxTransfers: 100,
        favorites: [{ id: "x", name: "Casa", lat: 200, lon: 0 }],
      });
    },
  };
  assert.deepEqual(loadPreferences(store), { maxTransfers: 4, favorites: [] });
});
