const KEY = "mbm.preferences.v1";
const empty = { favorites: [], maxTransfers: 4 };
export function loadPreferences(storage) {
  try {
    storage ??= globalThis.localStorage;
    const value = JSON.parse(storage.getItem(KEY));
    if (!value || !Array.isArray(value.favorites)) return { ...empty };
    return {
      ...(Array.isArray(value.routes)
        ? {
            routes: value.routes
              .filter(
                (r) =>
                  r &&
                  typeof r.id === "string" &&
                  typeof r.name === "string" &&
                  typeof r.code === "string",
              )
              .slice(0, 30),
          }
        : {}),
      maxTransfers: [0, 1, 2, 3, 4].includes(value.maxTransfers)
        ? value.maxTransfers
        : 4,
      favorites: value.favorites
        .filter(
          (f) =>
            typeof f.id === "string" &&
            typeof f.name === "string" &&
            f.name.trim() &&
            f.name.length <= 60 &&
            Number.isFinite(f.lat) &&
            Number.isFinite(f.lon) &&
            Math.abs(f.lat) <= 90 &&
            Math.abs(f.lon) <= 180,
        )
        .slice(0, 30),
    };
  } catch {
    return { ...empty };
  }
}
export function savePreferences(value, storage) {
  try {
    storage ??= globalThis.localStorage;
    storage.setItem(KEY, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}
