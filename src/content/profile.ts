/**
 * 全站内容都在这一个文件里。
 * 想改文案、加项目、换联系方式，只改这里就够了，不用动页面代码。
 * 带「待确认」注释的地方是我拿不准的事实，你核对一下。
 */

export type LinkItem = { label: string; href: string; note?: string }

export type SkillGroup = {
  group: string
  items: string[]
}

export type ExperienceItem = {
  org: string
  role: string
  period: string
  points: string[]
}

export type Project = {
  slug: string
  name: string
  subtitle: string
  /** 简历里的标准写法：项目名 | 角色 | 赛事/来源 */
  role: string
  period: string
  tags: string[]
  summary: string
  metrics: { value: string; label: string }[]
  links: LinkItem[]
  detail: {
    background: string
    contributions: string[]
    tech: string[]
    outcomes: string[]
  }
  /** 需要你确认的事实，会以小字显示在详情页 */
  todo?: string
}

export const profile = {
  name: '苏佳慧',
  enName: 'Su Jiahui',
  handle: '@sueorange',
  headline: '北京师范大学 · 人工智能专业（本科 2024–2028）',
  /** 一句话定位，出现在首屏最大那行字下面 */
  tagline: '把一个想法从零做到能被人打开、能被人用起来。',
  intro: [
    '人工智能专业在读，做过两件我自己比较满意的事：一件是给助农茶油品牌做了一整套数字化平台（小程序 + 网站 + 溯源 + AI 客服），另一件是把 QQ 空间里已经删掉的说说和照片从服务器残留的互动痕迹里捞了回来。',
    '我喜欢那种「看起来做不完、但拆开之后一步步真能做完」的事情，也习惯把过程写下来复盘——这个网站本身就是我做出来的东西之一。',
  ],
  /** 头像图片地址，留空就用名字首字生成 */
  avatar: '',
  links: [
    { label: 'GitHub', href: 'https://github.com/orangesue' },
    { label: '邮箱', href: 'mailto:202411079846@mail.bnu.edu.cn' },
    { label: 'QQ 空间归档演示', href: '/archive', note: '本站可交互' },
  ] as LinkItem[],
  /** 首屏下方的数字亮点 */
  highlights: [
    { value: '2', label: '完整落地的项目' },
    { value: '788', label: '归档的 QQ 空间说说' },
    { value: '88', label: '项自动化自检通过' },
    { value: '6', label: '组技术自检体系' },
  ],
  skills: [
    {
      group: '编程语言',
      items: ['Python', 'C++', 'Java', 'JavaScript', 'HTML / CSS', 'SQL'],
    },
    {
      group: '工程与工具',
      items: ['Node.js', 'React + TypeScript', '微信小程序', 'VS Code 远程开发（SSH）', '虚拟机部署', 'PowerShell / Shell 脚本'],
    },
    {
      group: '数据与后端',
      items: ['SQLite / MySQL', 'Redis 缓存', '接口逆向与数据抓取', 'ECDSA 数字签名', 'SHA-256 哈希链'],
    },
    {
      group: 'AI 协同',
      items: ['LLM 辅助开发与调试', '规则引擎 + 大模型混合客服', '技术文档阅读与方法沉淀'],
    },
  ] as SkillGroup[],
  experiences: [
    {
      org: 'BlockPulse Digital Asset Management',
      role: '技术实习生',
      period: '2025.09 – 2026.02',
      points: [
        '独立完成公司内工作环境的构建与优化：系统重装、开发工具链配置、环境调试，提升设备运行效率与工作流顺畅度。',
        '通过虚拟化平台搭建多操作系统环境，掌握虚拟机部署、网络配置与资源隔离，为开发与测试提供灵活的实验环境。',
        '熟练使用 PowerShell 与命令行工具进行系统管理与自动化操作，提高环境配置效率与可重复性。',
        '配置 VS Code 远程开发环境（SSH + 扩展插件），实现跨设备的高效开发与调试。',
      ],
    },
    {
      org: '中国移动 · 寒假线上研学冬令营',
      role: '研学学员',
      period: '2026.01 – 2026.03',
      points: [
        '参与「高泛化性 AI 生成视觉内容检测与取证技术研究」项目，针对前沿 AI 生成内容的伪造特征做技术调研与分析。',
        '探索多模态大模型（MLLM）与卷积神经网络（CNN）在图像篡改检测与内容取证中的应用，研究提升检测模型泛化性的方案。',
        '梳理相关学术文献与工程前沿，参与编写技术研究报告，沉淀对抗样本与内容安全方向的理论基础。',
      ],
    },
  ] as ExperienceItem[],
  campus: [
    '学院（社团）宣传部门成员：撰写多篇宣传文稿并参与宣发，提升组织知名度与影响力。',
    '担任宣传委员、班级联络员：负责信息整合、发布与反馈，保证信息传递准确及时。',
    '校合唱团成员：多次参与大型演出，积累舞台经验与团队协作能力。',
    '多次参与大型活动志愿服务，积累现场协调经验。',
  ],
  projects: [
    {
      slug: 'chayaya',
      name: '茶芽芽 · 浒口茶油助农数字化平台',
      subtitle: '「浒口茶油 · 乡味新生」助农茶油全链创富计划',
      // 待确认：赛事全称与级别（大创/国创立项 or 三创赛获奖），核对后改这一行
      role: '核心成员 · 数字化平台开发 | 大学生创新创业训练计划项目',
      period: '2026',
      tags: ['微信小程序', 'Node.js', '一物一码溯源', 'AI 智能客服'],
      summary:
        '把项目报告书里「技术方案设计」那几页纸，落地成一套真的能扫码、能下单、能问诊的系统：商品购买、一物一码区块链式溯源、AI 智能客服，另附可在无服务器环境打开的静态演示站。',
      metrics: [
        { value: '88', label: '项自检全部通过' },
        { value: '13', label: '个小程序页面' },
        { value: '100', label: '个一物一码' },
      ],
      links: [
        { label: '在线演示（GitHub Pages）', href: 'https://orangesue.github.io/chayaya-mall/' },
        { label: '项目仓库', href: 'https://github.com/orangesue' },
      ] as LinkItem[],
      detail: {
        background:
          '团队为湖南郴州浒口村的山茶油做助农品牌「茶芽芽」，主推婴儿山茶抚触油。项目报告里规划了多渠道线上商城与扫码溯源体系，但停留在文字描述；我负责把这部分真正实现出来。',
        contributions: [
          '从零实现整套后端：极简 HTTP 服务、商品/购物车/订单/支付/售后、一物一码分配与核销、管理后台。',
          '实现一物一码溯源：每个单品生成唯一溯源码，用 ECDSA（secp256k1）对「溯源码|批次号|检验编号」签名，扫码时服务端验签，篡改即判为仿制品；全流程节点用 SHA-256 哈希链串联，查询时逐节点重算比对。',
          '实现 AI 智能客服：五类意图识别 + 多轮槽位追问（月龄/症状/时长/部位）+ 五大类标准应答 + 情绪识别转人工；并为「婴儿能不能用」这一高风险场景设计了四级分级与强制免责。',
          '把小程序工程导出为可导入微信开发者工具的完整项目（13 个页面），并做了一套离线静态演示站，让评委扫码即可体验全流程。',
        ],
        tech: [
          'Node.js 后端，驱动抽象层让业务代码在 node:sqlite ↔ MySQL、内存缓存 ↔ Redis 之间无感切换',
          '前端原生 ES Module + 路由/状态管理，零构建即可运行',
          'ECDSA 签名 + SHA-256 哈希链 + 二维码生成与独立解码器回读校验',
          '规则引擎为主的对话系统，大模型仅做话术润色、不参与安全判定',
          'GitHub Actions 自动构建并发布静态演示站',
        ],
        outcomes: [
          '端到端业务链路 27/27、前端页面渲染 11/11、二维码链路 5/5、静态托管 20/20、全站链接巡检 15/15、AI 规则用例 10/10 —— 共 88 项自动化自检全部通过。',
          '另附两个网页版实验室（溯源实验室 / AI 实验室），可现场演示签名、验签、篡改拦截与哈希链校验。',
          '项目已与村合作社签订原料采购协议，商品在主流平台上线，小程序与静态演示站均可访问。',
        ],
      },
      todo: '赛事全称与获奖级别我拿不准（大创立项？三创赛获奖？），确认后改 profile.ts 里的 role 一行即可。',
    },
    {
      slug: 'qzone-archive',
      name: 'QQ 空间归档与已删除说说恢复',
      subtitle: '把自己散落的时间线，收回自己手里',
      role: '独立开发 | 个人项目',
      period: '2026.09',
      tags: ['Python', 'React + TypeScript', '接口逆向', '数据归档'],
      summary:
        '一套跑在本地的归档工具 + 一个展示站点：把 QQ 空间的说说、评论、配图完整备份下来，并从服务器残留的互动记录里找回已经删掉的内容。',
      metrics: [
        { value: '788', label: '条说说归档' },
        { value: '1701', label: '张配图落盘' },
        { value: '2020–2026', label: '时间跨度' },
      ],
      links: [
        { label: '在线演示（本站）', href: '/archive', note: '时间线可交互' },
        { label: '源码', href: 'https://github.com/orangesue/sueorange.shop' },
      ] as LinkItem[],
      detail: {
        background:
          'QQ 空间没有官方的完整导出，删掉的内容更是直接消失。市面上星标最高的几个开源项目在 2026 年 9 月集体归档停更，我想知道自己账号里那些被删掉的说说还能不能救回来。',
        contributions: [
          '从零实现抓取工具：扫码/粘贴 Cookie 登录态、分页抓取、按 tid 合并去重、配图本地化、断点续传与限流退避。',
          '逆向并横向对比多个私有接口，定位出「统一时间线」接口的正确参数组合与翻页游标，让时间轴能一路翻回过去。',
          '用互动记录里的「作者 QQ 号 + 说说正文」判定哪些内容属于自己、哪些已被删除——这一层身份校验是准确性的关键。',
          '解决一串真实工程问题：图片防盗链（Referer 判定）、GBK/UTF-8 混编、JS 对象字面量里的 undefined/NaN、腾讯的 network busy 限流。',
          '前端用 React + TypeScript 做了时间线、关键词搜索、仅看已找回、图片灯箱与统计条。',
        ],
        tech: [
          'Python（requests + BeautifulSoup + JSON5）抓取与解析，pytest 覆盖解析与合并规则',
          'Vite + React + TypeScript + Tailwind 构建展示站',
          'GitHub Actions 自动构建并发布到 GitHub Pages',
          '隐私优先：登录凭据与真实数据全部本地保存，仓库里只有代码与演示数据',
        ],
        outcomes: [
          '归档 788 条说说、1701 张配图、1449 条评论，时间跨度 2020–2026。',
          '摸清并写下了这类接口的能力边界：互动记录只保留约一年半，无互动痕迹的已删除内容无法恢复。',
          '站点已上线（GitHub Pages），真实数据不上传公网。',
        ],
      },
    },
    {
      slug: 'portfolio',
      name: '个人作品集网站（本站）',
      subtitle: '把做过的事讲清楚，本身就是一种能力',
      role: '独立开发 | 个人项目',
      period: '2026',
      tags: ['React', 'TypeScript', 'Tailwind', 'GitHub Actions'],
      summary:
        '你现在正在看的这个站点：配置驱动的内容层、响应式布局、自动部署，以及把 QQ 空间归档做成可交互的在线演示。',
      metrics: [
        { value: '2', label: '条公开演示路径' },
        { value: '100%', label: '静态托管' },
      ],
      links: [{ label: '源码', href: 'https://github.com/orangesue/sueorange.shop' }] as LinkItem[],
      detail: {
        background: '简历上的经历是干瘪的，作品需要能点开看。我想要一个能持续更新、不依赖服务器、随时能分享出去的展示平台。',
        contributions: [
          '设计并实现作品集页面结构：首屏定位、数字亮点、项目卡与详情页、技能与经历。',
          '内容层与展示层分离：所有文案集中在 profile.ts，改内容不用碰页面代码。',
          '配置 GitHub Actions，推送到主分支后自动构建并部署到 GitHub Pages。',
          '把 QQ 空间归档项目接成站内的可交互演示页。',
        ],
        tech: ['Vite + React + TypeScript', 'Tailwind CSS', 'React Router（含子路径部署适配）', 'GitHub Actions + GitHub Pages'],
        outcomes: ['站点已上线，纯静态、零服务器成本，手机端可正常阅读。'],
      },
    },
  ] as Project[],
  footerNote: '本站所有内容均为个人作品展示，数据与凭据不上传公网。',
}

/** QQ 空间归档演示页的文案 */
export const archiveConfig = {
  title: 'QQ 空间归档',
  intro:
    '这些内容来自我自己账号的本地抓取导出，托管在本地、不随仓库上传。标着「已找回」的，是从互动记录里捞回来的、原本已被删除的说说。',
}

export function findProject(slug: string): Project | undefined {
  return profile.projects.find((project) => project.slug === slug)
}
