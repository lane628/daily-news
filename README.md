# 📰 每日早报 - 个人新闻聚合网站

每天自动更新的个人新闻聚合网站，每天早上 9:00 抓取前一天的重要新闻，分为互联网/商业、AI 前沿、金融市场三个板块呈现。

## 功能特性

- **三大板块**：互联网与商业、AI 前沿、金融市场
- **AI 摘要**：使用 DeepSeek API 自动生成中文摘要
- **全文搜索**：基于 MiniSearch 的纯前端全文检索
- **行情速览**：侧边栏实时显示主要股指涨跌
- **AI 助手**：浮动聊天窗口，可以对新闻进行追问
- **自动部署**：GitHub Actions 每日定时构建，GitHub Pages 托管

## 技术栈

| 组件 | 技术 |
|------|------|
| 静态生成器 | Hugo |
| 托管 | GitHub Pages |
| CI/CD | GitHub Actions |
| 内容采集 | Python + feedparser |
| AI 摘要 | DeepSeek API |
| 前端搜索 | MiniSearch |
| AI 助手代理 | Cloudflare Worker |

## 快速开始

### 1. 配置 Secrets

在 GitHub 仓库 Settings → Secrets 中添加：

- `DEEPSEEK_API_KEY`: DeepSeek API 密钥

### 2. 本地开发

```bash
# 安装 Python 依赖
pip install -r scripts/requirements.txt

# 手动抓取新闻（需设置环境变量）
export DEEPSEEK_API_KEY="your-key"
python scripts/fetch_news.py
python scripts/fetch_market.py
python scripts/build_index.py

# 启动 Hugo 开发服务器
hugo server -D
```

### 3. 部署 Cloudflare Worker

```bash
cd cloudflare-worker
# 使用 wrangler 部署
npx wrangler deploy worker.js
# 设置 API Key 环境变量
npx wrangler secret put DEEPSEEK_API_KEY
```

然后修改 `assets/js/chat.js` 中的 `WORKER_URL` 为你的 Worker 地址。

### 4. 自定义

- **修改信源**：编辑 `scripts/utils/rss_sources.py`
- **修改样式**：编辑 `assets/css/main.css`
- **修改布局**：编辑 `layouts/` 下的模板文件
- **调整构建时间**：编辑 `.github/workflows/daily-build.yml` 的 cron 表达式

## 成本

| 项目 | 费用 |
|------|------|
| GitHub Pages | 免费 |
| GitHub Actions | 免费（2000 分钟/月） |
| DeepSeek API | ≈ 3-5 分/天 |
| Cloudflare Worker | 免费（10 万请求/天） |
| **总计** | **约 1-3 元/月** |

## 目录结构

```
daily-news/
├── .github/workflows/     # CI/CD 配置
├── scripts/               # Python 采集脚本
├── content/daily/         # 每日新闻 Markdown
├── static/                # 静态资源（搜索索引、行情数据）
├── assets/                # Hugo 前端资源（CSS/JS）
├── layouts/               # Hugo 模板
├── cloudflare-worker/     # AI 助手 API 代理
└── config.toml            # Hugo 配置
```

## License

MIT
