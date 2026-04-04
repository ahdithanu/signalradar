import "@testing-library/jest-dom";

// ── Mock localStorage ─────────────────────────────────────────────────────────
// jsdom provides localStorage but we need spy capabilities.
// We keep the real implementation and just ensure it's available.

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
});

// ── Suppress console.warn/error in tests unless DEBUG_TESTS is set ───────────
if (!process.env.DEBUG_TESTS) {
  const noop = () => {};
  vi.spyOn(console, "warn").mockImplementation(noop);
  vi.spyOn(console, "error").mockImplementation(noop);
}
