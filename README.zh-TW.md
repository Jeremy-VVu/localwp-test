# localwp-test

[English](README.md) | 繁體中文

給 [Claude Code](https://claude.com/claude-code) 用的 skill：在 [LocalWP](https://localwp.com/)（Local by Flywheel）的 WordPress 開發站上測試外掛或佈景主題。

所有操作都透過單一入口 `bin/lwp`，只要在 Claude Code 加一條權限規則，就能免除每次的確認提示。

## 功能

- **WP-CLI**：使用 LocalWP 內建的 PHP、php.ini 與 WP-CLI，會刪除資料的操作會被擋下，需明確加上 `--lwp-yes`
- **唯讀 SQL**：只允許 SELECT／SHOW／DESCRIBE／EXPLAIN
- **PHP 多版本語法檢查**：同時用站台版本與指定版本（例如 7.4、8.4）檢查
- **以管理員身分請求頁面**：自動產生登入 cookie，回報 HTTP 狀態與頁面上的 PHP 錯誤
- **無頭瀏覽器冒煙測試**：可自動爬遍後台左側選單所有頁面，抓 console 錯誤、未捕捉例外、4xx/5xx；重複訊息會合併，已知的環境雜訊會被過濾
- **自訂瀏覽器腳本**：`require('lwp-browser')`，底層是 puppeteer
- **WP_DEBUG_LOG 開關與分組統計**：關閉時會放回位元組完全一致的原檔
- **對外 HTTP 請求紀錄與封鎖**、**資料庫快照與還原**、**測試用暫存檔管理**
- **被入侵站台的唯讀鑑識**：`files`、`stat`、`forensic scan|mtimes` 檢查 uploads 內的 PHP、mu-plugins、auto_prepend、隱藏檔、後門寫法與檔案時間分布；`forensic db|sql` 不載入 WordPress，直接讀資料庫，避免執行站台裡的惡意程式碼

## 支援平台

| | Windows（Git Bash） | Linux | macOS |
|---|---|---|---|
| Local 資料目錄 | `%APPDATA%\Local` | `~/.config/Local` | `~/Library/Application Support/Local` |
| 瀏覽器 | Edge → Chrome | Edge → Chrome → Chromium | Edge → Chrome → Chromium |

需要：bash、python3（Windows 為 python）、node、curl，以及 Edge／Chrome／Chromium 其中一個。

## 安裝

```bash
git clone https://github.com/Jeremy-VVu/localwp-test.git ~/.claude/skills/localwp-test
cd ~/.claude/skills/localwp-test
npm ci            # 安裝 puppeteer-core（只裝在 skill 目錄內）
chmod +x bin/lwp
```

在 `~/.claude/settings.json` 加入權限規則，讓 Claude Code 呼叫 lwp 時不必每次確認：

```json
{
  "permissions": {
    "allow": [
      "Bash(~/.claude/skills/localwp-test/bin/lwp)",
      "Bash(~/.claude/skills/localwp-test/bin/lwp *)"
    ]
  }
}
```

## 使用

```bash
lwp list                                   # 列出所有 Local 站台
lwp <站台> info                            # PHP、資料庫、外掛狀態
lwp <站台> debug on                        # 開啟除錯紀錄
lwp <站台> smoke --all-admin --no-shots /  # 爬前台首頁與整個後台選單
lwp <站台> debug summary                   # 依類型＋檔案分組統計 debug.log
lwp <站台> cleanup                         # 還原 wp-config.php、關閉瀏覽器等
```

完整用法執行 `lwp help`；給 Claude 看的操作規則、安全規則與已知雜訊清單在 [`SKILL.md`](SKILL.md)。

## 注意

- 只會操作 LocalWP `sites.json` 裡登記的本機站台，不會、也不應該拿來碰正式站。
- 輸出（cookie、截圖、快照）放在 `<站台>/app/.lwp-test/`，不在網站 public 目錄底下。
- 瀏覽器設定檔放在使用者快取目錄（例如 `~/.cache/localwp-test/`），可隨時刪除。

## 授權

[MIT](LICENSE)
