import { useEffect, useState } from 'react'
import { normalizeArchive } from '../lib/archive'
import type { ArchiveData } from '../types'

export type ArchiveState = {
  status: 'loading' | 'ready' | 'error'
  data: ArchiveData | null
  /** true 表示没找到本地抓取结果，正在展示仓库自带的演示数据 */
  isDemo: boolean
  error?: string
}

const EMPTY: ArchiveData = { generatedAt: '', posts: [] }

let cached: Promise<{ data: ArchiveData; isDemo: boolean }> | null = null

async function fetchJson(url: string): Promise<unknown> {
  const response = await fetch(url, { cache: 'no-cache' })
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`)
  }
  return response.json()
}

/**
 * 真实归档放在 public/data/shuoshuo.json（不入库，只在本地存在）；
 * 线上仓库没有这个文件，于是回退到演示数据 demo.json。
 */
export function loadArchive(): Promise<{ data: ArchiveData; isDemo: boolean }> {
  if (cached) return cached

  const base = import.meta.env.BASE_URL.endsWith('/')
    ? import.meta.env.BASE_URL
    : `${import.meta.env.BASE_URL}/`

  cached = (async () => {
    try {
      const raw = await fetchJson(`${base}data/shuoshuo.json`)
      return { data: normalizeArchive(raw), isDemo: false }
    } catch {
      const raw = await fetchJson(`${base}data/demo.json`)
      return { data: normalizeArchive(raw), isDemo: true }
    }
  })()

  return cached
}

/** 测试用：清掉缓存，避免用例之间互相污染 */
export function resetArchiveCache(): void {
  cached = null
}

export function useArchive(): ArchiveState {
  const [state, setState] = useState<ArchiveState>({
    status: 'loading',
    data: null,
    isDemo: false,
  })

  useEffect(() => {
    let alive = true

    loadArchive()
      .then((result) => {
        if (!alive) return
        setState({ status: 'ready', data: result.data, isDemo: result.isDemo })
      })
      .catch((error: unknown) => {
        if (!alive) return
        setState({
          status: 'error',
          data: EMPTY,
          isDemo: false,
          error: error instanceof Error ? error.message : String(error),
        })
      })

    return () => {
      alive = false
    }
  }, [])

  return state
}

