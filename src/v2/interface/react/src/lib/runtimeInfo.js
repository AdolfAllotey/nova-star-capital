import { fetchJson } from "./apiClient";

let cache = null;

export async function getRuntimeInfo() {
  if (cache) return cache;

  try {
    const res = await fetchJson("/dev/info", { timeoutMs: 5000 });
    if (res?.ok && res.data) {
      cache = {
        env: res.data.env || "UNKNOWN",
        apiVersion: res.data.api_version || "N/A",
        dataDir: res.data.data_dir || null,
        openaiConfigured: Boolean(res.data.openai_configured),
      };
      return cache;
    }
  } catch (e) {
    console.warn("[runtimeInfo] unable to fetch /dev/info", e);
  }

  cache = {
    env: "UNKNOWN",
    apiVersion: "N/A",
    dataDir: null,
    openaiConfigured: false,
  };
  return cache;
}
