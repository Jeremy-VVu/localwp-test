---
name: localwp-test
description: 在 LocalWP（Local by Flywheel）的 WordPress 開發站上測試外掛或佈景主題：WP-CLI、唯讀 SQL、PHP 多版本語法檢查、以管理員身分請求頁面、無頭瀏覽器（Edge／Chrome）冒煙測試與截圖、自訂瀏覽器腳本、WP_DEBUG_LOG 開關、對外 HTTP 請求紀錄、資料庫快照。支援 Windows（Git Bash）、Linux、macOS。當使用者要在 LocalWP 站台上測試、驗證功能、檢查錯誤、跑 WP-CLI 或查資料庫時使用。站台通常是 *.local 網域，或位於 ~/Local Sites/<站台>、<任意目錄>/<站台>/app/public 這種 LocalWP 目錄結構。所有操作都透過單一入口 lwp，方便用一條權限規則免除確認提示。
---

# LocalWP 測試（lwp）

所有操作都透過單一指令：

```
~/.claude/skills/localwp-test/bin/lwp <站台> <子指令> [參數...]
```

`<站台>` 可以用 Local 的站台名稱、網域（amce.local）、資料夾名稱或 id。`lwp list` 列出所有站台，`lwp help` 顯示完整用法。

## 免確認的關鍵：每次只單獨呼叫 lwp

使用者在 `~/.claude/settings.json` 允許了 `Bash(~/.claude/skills/localwp-test/bin/lwp)` 和 `Bash(~/.claude/skills/localwp-test/bin/lwp *)`，所以只有「單獨一條、以 `~/.claude/skills/localwp-test/bin/lwp` 開頭的指令」才不會跳出確認提示。路徑要照這個寫法，不要改成 `/c/Users/...`、`C:/Users/...` 或 `/home/<使用者>/...`。

- **要做：** 一個 Bash 呼叫只放一條 `~/.claude/skills/localwp-test/bin/lwp ...`。多個步驟就用多個 Bash 呼叫，彼此獨立的步驟可以並行送出。
- **不要做：** 用 `&&`、`;`、`|`、`cd ... &&`、`$(...)` 串接，也不要加環境變數前綴（`FOO=1 lwp ...`）。這些組合都不會符合規則，會跳出確認提示。
- 需要過濾輸出時，`sql` 寫精確的 WHERE 條件，`wp` 用 `--fields=`、`--format=`，不要接 `| grep`。

### 這些事也改用 lwp，才不會跳出確認

| 原本的寫法（會跳確認） | 改用 |
|---|---|
| `grep -rn ... D:/.../public/...`、搜尋原版外掛等工作目錄外的檔案 | `lwp <站台> grep <正規式> [路徑...] [--include=*.php -i ...]` |
| `cat`／`sed -n`／Read 工具讀工作目錄外的檔案 | `lwp <站台> cat <檔案> [起-迄]` |
| `cd 某目錄 && node 腳本.js` | `lwp <站台> node <腳本絕對路徑> [參數...]` |
| `node <輸出目錄>/xxx.js`、`lwp run <完整路徑>` | `lwp <站台> run xxx.js`、`lwp <站台> node xxx.js`（找不到時自動找 `.lwp-test/`） |
| `cp` 測試檔（譯檔、mu-plugin 等）到站台，測完再 `rm` | `lwp <站台> tmp put <檔案...> --to=<wp-content 下的目錄>`，測完 `lwp <站台> tmp clear` |

`grep`、`cat` 的相對路徑以站台的 `public` 為準（例如 `wp-content/plugins/xxx`），也可以用絕對路徑。

## 授權原則：除了刪除資料，其他都不用先問

使用者的授權範圍是：**測試與開發相關操作都可以直接做，只有「刪除資料」要先取得同意。**

可以直接做（不必詢問）：
- 所有唯讀操作：`info`、`sql`、`get`、`grep`、`cat`、`lint`、`smoke`、`shot`、`run`、`debug status|log`、`httplog show`、`snapshot`（建立快照）、`tmp list`。
- 測試用的暫時狀態，以及還原這些狀態：`debug on|off|clear`、`httplog on|off|block|unblock|clear`、`browser start|stop`、`cleanup`。
- 用 `tmp put` 放入測試檔、用 `tmp clear` 清除。`tmp clear` 只刪除 lwp 自己放入、而且內容沒被改過的檔案，因此**不算刪除使用者資料**。
- 透過瀏覽器腳本或 WP-CLI 修改設定做測試（例如改選單標題後儲存）。**先 `snapshot` 並告訴使用者快照名稱。**
- 測完把資料庫還原成「同一段工作中、測試前自己建立的快照」，以撤銷自己的測試改動。這時仍需加 `--lwp-yes`，但不必再問；回報時要說明還原了哪個快照。

必須先取得使用者明確同意（同意後才加 `--lwp-yes`）：
- 刪除任何不是 lwp 自己建立的東西：外掛、佈景主題、使用者、文章、選項、meta、資料表、檔案。
- 還原「不是這段工作中自己建立的」快照，或任何會覆蓋使用者資料的匯入。
- `tmp clear` 回報「保留（內容被修改）」的檔案：不要自行刪除，交給使用者決定。

lwp 會擋下以下操作，必須加 `--lwp-yes` 才會執行：
- `db reset|drop|clean|import`、`site empty|delete`、`plugin delete|uninstall`、`theme delete`、`user delete`、`core update|download`、沒加 `--dry-run` 的 `search-replace`。
- `option|post|term|comment|menu|widget|transient|site option|user meta|post meta|term meta|comment meta|network meta|role|cap|cron event` 的 `delete|remove|empty`。
- `post generate|update`、`media regenerate`、`rewrite flush --hard`、`cache flush`。
- 含 DELETE／DROP／TRUNCATE／UPDATE／ALTER／REPLACE／INSERT／RENAME／CREATE 的 `wp db query`。唯讀查詢請用 `sql`。
- `restore`。

## 常用流程

1. `lwp <站台> info`：確認站台已啟動（資料庫「運作中」）、PHP 版本、外掛狀態。資料庫沒回應時，請使用者在 LocalWP 啟動站台。
2. 開始測試前執行 `lwp <站台> debug on`。測完執行 `lwp <站台> debug summary` 看依「類型＋訊息＋檔案」分組的統計（預設只看今天，`--all` 看全部、`--date=YYYY-MM-DD` 指定日期、最後可加組數），需要原始內容再用 `debug log [行數]`。
3. 需要確認外掛有沒有對外連線時：`httplog on` → 操作 → `httplog show`。測試可疑或已知遭入侵的外掛（例如會向原廠伺服器檢查更新）時，先執行 `httplog block <網域>` 擋下連線，請求仍會記錄並標為 BLOCKED。
4. PHP 語法：`lwp <站台> lint <外掛目錄> --php=7.4`，會同時用站台的 PHP 版本和指定版本檢查，並行處理。
5. 頁面檢查：
   - `lwp <站台> get <路徑>`：curl，速度快，看 HTTP 狀態與頁面上的 PHP 錯誤字樣，不會執行 JS。
   - `lwp <站台> smoke <路徑...>`：真實瀏覽器，抓 console.error、未捕捉例外、站台 4xx/5xx。
   - `lwp <站台> smoke --all-admin --no-shots`：自動爬遍後台左側選單的所有頁面。
   - smoke 的輸出：同一頁重複的訊息合併成「×N」，終端只列有問題的頁面，完整結果（含 OK 頁面與被忽略的雜訊）寫在 `.lwp-test/smoke-report.txt`。下方「判讀結果」列的已知雜訊預設會被過濾，只在最後一行統計筆數；要全部顯示時加 `--raw`。
   - 路徑含 `&` 時要加單引號（`'/wp-admin/edit.php?post_type=x&page=y'`），否則會被 shell 當成背景執行、看不到輸出。
6. 功能流程（填表、按儲存、驗證結果）：在輸出目錄寫一個腳本，再用 `lwp <站台> run <腳本.js>` 執行（API 見下方）。
7. 需要在站台放測試檔（例如測試用譯檔 .mo／.json、追蹤用 mu-plugin）時，用 `lwp <站台> tmp put <檔案...> --to=<wp-content 下的目錄>`。原本就存在的檔案不會被覆蓋。
8. 結束時執行 `lwp <站台> cleanup`：還原 wp-config.php、移除 HTTP 紀錄器、清除 tmp 暫存檔、關閉瀏覽器。

輸出（cookie、截圖 `shots/`、`last-get.html`、資料庫快照、自訂腳本）都放在 `<站台>/app/.lwp-test/`。這個目錄不在 public 底下，網站無法存取。截圖可以用 Read 工具查看；如果被「只能讀工作目錄」擋住，就請使用者在 `<站台>/app` 開啟 Claude Code，或執行 `/add-dir`。

## 安全規則（必須遵守）

- **會刪除資料的操作會被 lwp 擋下**（清單見上方「授權原則」）。除了「還原自己剛建立的測試前快照」之外，只有在使用者**於本次對話中明確同意這個具體操作**之後，才能加上 `--lwp-yes`。不可以自行判斷加上。
- 做會大量改動資料的測試之前，先執行 `lwp <站台> snapshot <名稱>`，並告訴使用者快照名稱。
- `sql` 只允許單一的 SELECT／SHOW／DESCRIBE／EXPLAIN。要改資料請用 `wp option update`、`wp post meta` 等明確的 WP-CLI 指令，並在回報裡說明改了什麼。
- `wp eval`／`wp eval-file`、`lwp node`、`lwp run` 都能執行任意程式，只用來讀取、測試或觸發外掛自己的程式。不要用它們刪除資料，也不要用來繞過上面的限制。
- lwp 只會操作 LocalWP 的 sites.json 裡登記的本機站台，不能、也不要拿它去碰正式站。

## 自訂瀏覽器腳本（lwp run）

腳本放在 `<站台>/app/.lwp-test/`，用 `require('lwp-browser')`：

```js
const lwp = require('lwp-browser');
(async () => {
	const { page, problems, status, close } = await lwp.open('/wp-admin/options-general.php?page=xxx');
	await page.click('#some-checkbox');
	await lwp.clickAndWait(page, '#submit');            // 送出表單並等待頁面跳轉
	console.log(await lwp.notices(page));               // WordPress 通知文字
	await lwp.goto(page, '/wp-admin/');                 // 換頁（不需重新 open）
	await lwp.shot(page, 'after-save');                 // 截圖到 shots/after-save.png
	console.log(problems.length ? problems : 'no problems');
	await close();
})();
```

API：`open(url)`、`goto(page, url)`、`clickAndWait(page, selector|handle)`、`notices(page)`、`phpErrors(page)`、`shot(page, name)`、`sleep(ms)`、`BASE`、`OUT`。`page` 是 puppeteer 的 Page，可以直接用 `page.evaluate`、`page.$eval`、`page.keyboard` 等。驗證資料時，腳本跑完後另外用 `lwp <站台> sql` 或 `lwp <站台> wp option get ... --format=json` 查。

## 判讀結果：已知的非外掛問題

以下是 WordPress 核心或環境本身的現象，不要誤判成受測外掛的問題。標 🔇 的會被 `smoke` 自動過濾（規則在 `lib/browser.js` 的 `NOISE`，新增已知雜訊時兩邊一起更新）：

- 使用區塊佈景主題（例如 Twenty Twenty-Five）時，`nav-menus.php` 回傳 500，訊息是「目前使用的佈景主題不支援導覽選單或小工具」。
- 🔇 WP 7.x 的 `options-connectors.php` 會對沒安裝的 AI 外掛發出 `/wp-json/wp/v2/plugins/ai...` 請求並得到 404。
- 🔇 Chrome 的 `Permissions policy violation: unload is not allowed`：瀏覽器停用 unload 事件的警告，WordPress 編輯器頁面都會出現。
- 🔇 `Google Maps JavaScript API error: RefererNotAllowedMapError`：Maps 金鑰沒有授權 localhost。
- 🔇 Elementor 後台查詢 `https://ipapi.co/json/` 被 CORS 擋，以及 reCAPTCHA 的 report-only CSP 紀錄。
- 🔇 頁面跳轉時偶發 `ERR_HTTP2_PROTOCOL_ERROR`：失敗的請求是 `*.kaspersky-labs.com`，也就是本機 Kaspersky 防毒注入的 script，不是站台的問題。
- 偶發 502 Bad Gateway（大量並行請求時），單獨重試會是 200。
- 頁面上找不到某段 JS 產生的文字時，可能是元件尚未展開（例如選單編輯面板要點開才會建立欄位），不一定是錯誤。
- `httplog` 裡的 api.wordpress.org、s.w.org，以及站台自己的網域（wp-cron、loopback），屬於核心行為。判斷外掛有沒有對外連線，要看「由外掛／佈景主題發出的請求」那一段。
- 判斷某個錯誤是不是受測外掛造成的：停用該外掛後再跑一次同樣的 `smoke`／`get` 比對。

## 環境細節與已處理的坑

- 平台會自動偵測（`lwp <站台> info` 看得到實際使用的 PHP 路徑）：

  | | Windows（Git Bash） | Linux | macOS |
  |---|---|---|---|
  | Local 資料目錄 | `%APPDATA%\Local` | `~/.config/Local` | `~/Library/Application Support/Local` |
  | PHP | `lightning-services/php-<版本>/bin/win64/php.exe` | `.../bin/linux/bin/php` | `.../bin/darwin(-arm64)/bin/php` |
  | WP-CLI | `C:\Program Files (x86)\Local\...\wp-cli` | `/opt/Local/resources/extraResources/bin/wp-cli` | `/Applications/Local.app/.../wp-cli` |
  | 瀏覽器 | Edge → Chrome | Edge → Chrome → Chromium（PATH 中找） | Edge → Chrome → Chromium |
- 站台資訊來自 Local 資料目錄的 `sites.json`（只讀取指定的那一個站台）。PHP、MySQL 用的是 Local 的 lightning-services，php.ini 用的是 `<Local 資料目錄>/run/<id>/conf/php/php.ini`。
- Linux／macOS 版的 PHP 依賴同目錄的 `shared-libs`（例如 libtidy），直接執行會出現 `error while loading shared libraries`。lwp 只對 PHP 程序設定 `LD_LIBRARY_PATH`／`DYLD_LIBRARY_PATH`，不影響其他指令。
- 可以用環境變數 `LWP_BROWSER` 指定瀏覽器執行檔。
- `wp db *` 需要 `MYSQL_TCP_PORT` 才會連到站台的資料庫埠（lwp 已處理）。
- Windows 上 Chrome 用 puppeteer 直接 launch 時會立即結束（exit code 21），所以 lwp 改成在背景啟動瀏覽器（`--remote-debugging-port`，預設 9333），再用 `puppeteer.connect` 連線。設定檔放在使用者快取目錄（Linux：`~/.cache/localwp-test/`；macOS：`~/Library/Caches/localwp-test/`；Windows：`%LOCALAPPDATA%\localwp-test\`），不放進 skill 目錄；`browser stop` 只會關掉這個實例。
- （Windows）呼叫 node 時已關閉 Git Bash 的路徑轉換，避免 `/wp-admin/...` 被改成 `C:/Program Files/Git/...`。
- Windows 的 Python 輸出是 CRLF，lwp 讀取時已去除 `\r`。Windows 用 `python`，Linux／macOS 用 `python3`（自動選擇）。
- `debug off`：如果開啟後 wp-config.php 沒被別人改過，就放回位元組完全一致的原檔；否則逐一還原常數。
- puppeteer-core 裝在 skill 目錄內（有自己的 package.json）。**不要**在沒有 package.json 的目錄執行 `npm i`，否則會裝進使用者家目錄。
