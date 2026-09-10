import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Archive from './pages/Archive'
import Home from './pages/Home'

/** 站点部署在子路径（GitHub Pages）时，路由也要跟着带上前缀 */
function routerBasename(): string {
  const base = import.meta.env.BASE_URL || '/'
  return base.endsWith('/') && base.length > 1 ? base.slice(0, -1) : base
}

export default function App() {
  return (
    <BrowserRouter basename={routerBasename()}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/archive" element={<Archive />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

