import {
  buildApiUrl,
} from "./apiBase";

export async function safeFetch(path, options = {}) {
  const response = await fetch(
    buildApiUrl(path),
    {
      ...options,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    }
  );

  if (!response.ok) {
    const text = await response
      .text()
      .catch(() => "");

    throw new Error(
      `HTTP ${response.status} on ${path}` +
        (
          text
            ? ` — ${text.slice(0, 200)}`
            : ""
        )
    );
  }

  const contentType =
    response.headers.get("content-type") || "";

  if (
    contentType.includes(
      "application/json"
    )
  ) {
    return response.json();
  }

  return response.text();
}
