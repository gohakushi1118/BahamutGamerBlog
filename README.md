# baha-home-sync

把巴哈姆特「創作大廳（小屋）」某位創作者的**公開**創作，自動抓取、轉成 Markdown，
並（選用）由 Jenkins 定時同步到 GitHub。

A tool to scrape a Bahamut creator's **public** 小屋 creations, convert them to
Markdown, and optionally sync them to a GitHub repo on a schedule via Jenkins.

---

## 功能

- 透過官方 JSON API 逐頁抓取某 `owner` 的全部創作清單
- 逐篇取出標題 / 發表時間 / 內文，轉成帶 YAML frontmatter 的 Markdown
- 圖片保留巴哈 CDN 連結；含圖的標題會自動解包避免漏圖
- 自動產生 `README.md` 文章索引與 `scrape_state.json` 抓取摘要
- 只抓**公開**文章，鎖文 / 需登入 / 已刪除者自動略過並記錄

## 安裝

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## 使用

```bash
python scraper.py --owner <小屋帳號ID> --out <輸出目錄>
```

| 參數 | 說明 | 預設 |
| --- | --- | --- |
| `--owner` | 小屋帳號 ID（網址 `?owner=` 的值，必填） | — |
| `--out` | 輸出目錄 | `.` |
| `--delay` | 每篇之間延遲秒數（禮貌爬蟲） | `1.0` |

輸出：`<out>/posts/<csn>-<slug>.md`、`<out>/README.md`、`<out>/scrape_state.json`。

## Jenkins 自動排程（選用）

`Jenkinsfile` + `sync.sh` 提供一條 Docker pipeline：在 `python:3.12-slim` 容器內
clone 目標 repo → 抓取 → commit → push，主機免裝 Python。

1. Jenkins 安裝 **Pipeline**、**Git** 外掛，主機需有 Docker。
2. **Credentials → Username with password**：ID `github-pat`、填你的 GitHub 帳號與
   [Personal Access Token](https://github.com/settings/tokens)（勾 `repo`）。
3. **New Item → Pipeline → Pipeline script from SCM**，指向你的 fork，Script Path `Jenkinsfile`。
4. **Build with Parameters** 填 `OWNER`。排程在 `triggers { cron('H 4 * * *') }`。

> 此 `Jenkinsfile` 針對 **Windows Jenkins 主機 + Docker Desktop** 設計（用 `bat` 並把
> workspace 唯讀掛載，所有寫入都在容器內完成）。若你的 Jenkins 跑在 **Linux** 主機，
> 可直接改用宣告式 `agent { docker { image 'python:3.12-slim' } }` + `sh`，更簡單。

## 免責聲明 / Disclaimer

- 本工具僅用於**個人備份自己或公開可見的創作內容**，請尊重原作者著作權。
- 抓取的內容著作權屬原作者所有；散布前請自行確認是否取得授權。
- 使用前請遵守巴哈姆特網站服務條款，並控制抓取頻率以免造成站方負擔。
- 本工具按「現狀」提供，作者不對任何使用後果負責（見 [LICENSE](LICENSE)）。

## 授權

[MIT](LICENSE)
