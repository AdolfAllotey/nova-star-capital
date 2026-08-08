// Canonical JSON client for NSC React.

import {
  API_BASE,
  buildApiUrl,
} from "./apiBase";

async function readJsonSafe(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function fetchJson(path, options = {}) {
  const {
    timeoutMs = 12000,
    ...fetchOptions
  } = options || {};

  const controller = new AbortController();
  const timer = setTimeout(
    () => controller.abort(),
    timeoutMs
  );

  try {
    const response = await fetch(
      buildApiUrl(path),
      {
        ...fetchOptions,
        signal: controller.signal,
        cache: fetchOptions.cache || "no-store",
        headers: {
          Accept: "application/json",
          ...(fetchOptions.headers || {}),
        },
      }
    );

    const data = await readJsonSafe(response);

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        error:
          data ||
          {
            detail:
              response.statusText ||
              "HTTP request failed",
          },
      };
    }

    return {
      ok: true,
      status: response.status,
      data,
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      error: {
        message: String(
          error?.message ||
            error ||
            "fetch error"
        ),
      },
    };
  } finally {
    clearTimeout(timer);
  }
}

export function buildUrl(path) {
  return buildApiUrl(path);
}

export function apiUrl(path) {
  return buildApiUrl(path);
}

export {
  API_BASE,
};
