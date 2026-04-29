# SpecialHer 图片小程序（最省钱：TG → GitHub → 微信小程序）

你每天跑一次 Python 脚本，从 Telegram 频道 `@SpecialHer` 抓取“当天”的新图片（最多 10 张），落到本地 `site/images/YYYY-MM-DD/`，生成 `site/manifest.json`，然后 `git push` 到 GitHub Public 仓库。微信小程序只需要拉取 `manifest.json` 并预览图片即可。

## 1) 准备（一次性）

### A. 建 GitHub Public 仓库

把本目录内容放进一个 Public repo（例如 `specialher-miniapp`）。之后小程序会从 GitHub 的 raw 链接读取：

- `manifest.json`: `https://raw.githubusercontent.com/<USER>/<REPO>/<BRANCH>/site/manifest.json`
- 图片：同域名下的 `site/images/...`

### B. Telegram API（一次性）

Telethon 需要你的 Telegram API：

- `TG_API_ID`
- `TG_API_HASH`

获取方式：Telegram 官方 `my.telegram.org`（用你的账号登录后创建应用拿到）。

### C. Python 环境

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

首次运行会让你在终端里用手机号登录 Telegram（会生成 `backend/.tg.session` 文件，已在 `.gitignore` 里忽略）。

## 2) 每天执行（自动抓取 + 更新 manifest）

在仓库根目录：

```bash
export TG_API_ID="xxx"
export TG_API_HASH="xxx"
export TG_CHANNEL="SpecialHer"
python3 backend/run_daily.py
```

脚本逻辑：
- 只抓“今天（Asia/Shanghai，UTC+8）”发布的图片消息
- 只下载没抓过的（按 `message.id` 去重）
- 更新 `site/index.json`（历史索引）和 `site/manifest.json`（给小程序读的最近 10 张列表）

## 3) 发布到 GitHub（手动）

```bash
git add site
git commit -m "Update images"
git push
```

或者用脚本（会自动 commit/push）：

```bash
./backend/publish_site.sh
```

后续你也可以把这一步放进 cron（见下方）。

## 4) 微信小程序

小程序代码在 `miniapp/`。

你需要把 `miniapp/utils/config.js` 里的 `MANIFEST_URL` 改成你 GitHub raw 的实际地址，然后在微信开发者工具里导入 `miniapp/` 目录即可。

注意：小程序需要把 `raw.githubusercontent.com` 加到“request 合法域名”和“downloadFile 合法域名”（微信公众平台后台配置）。

## 5) cron（可选，macOS）

示例（每天 08:05 执行；你按需改时间）：

```bash
crontab -e
```

加入（把路径改成你本机实际路径）：

```cron
5 8 * * * cd /ABS/PATH/specialher-miniapp && /usr/bin/env TG_API_ID=xxx TG_API_HASH=xxx TG_CHANNEL=SpecialHer /ABS/PATH/specialher-miniapp/backend/.venv/bin/python /ABS/PATH/specialher-miniapp/backend/run_daily.py >> /ABS/PATH/specialher-miniapp/backend/cron.log 2>&1
```
