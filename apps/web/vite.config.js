import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
    plugins: [react()],
    server: {
        proxy: {
            // /api で始まるリクエストを、api サービスへ中継する
            "/api": "http://api:8000",
        },
    },
});
