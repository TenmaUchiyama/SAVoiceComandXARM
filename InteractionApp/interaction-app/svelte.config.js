import adapter from "@sveltejs/adapter-auto";

/** @type {import('@sveltejs/kit').Config} */
const config = {
  kit: {
    adapter: adapter(),
    // SPA mode — disable SSR
    csp: { mode: "auto" },
  },
};

export default config;
