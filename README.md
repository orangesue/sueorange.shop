# suorange.shop

个人主页 + QQ 空间说说归档。

站点是纯静态的（Vite + React + TypeScript）。真正的内容由 `tools/qzone/` 里的本地抓取工具
生成 —— 它在你自己的机器上运行，用你自己的登录凭据把自己的说说（包括**已经从空间里删掉、
但还留有互动痕迹的那部分**）导出成 JSON 和图片。

> **真实数据永远不进仓库。** `secrets/`、`public/data/shuoshuo.json`、`public/data/images/`
> 都在 `.gitignore` 里。仓库里只有代码和一份演示数据。

## 目录结构

```
src/                   站点源码（页面、组件、纯函数与单测）
public/data/demo.json  演示数据，线上展示用
public/data/           抓取结果落地处（不入库）
tools/qzone/           Python 抓取工具
secrets/cookie.txt     你的登录 Cookie（不入库）
```

## 站点：本地开发

```bash
npm install
npm run dev        # http://localhost:5173
npm run test       # Vitest
npm run build      # 类型检查 + 构建 + 生成 404.html
npm run preview    # 预览构建产物
```

## 抓取工具

### 它能做什么，不能做什么

先说边界，免得白折腾：

| 内容 | 能否找回 |
| --- | --- |
| 现存的说说、评论、配图 | ✅ 完整 |
| 已删除、但有人评论/点赞过的说说 | ✅ 从互动消息记录里找回 |
| 已删除、且从未有过任何互动痕迹的说说 | ❌ 腾讯服务器上已经没有入口 |
| 「仅自己可见」的说说 | ❌ 不在互动列表里 |
| 已被腾讯清理掉的照片 | ⚠️ 只能拿到失效链接 |

原理是两条通道互补：

1. **未删除说说接口**（`emotion_cgi_msglist_v6`）→ 拿到现存的全部说说、评论、配图。
2. **互动消息列表**（`feeds2_html_pav_all`）→ 沿着时间轴往前翻，拿到历史上产生过互动的
   说说。只在这里出现、却不在通道 1 里的，就是**已经被你删掉的那条**，脚本会给它打上
   `deleted: true`，站点上显示为「已找回」。

### 准备工作

```bash
cd tools/qzone
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

然后取 Cookie：**浏览器登录 QQ 空间** → `F12` → **Network** 面板 → 随便点开一个
`taotao.qq.com` 或 `ic2.qzone.qq.com` 的请求 → **Request Headers** → 复制整行 `Cookie`，
存到 `<仓库根目录>/secrets/cookie.txt`（参考 `tools/qzone/cookie.example.txt`）。

必须包含 `uin`（或 `p_uin`）、`skey`、`p_skey` 三个字段，缺一个都会直接报错提示你。

> Cookie 等同于账号权限。只放在本机，不要发给任何人，不要提交进仓库，用完可以退出登录让它失效。

### 运行

```bash
cd tools/qzone

# 先小步试跑，确认通道通
python fetch.py --max-pages 2 --max-feed-pages 2

# 正式抓取（默认会下载配图、写入 public/data/）
python fetch.py

# 只抓文字不下载图片
python fetch.py --no-images

# 顺手保存原始响应，排查问题时很有用
python fetch.py --dump-raw ../../public/data/raw
```

抓完回到仓库根目录跑 `npm run dev`，打开 `/archive` 就能看到自己的归档了。

### 离线模式

`--dump-raw` 保存下来的原始响应可以直接离线重放，不联网也不会消耗 Cookie：

```bash
python fetch.py \
  --offline-msglist ../../public/data/raw/msglist-001.txt \
  --offline-feeds   ../../public/data/raw/feeds-001.txt
```

接口字段一旦变化，改动集中在 `qz_archive/parse.py`（纯解析，带单测）和
`qz_archive/api.py`（网络与分页），其余部分不用动。

### 测试

```bash
cd tools/qzone
pytest
```

## 数据格式

`public/data/shuoshuo.json`：

```jsonc
{
  "generatedAt": "2026-09-10T12:00:00Z",
  "uin": "123456789",
  "posts": [
    {
      "id": "abc123",
      "tid": "abc123",
      "createdAt": "2020-02-14T07:45:00Z",  // UTC，页面按本地时区显示
      "text": "正文",
      "images": ["data/images/abc123/1.jpg"], // 没下载成功的会是原始 http 链接
      "comments": [{ "author": "小明", "text": "沙发", "createdAt": "" }],
      "likes": 3,
      "deleted": false,       // true = 从互动记录里找回的已删除说说
      "source": "msglist",    // msglist | feeds | both
      "repost": null
    }
  ]
}
```

## 部署

推送到 `main` 后，GitHub Actions 会自动构建并发布到 GitHub Pages
（`.github/workflows/deploy.yml`）。产物是纯静态文件，`scripts/make-404.mjs` 会额外
生成 `404.html`，让直接访问 `/archive` 这类深链接也能正常打开。

站点默认部署在子路径 `/sueorange.shop/`。绑定自定义域名 `sueorange.shop` 之后，
在 workflow 里把 `VITE_BASE` 改成 `/` 即可。

## 免责声明

这个工具只为你自己的账号、你自己的数据服务。它通过网页接口读取数据，不属于腾讯官方
支持的使用方式，请自行评估账号与合规风险；不要用它抓取他人的空间内容。

## 附：本机虚拟机没有外网时怎么办

这台开发用的 Ubuntu 虚拟机走 VMware NAT，但 NAT 没有转发外网（DNS 和默认路由都不通）。
所有需要联网的操作（`npm install`、`pip install`、`git push`）都靠一条 SSH 反向隧道 +
一个本地桥来完成：

```bash
# 在 Windows 宿主机上执行：把宿主机的 SOCKS5 代理接到虚拟机的 10810 端口
ssh -R 10810:127.0.0.1:10808 suorange@192.168.80.128

# 在虚拟机里执行：把 SOCKS 包装成本地 HTTP 代理（npm 只认 HTTP 代理）
BRIDGE_SOCKS_PORT=10810 python3 tools/setup/socks-bridge.py &

# 然后 npm / pip 都指定这个代理
npm install --proxy=http://127.0.0.1:8899 --https-proxy=http://127.0.0.1:8899
HTTPS_PROXY=http://127.0.0.1:8899 pip install -r requirements-dev.txt
```

桥只监听 `127.0.0.1`，用完直接结束进程即可。
