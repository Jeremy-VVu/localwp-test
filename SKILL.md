---
name: localwp-test
description: 在 LocalWP（Local by Flywheel）的 WordPress 開發站上測試外掛或佈景主題：WP-CLI、唯讀 SQL、PHP 多版本語法檢查、以管理員身分請求頁面、無頭瀏覽器（Edge／Chrome）冒煙測試與截圖、自訂瀏覽器腳本、WP_DEBUG_LOG 開關、對外 HTTP 請求紀錄、資料庫快照，以及在隔離的被入侵站台副本上做唯讀鑑識（檔案時間分布、uploads PHP、mu-plugins、後門寫法、不載入 WordPress 的資料庫檢查）。支援 Windows（Git Bash）、Linux、macOS。當使用者要在 LocalWP 站台上測試、驗證功能、檢查錯誤、跑 WP-CLI 或查資料庫時使用。站台通常是 *.local 網域，或位於 ~/Local Sites/<站台>、<任意目錄>/<站台>/app/public 這種 LocalWP 目錄結構。所有操作都透過單一入口 lwp，方便用一條權限規則免除確認提示。
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
| `find ... -newermt`、`find -name`、`ls -la` 找檔案 | `lwp <站台> files [路徑...] [--after=/--before=YYYY-MM-DD] [--name=GLOB,...] [--php] [--hidden] [--ww]` |
| `stat`、`md5sum`、`ls --time-style=full-iso` | `lwp <站台> stat <檔案...>` |
| `find ... -printf '%TY-%Tm-%Td' \| sort \| uniq -c` 統計修改時間 | `lwp <站台> forensic mtimes [路徑] [--by=day\|month\|hour] [--min=N]`（`--min` 只顯示檔案數 ≥ N 的時段，`--by=hour` 時建議加）；某天的檔案分布 `--on=YYYY-MM-DD` |
| 被入侵站台用 `sql`（會載入 WordPress） | `lwp <站台> forensic sql "<SELECT ...>"`（直接連資料庫，不執行站台程式碼） |
| `python -c` 解析站台裡的 JSON、換算時間戳記 | `lwp <站台> php -r '...'` |

`grep`、`cat`、`files`、`stat` 的相對路徑以站台的 `public` 為準（例如 `wp-content/plugins/xxx`），也可以用絕對路徑。

## 授權原則：除了刪除資料，其他都不用先問

使用者的授權範圍是：**測試與開發相關操作都可以直接做，只有「刪除資料」要先取得同意。**

可以直接做（不必詢問）：
- 所有唯讀操作：`info`、`sql`、`get`、`grep`、`cat`、`files`、`stat`、`forensic scan|mtimes|db|sql`、`lint`、`smoke`、`shot`、`run`、`debug status|log`、`httplog show`、`snapshot`（建立快照）、`tmp list`。
- 對外查詢公開資訊：用 WebSearch／WebFetch 查外掛的已知漏洞（Wordfence Intelligence、Patchstack、WPScan）、changelog、惡意程式特徵。**不要**連到 IOC 裡的控制端網域。
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

## 被入侵站台的鑑識（隔離副本）

使用者把被入侵的站台備份還原到 Local，目的是在離線環境裡**找出入侵管道**，不是在副本上清理。這種站台的程式碼要當成惡意程式看待，規則比一般測試嚴格：

**可以直接做（唯讀，不執行站台程式碼）：**
- `forensic scan`、`forensic mtimes`、`files`、`stat`、`grep`、`cat`、`forensic db`、`forensic sql`：只讀檔案或直接讀資料庫。
- 用 Read 讀取惡意檔案的原始碼來分析它的行為（控制端網址、植入方式、資料檔格式）。
- `wp core verify-checksums`、`wp plugin verify-checksums --all`：WP-CLI 這兩個指令不會跑到前台程式，但仍會載入 mu-plugins，見下一點。

**要先想過再做，並在回報中說明：**
- 任何會載入 WordPress 的操作（`wp ...`、`sql`、`info`、`get`、`smoke`、`cookie`）都會執行 mu-plugins、啟用中的外掛與佈景主題，也就包含惡意程式碼。WP-CLI 的 `--skip-plugins --skip-themes` **擋不到 mu-plugins**。查資料庫一律優先用 `forensic db`／`forensic sql`。
- 必須載入 WordPress 時（例如跑 checksums），先執行 `lwp <站台> httplog block <IOC 裡的控制端網域>`，再用 `httplog show` 確認有沒有對外連線。

**不要做：**
- 不要用 `get`、`smoke`、瀏覽器或 `php` 去請求或執行惡意檔案本身（例如 `uploads/xxx.php`），它可能會回報給控制端或改寫其他檔案。
- 不要刪除或修改惡意檔案：副本是證據。使用者要清理時，處理的是正式站，不是這份副本。
- 不要連到 IOC 裡的網域（WebFetch、curl 都不行）；查詢情資用搜尋引擎即可。

**建議流程：**
1. 先讀專案 `docs/` 裡的事件報告與 IOC，把控制端網域、檔名、特徵字串整理成 `--ioc` 正規式。
2. `forensic scan --ioc="<IOC 正規式>"`：uploads 內的 PHP、mu-plugins、wp-content 根目錄 PHP、auto_prepend／Handler、不認識的隱藏檔、後門寫法、超長行。
3. 讀惡意檔案的資料檔（例如連線設定、連結清單）找時間線索。檔案時間戳記常被搬站或還原改寫，**資料檔裡記錄的 Unix 時間**通常比較可信，用 `lwp <站台> php -r 'echo date("c", 1778279937);'` 換算。
4. `forensic mtimes`，再用 `forensic mtimes wp-content --on=<可疑日期>` 看那天有哪些檔案一起被改。整批外掛同一秒被改通常是搬站、還原或更新；只有零星幾個檔案時才值得細看。
5. `forensic db`：管理員帳號、cron、啟用中的外掛、最近停用的外掛、options／文章／postmeta 的可疑內容、可用的紀錄表。
6. 翻資安外掛留下的紀錄（`forensic sql`）：Wordfence 的 `wfstatus`（每次掃描「添加问题／Adding issue」的檔案與時間）、`wflogins`（登入，IP 欄位是二進位）、`wfhits`；Simple History；Limit Login Attempts／All In One Login 的登入紀錄；WP Statistics 的 `statistics_pages` 只記前台頁面瀏覽，看不到直接請求 PHP 的紀錄。
7. 比對外掛版本與已知漏洞：`wp plugin verify-checksums --all` 找被改過的檔案；付費外掛無法比對，就看有沒有破解版跡象；用 WebSearch 查各外掛在入侵時間點之前的漏洞，並確認漏洞的前提條件（例如需要特定表單欄位）在這個站台是否成立。
8. 記得標明限制：`.wpress` 等備份通常**不含 WordPress 核心與伺服器存取日誌**，核心比對與存取日誌追查要到原主機做；Windows 上沒有 Unix 權限，777 檢查也要到原主機做。

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
- 登入 cookie 除了到期會重新產生，伺服器端的工作階段失效時也會自動處理（外掛更新、改密碼、登出所有裝置都可能造成）：`get` 請求 `/wp-admin/...` 得到 302 時會驗證並重試一次；`smoke`／`shot`／`run` 開始前會先請求 `profile.php` 確認登入有效。看到「登入工作階段已失效」的訊息屬於正常。`lwp-browser` 每次 `open()` 都會重新設定 cookie，所以腳本裡清掉 cookie 不會影響之後的測試。
- puppeteer-core 裝在 skill 目錄內（有自己的 package.json）。**不要**在沒有 package.json 的目錄執行 `npm i`，否則會裝進使用者家目錄。
