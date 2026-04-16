/**
 * data-store.js — DataStore singleton (Model layer, ARCH-4)
 *
 * Provides TTL-based caching, request coalescing, AbortController
 * race-condition protection, and retry logic for data.json.
 *
 * Cross-iframe sharing: initialized on window.top so all sub-pages
 * served from the same origin share one cache instance.
 */
(function () {
  // ── Shared root: use window.top when inside an iframe ────────────────────
  const root = (window.top && window.top !== window) ? window.top : window;

  if (root.DataStore) {
    // Already initialized — expose reference on this frame and exit
    if (window !== root) window.DataStore = root.DataStore;
    return;
  }

  // ── DataStore definition ──────────────────────────────────────────────────
  const DS = {
    _cache    : null,
    _ttl      : 60_000,   // 60 s — aligned with setInterval in script.js
    _lastFetch: 0,
    _listeners: [],
    _pending  : null,     // in-flight Promise (for coalescing)
    _controller: null,    // AbortController for the active fetch

    /**
     * get(force?)
     * Returns cached data if still fresh, otherwise fetches.
     * Concurrent callers during a fetch receive the same Promise.
     *
     * @param {boolean} force - bypass TTL and force a new network request
     * @returns {Promise<object>} parsed data.json
     */
    async get(force = false) {
      const isStale = (Date.now() - this._lastFetch) > this._ttl;

      // Return cache when fresh and not forced
      if (!force && !isStale && this._cache !== null) {
        return this._cache;
      }

      // Coalesce: return existing in-flight promise
      if (this._pending) {
        return this._pending;
      }

      // Abort any zombie controller from a previously cancelled request
      if (this._controller) {
        this._controller.abort();
        this._controller = null;
      }

      this._pending = this._fetchWithRetry()
        .then(data => {
          this._cache     = data;
          this._lastFetch = Date.now();
          this._notify(data);
          return data;
        })
        .finally(() => {
          this._pending    = null;
          this._controller = null;
        });

      return this._pending;
    },

    /**
     * refresh()
     * Force a new fetch regardless of TTL, then notify subscribers.
     */
    refresh() {
      return this.get(true);
    },

    /**
     * subscribe(fn)
     * Register a listener called with (data) after every successful fetch.
     * @returns {function} call to unsubscribe
     */
    subscribe(fn) {
      this._listeners.push(fn);
      return () => {
        this._listeners = this._listeners.filter(l => l !== fn);
      };
    },

    // ── Private ─────────────────────────────────────────────────────────────

    _notify(data) {
      this._listeners.forEach(fn => {
        try { fn(data); } catch (e) { console.warn('[DataStore] listener error', e); }
      });
    },

    async _fetchWithRetry(attempt = 0) {
      const MAX_RETRIES = 2;
      const BACKOFF     = [500, 1000]; // ms

      this._controller = new AbortController();
      try {
        const res = await fetch('data.json?t=' + Date.now(), {
          signal: this._controller.signal,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (err) {
        if (err.name === 'AbortError') throw err; // intentional cancel — propagate
        if (attempt < MAX_RETRIES) {
          console.warn(`[DataStore] fetch failed (attempt ${attempt + 1}), retrying...`, err.message);
          await new Promise(r => setTimeout(r, BACKOFF[attempt]));
          return this._fetchWithRetry(attempt + 1);
        }
        throw err;
      }
    },
  };

  root.DataStore = DS;
  if (window !== root) window.DataStore = DS;
})();
