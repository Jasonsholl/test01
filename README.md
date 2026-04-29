# SpecialHer 图片小程序（本地图片 → GitHub → 微信小程序）

你每天把图片手动下载到本地文件夹，然后跑一次导入脚本。脚本会把图片复制到 `site/images/YYYY-MM-DD/`，生成 `site/manifest.json`，再 `git push` 到 GitHub Public 仓库。微信小程序只需要拉取 `manifest.json` 并预览图片即可。

## 1) 准备（一次性）

### A. 建 GitHub Public 仓库

把本目录内容放进一个 Public repo（例如 `specialher-miniapp`）。之后小程序会从 GitHub 的 raw 链接读取：

- `manifest.json`: `https://raw.githubusercontent.com/<USER>/<REPO>/<BRANCH>/site/manifest.json`
- 图片：同域名下的 `site/images/...`

### B. Python 环境

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

本地图片导入脚本不需要 Telegram 登录。`requirements.txt` 里仍保留 Telethon，是给旧的 TG 抓取脚本备用。

## 2) 每天执行（导入本地图片 + 更新 manifest）

在仓库根目录：

```bash
backend/.venv/bin/python backend/import_local.py "/你的/图片文件夹"
```

脚本逻辑：
- 默认按“今天（Asia/Shanghai，UTC+8）”归档
- 默认最多导入 10 张
- 按图片内容 SHA-256 去重，重复图片不会再次导入
- 更新 `site/index.json`（历史索引）和 `site/manifest.json`（给小程序读的最近 10 张列表）

指定日期示例：

```bash
backend/.venv/bin/python backend/import_local.py "/你的/图片文件夹" --date 2026-04-29
```

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
5 8 * * * cd /ABS/PATH/specialher-miniapp && /ABS/PATH/specialher-miniapp/backend/run_and_publish_local.sh "/ABS/PATH/downloaded-images" >> /ABS/PATH/specialher-miniapp/backend/cron.log 2>&1
```
