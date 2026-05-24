const TOKEN_KEY = "linelink_token";

let memoryToken: string | null = null;

function getStorage(): Storage | null {
  try {
    if (typeof window === "undefined" || !window.localStorage) return null;
    const testKey = "__linelink_storage_test__";
    window.localStorage.setItem(testKey, "1");
    window.localStorage.removeItem(testKey);
    return window.localStorage;
  } catch {
    return null;
  }
}

export const tokenStorage = {
  get() {
    const storage = getStorage();
    return storage?.getItem(TOKEN_KEY) ?? memoryToken;
  },
  set(token: string) {
    memoryToken = token;
    const storage = getStorage();
    storage?.setItem(TOKEN_KEY, token);
  },
  remove() {
    memoryToken = null;
    const storage = getStorage();
    storage?.removeItem(TOKEN_KEY);
  }
};
