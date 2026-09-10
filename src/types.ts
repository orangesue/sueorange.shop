/** 一条说说的来源通道：现存说说接口 / 互动消息列表 / 两者都有 */
export type ArchiveSource = 'msglist' | 'feeds' | 'both'

export type ArchiveComment = {
  author: string
  text: string
  createdAt?: string | null
}

/**
 * 归档数据的唯一对外契约。
 * Python 抓取工具写出的 shuoshuo.json 必须符合这个形状。
 */
export type ArchivePost = {
  id: string
  tid: string
  /** ISO 8601 时间字符串 */
  createdAt: string
  text: string
  /** 本地相对路径（data/images/...）或仍未下载的 http 地址 */
  images: string[]
  comments: ArchiveComment[]
  likes: number
  /** true 表示这条只存在于互动消息列表里，即原说说已被删除 */
  deleted: boolean
  source: ArchiveSource
  /** 转发/引用的原文，没有则为 null */
  repost?: string | null
}

export type ArchiveData = {
  generatedAt: string
  uin?: string
  posts: ArchivePost[]
}

export type ArchiveFilter = 'all' | 'deleted' | 'withImages'

