import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * 部署在 GitHub Pages 时站点位于子路径 /sueorange.shop/。
 * 绑定自定义域名（sueorange.shop）后，把环境变量 VITE_BASE 设为 "/" 即可。
 */
export default defineConfig(({ command }) => ({
  base: command === 'build' ? process.env.VITE_BASE ?? '/sueorange.shop/' : '/',
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
}))

