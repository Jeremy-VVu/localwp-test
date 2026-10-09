<?php
/**
 * 唯讀的資料庫鑑識（lwp forensic db／forensic sql 的實作）。
 *
 * 不載入 WordPress：被入侵的站台一跑 WP-CLI 就會執行 mu-plugins／外掛裡的惡意程式碼
 * （--skip-plugins 也擋不住 mu-plugins），所以這裡直接用 mysqli 連線，
 * wp-config.php 也只用正規式讀出 DB_NAME 等常數與 $table_prefix，不 include。
 *
 * 用法：php forensic-db.php <public> <port> db [--keywords=正規式]
 *       php forensic-db.php <public> <port> sql "<SELECT ...>"
 */
mysqli_report(MYSQLI_REPORT_OFF);
[$self, $public, $port, $cmd] = array_pad($argv, 4, null);
$cfg = @file_get_contents("$public/wp-config.php");
if ($cfg === false) {
	fwrite(STDERR, "讀不到 $public/wp-config.php\n");
	exit(2);
}
function cfg_const($cfg, $name, $default = '') {
	return preg_match('/define\s*\(\s*[\'"]' . $name . '[\'"]\s*,\s*[\'"]([^\'"]*)[\'"]/', $cfg, $m) ? $m[1] : $default;
}
$prefix = preg_match('/\$table_prefix\s*=\s*[\'"]([^\'"]+)[\'"]/', $cfg, $m) ? $m[1] : 'wp_';
$db = @new mysqli('127.0.0.1', cfg_const($cfg, 'DB_USER', 'root'), cfg_const($cfg, 'DB_PASSWORD', 'root'), cfg_const($cfg, 'DB_NAME', 'local'), (int) $port);
if ($db->connect_errno) {
	fwrite(STDERR, "資料庫連線失敗：{$db->connect_error}\n");
	exit(3);
}
$db->set_charset('utf8mb4');

function q($sql) {
	global $db, $prefix;
	$res = $db->query(str_replace('{prefix}', $prefix, $sql));
	if ($res === false) {
		return "SQL 錯誤：{$db->error}";
	}
	return $res === true ? [] : $res->fetch_all(MYSQLI_ASSOC);
}
function show($title, $rows, $empty = '（無）') {
	echo "\n== $title\n";
	if (is_string($rows)) {
		echo "  $rows\n";
		return;
	}
	if (!$rows) {
		echo "  $empty\n";
		return;
	}
	$cols = array_keys($rows[0]);
	echo '  ' . implode("\t", $cols) . "\n";
	foreach ($rows as $r) {
		echo '  ' . implode("\t", array_map(fn($v) => str_replace(["\r", "\n", "\t"], ' ', mb_substr((string) $v, 0, 160)), $r)) . "\n";
	}
}

if ($cmd === 'sql') {
	$sql = $argv[4] ?? '';
	if (!preg_match('/^\s*(SELECT|SHOW|DESCRIBE|DESC|EXPLAIN)\b/i', $sql) || preg_match('/;\s*\S/', $sql)) {
		fwrite(STDERR, "forensic sql 只允許單一的 SELECT／SHOW／DESCRIBE／EXPLAIN 查詢\n");
		exit(1);
	}
	show('查詢結果（未載入 WordPress）', q($sql), '(0 rows)');
	exit(0);
}

$opts = [];
foreach (array_slice($argv, 4) as $a) {
	if (preg_match('/^--([^=]+)=(.*)$/', $a, $m)) {
		$opts[$m[1]] = $m[2];
	}
}
// 垃圾連結常見關鍵字（博弈、色情、藥品），可用 --keywords 換成自己的
$kw = $opts['keywords'] ?? 'casino|bahis|betting|giris|slot gacor|togel|judi|viagra|cialis|porn|escort|replica|payday';
$kw_sql = $db->real_escape_string($kw);
$sus = "(%s LIKE '%%<script%%' OR %s LIKE '%%<iframe%%' OR %s LIKE '%%eval(%%' OR %s LIKE '%%base64_decode%%' OR %s LIKE '%%gzinflate%%'"
	. " OR %s LIKE '%%-9999px%%' OR %s LIKE '%%display:none%%<a %%' OR %s REGEXP '$kw_sql')";
$sus_of = fn($col) => sprintf($sus, ...array_fill(0, 8, $col));

echo "資料表前綴 {$prefix}（未載入 WordPress，直接讀資料庫）\n";

show('網址', q("SELECT option_name, option_value FROM {prefix}options WHERE option_name IN ('siteurl','home','template','stylesheet','admin_email','users_can_register','default_role')"));

show('管理員帳號（確認每一個都認識）', q("SELECT u.ID, u.user_login, u.user_email, u.user_registered, u.display_name
	FROM {prefix}users u JOIN {prefix}usermeta m ON m.user_id=u.ID AND m.meta_key='{$prefix}capabilities'
	WHERE m.meta_value LIKE '%administrator%' ORDER BY u.user_registered"));

show('各角色人數', q("SELECT m.meta_value AS caps, COUNT(*) n FROM {prefix}usermeta m WHERE m.meta_key='{$prefix}capabilities' GROUP BY m.meta_value ORDER BY n DESC LIMIT 15"));

show('最近註冊的 10 個帳號', q("SELECT ID, user_login, user_email, user_registered FROM {prefix}users ORDER BY user_registered DESC LIMIT 10"));

// cron 與外掛啟用清單：unserialize 時不建立任何物件，避免觸發惡意序列化資料
$raw = q("SELECT option_name, option_value FROM {prefix}options WHERE option_name IN ('cron','active_plugins','recently_activated')");
$opt = is_array($raw) ? array_column($raw, 'option_value', 'option_name') : [];
$cron = @unserialize($opt['cron'] ?? '', ['allowed_classes' => false]);
$hooks = [];
if (is_array($cron)) {
	foreach ($cron as $t => $events) {
		if (is_array($events)) {
			foreach ($events as $hook => $ev) {
				$hooks[$hook] = ($hooks[$hook] ?? 0) + 1;
			}
		}
	}
}
ksort($hooks);
echo "\n== cron 排程（共 " . count($hooks) . " 個 hook；不認得前綴的要查是哪個外掛註冊的）\n";
echo '  ' . implode('  ', array_keys($hooks)) . "\n";

$active = @unserialize($opt['active_plugins'] ?? '', ['allowed_classes' => false]);
echo "\n== 啟用中的外掛（active_plugins）\n  " . (is_array($active) ? implode("\n  ", $active) : '（讀不到）') . "\n";
$recent = @unserialize($opt['recently_activated'] ?? '', ['allowed_classes' => false]);
if (is_array($recent) && $recent) {
	echo "\n== 最近停用的外掛（recently_activated，可對照入侵時間）\n";
	foreach ($recent as $p => $t) {
		echo '  ' . date('Y-m-d H:i', (int) $t) . "  $p\n";
	}
}

// options 的值可能很大，MySQL 的 REGEXP 會逾時，改在 PHP 端比對
$sus_rx = '/<script|<iframe|eval\s*\(|base64_decode|gzinflate|-9999px|display:\s*none[^>]*>\s*<a\s|' . str_replace('/', '\/', $kw) . '/i';
$found = [];
$all = q("SELECT option_name, autoload, option_value FROM {prefix}options WHERE option_name NOT LIKE '\\_transient%' AND option_name NOT LIKE '\\_site\\_transient%'");
foreach (is_array($all) ? $all : [] as $r) {
	if (preg_match($sus_rx, $r['option_value'], $m, PREG_OFFSET_CAPTURE)) {
		$at = max(0, $m[0][1] - 40);
		$found[] = ['option_name' => $r['option_name'], 'autoload' => $r['autoload'], 'len' => strlen($r['option_value']),
			'match' => substr($r['option_value'], $at, 120)];
	}
}
show('options 中的可疑內容（指令碼、iframe、eval、隱藏連結、垃圾關鍵字；外掛設定裡的 <script 常是正常的）', is_array($all) ? $found : $all);

show('文章內容的可疑內容（不含修訂版本）', q("SELECT ID, post_type, post_status, post_modified, post_title FROM {prefix}posts
	WHERE post_type NOT IN ('revision') AND " . $sus_of('post_content') . " ORDER BY post_modified DESC LIMIT 40"));

show('postmeta 的可疑內容（Elementor 等頁面資料）', q("SELECT pm.post_id, pm.meta_key, LENGTH(pm.meta_value) len FROM {prefix}postmeta pm
	WHERE pm.meta_key NOT LIKE '\\_wp\\_attachment%' AND (pm.meta_value LIKE '%eval(%' OR pm.meta_value LIKE '%base64_decode%' OR pm.meta_value LIKE '%-9999px%' OR pm.meta_value REGEXP '$kw_sql') LIMIT 40"));

show('文章每月修改數（找出異常的大量修改）', q("SELECT DATE_FORMAT(post_modified,'%Y-%m') m, COUNT(*) n FROM {prefix}posts
	WHERE post_type NOT IN ('revision','nav_menu_item') GROUP BY m ORDER BY m DESC LIMIT 18"));

// 資安外掛的紀錄表：列出筆數，方便判斷哪些紀錄可以拿來追查
$tables = q("SHOW TABLES");
$names = is_array($tables) ? array_map(fn($r) => reset($r), $tables) : [];
$logs = array_values(array_filter($names, fn($t) => preg_match('/(wflogins|wfhits|wfstatus|wfissues|wfsecurityevents|wfauditevents|simple_history$|aio_login|limit_login|llar|wsal|itsec|stream$|activity_log|statistics_visitor|statistics_pages|actionscheduler_logs)/i', $t)));
echo "\n== 可用的紀錄資料表（筆數；細節用 lwp <站台> forensic sql 查）\n";
foreach ($logs as $t) {
	$c = q("SELECT COUNT(*) n FROM `$t`");
	echo '  ' . str_pad($t, 40) . (is_array($c) ? $c[0]['n'] : $c) . "\n";
}
$other = array_values(array_filter($names, fn($t) => strpos($t, $prefix) !== 0));
if ($other) {
	echo "\n== 不是 {$prefix} 前綴的資料表（可能是其他站、舊安裝或攻擊者建立）\n  " . implode('  ', $other) . "\n";
}
echo "\n提示：Wordfence 的 wfstatus 會記錄每次掃描發現的檔案（「添加问题」「Adding issue」），常能找到最早被發現的時間點：\n"
	. "  lwp <站台> forensic sql \"SELECT FROM_UNIXTIME(ctime) t, msg FROM {prefix}wfstatus WHERE msg LIKE '%issue%' OR msg LIKE '%问题%' ORDER BY ctime\"\n";
