import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import jsconfigPaths from "vite-jsconfig-paths";

export default defineConfig({
  plugins: [
    react(),
    jsconfigPaths(), // ✅ no enforce string here
    // If you have a custom plugin, make sure enforce is correct:
    // {
    //   name: "my-plugin",
    //   enforce: "pre", // "pre", "post" or omit
    //   configResolved(config) { ... },
    //   resolveId(id, importer) { ... }
    // }
  ],
});
