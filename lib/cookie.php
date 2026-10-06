<?php
/**
 * 產生登入 cookie（Netscape 格式，curl 與瀏覽器腳本共用）：
 *   wp eval-file cookie.php <輸出檔> [使用者登入名稱或 ID]
 * 未指定使用者時，使用第一個 administrator。
 */
if ( empty($args[0]) ) {
	WP_CLI::error('缺少輸出檔路徑');
}
$out = $args[0];

if ( !empty($args[1]) ) {
	$user = is_numeric($args[1]) ? get_user_by('id', (int) $args[1]) : get_user_by('login', $args[1]);
} else {
	$admins = get_users(['role' => 'administrator', 'number' => 1, 'orderby' => 'ID', 'order' => 'ASC']);
	$user = $admins ? $admins[0] : false;
}
if ( !$user ) {
	WP_CLI::error('找不到使用者');
}

$host = wp_parse_url(home_url(), PHP_URL_HOST);
$secure = is_ssl() || (wp_parse_url(admin_url(), PHP_URL_SCHEME) === 'https');
$exp = time() + 6 * HOUR_IN_SECONDS;
$authName = $secure ? SECURE_AUTH_COOKIE : AUTH_COOKIE;
$authScheme = $secure ? 'secure_auth' : 'auth';
$flag = $secure ? 'TRUE' : 'FALSE';

$jar = "# Netscape HTTP Cookie File\n";
foreach ([[$authName, $authScheme, ADMIN_COOKIE_PATH], [$authName, $authScheme, PLUGINS_COOKIE_PATH], [LOGGED_IN_COOKIE, 'logged_in', COOKIEPATH]] as $c) {
	$val = wp_generate_auth_cookie($user->ID, $exp, $c[1]);
	$jar .= "{$host}\tFALSE\t{$c[2]}\t{$flag}\t{$exp}\t{$c[0]}\t{$val}\n";
}
file_put_contents($out, $jar);
file_put_contents($out . '.meta', json_encode([
	'user'    => $user->user_login,
	'user_id' => $user->ID,
	'home'    => home_url(),
	'expires' => $exp,
]));
WP_CLI::success("cookie for {$user->user_login} (ID {$user->ID}) → {$out}");
