import {
  buildApiUrl,
} from "../lib/apiBase";

export async function apiGet(path) {
  const response = await fetch(
    buildApiUrl(path),
    {
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    try {
      return await response.json();
    } catch {
      return {};
    }
  }

  return response.json();
}
