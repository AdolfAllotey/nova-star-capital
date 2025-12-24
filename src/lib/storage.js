const safe = (() => {
  try {
    const k = "__test__"
    window.localStorage.setItem(k, "1")
    window.localStorage.removeItem(k)
    return window.localStorage
  } catch { return null }
})()

export const Storage = {
  get(k){ try { return safe ? safe.getItem(k) : null } catch { return null } },
  set(k,v){ try { if (safe) safe.setItem(k,v) } catch {} },
  del(k){ try { if (safe) safe.removeItem(k) } catch {} },
}
