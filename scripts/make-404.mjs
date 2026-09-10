/**
 * GitHub Pages 是纯静态托管，直接访问 /archive 会 404。
 * 把 index.html 复制成 404.html，让 Pages 在找不到路径时也交回给前端路由。
 */
import { copyFileSync, existsSync } from 'node:fs'
import { join } from 'node:path'

const distDir = join(process.cwd(), 'dist')
const indexFile = join(distDir, 'index.html')
const fallbackFile = join(distDir, '404.html')

if (!existsSync(indexFile)) {
  console.error('[make-404] 找不到 dist/index.html，请先执行 vite build')
  process.exit(1)
}

copyFileSync(indexFile, fallbackFile)
console.log('[make-404] 已生成 dist/404.html（SPA 深链接回退）')

