import { resolve } from "node:path";

import { svelte } from '@sveltejs/vite-plugin-svelte';

import { defineConfig, loadEnv } from "vite";

import tailwindcss from '@tailwindcss/vite';


export default defineConfig(({ mode }) => {
	const env = loadEnv(mode, process.cwd(), "");

	const INPUT_DIR = "./frontend";
	const OUTPUT_DIR = "./frontend/dist";

	return {
		plugins: [
	        tailwindcss(),
			svelte()
		],
		resolve: {
			alias: {
				"@": resolve(INPUT_DIR, "js"),
				$lib: resolve(INPUT_DIR, "js/lib"),
			},
		},
		root: resolve(INPUT_DIR),
		base: "/static/",
		server: {
			host: "0.0.0.0",
			port: Number(env.DJANGO_VITE_DEV_SERVER_PORT) || 5173,
			watch: {
				usePolling: true,
			},
		},
		build: {
			manifest: "manifest.json",
			emptyOutDir: true,
			outDir: resolve(OUTPUT_DIR),
			rollupOptions: {
				input: {
					main: resolve(INPUT_DIR, "js/main.js"),
					css: resolve(INPUT_DIR, "css/main.css"),
				},
			},
		},
	};
});
