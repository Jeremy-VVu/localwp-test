<?php
/**
 * 唯讀 SQL 查詢：wp eval-file sql.php "<SELECT ...>" [format]
 * 只允許 SELECT / SHOW / DESCRIBE / EXPLAIN，避免透過免確認的入口改動資料。
 * 表名可用 {prefix} 代表 $wpdb->prefix，例如 SELECT * FROM {prefix}options。
 */
global $wpdb;

if ( empty($args[0]) ) {
	WP_CLI::error('用法：lwp <站台> sql "SELECT ..." [table|json|csv]');
}
$sql = str_replace('{prefix}', $wpdb->prefix, $args[0]);
$format = isset($args[1]) ? $args[1] : 'table';

if ( !preg_match('/^\s*(SELECT|SHOW|DESCRIBE|DESC|EXPLAIN)\b/i', $sql) || preg_match('/;\s*\S/', $sql) ) {
	WP_CLI::error('sql 只允許單一的 SELECT／SHOW／DESCRIBE／EXPLAIN 查詢。要改資料請用 lwp <站台> wp ...，並先取得使用者同意。');
}

$rows = $wpdb->get_results($sql, ARRAY_A);
if ( $wpdb->last_error ) {
	WP_CLI::error($wpdb->last_error);
}
if ( empty($rows) ) {
	WP_CLI::line('(0 rows)');
	return;
}
WP_CLI\Utils\format_items($format, $rows, array_keys($rows[0]));
