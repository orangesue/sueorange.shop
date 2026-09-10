/**
 * 全站文案与个人信息集中在这里，改这一个文件就能改主页。
 * 带 "占位" 字样的都是给你替换的。
 */
export const siteConfig = {
  /** 站点标题 / 浏览器标签上的名字 */
  title: 'sueorange',
  /** 主页大标题 */
  name: '你的名字（占位）',
  /** 小字副标题 */
  handle: '@sueorange',
  /** 一句话简介 */
  tagline: '把散落的时间线，收拢回自己手里。',
  /** 自我介绍段落，每项一段 */
  bio: [
    '这里是占位简介：写一两句关于你自己的话，比如在学什么、在做什么。',
    '归档页里躺着我从 QQ 空间抢救回来的说说和照片，它们本来已经被我删掉了。',
  ],
  /** 头像图片地址，留空则自动用名字首字生成圆形头像 */
  avatar: '',
  /** 社交链接，不需要的删掉即可 */
  links: [
    { label: 'GitHub', href: 'https://github.com/orangesue' },
    { label: '邮箱', href: 'mailto:orangesue098@gmail.com' },
  ],
  /** 归档页文案 */
  archive: {
    title: 'QQ 空间归档',
    intro:
      '这些内容来自我自己账号的本地抓取导出。标着「已找回」的，是从互动消息记录里捞回来的、原本已被删除的说说。',
  },
  footer: 'sueorange.shop',
}

