<?php
/*
 * Plugin Name: LWP Test – HTTP Request Logger (temporary)
 * Description: 由 localwp-test skill 安裝的臨時 mu-plugin，記錄所有對外 HTTP 請求；列在 wp-content/lwp-http-block.txt 的網域會被擋下。用 `lwp <站台> httplog off` 移除。
 */
add_filter('pre_http_request', function ($preempt, $args, $url) {
	$caller = '';
	foreach (debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS) as $frame) {
		if ( isset($frame['file']) ) {
			$file = str_replace('\\', '/', $frame['file']);
			if ( (strpos($file, '/plugins/') !== false || strpos($file, '/themes/') !== false) && strpos($file, '/mu-plugins/') === false ) {
				$caller = preg_replace('#^.*?/wp-content#', '', $file) . ':' . $frame['line'];
				break;
			}
		}
	}

	$host = strtolower((string) wp_parse_url($url, PHP_URL_HOST));
	$blocked = false;
	$blockFile = WP_CONTENT_DIR . '/lwp-http-block.txt';
	if ( $host !== '' && is_readable($blockFile) ) {
		foreach (file($blockFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $pattern) {
			$pattern = strtolower(trim($pattern));
			if ( $pattern !== '' && ($host === $pattern || substr($host, -strlen('.' . $pattern)) === '.' . $pattern) ) {
				$blocked = true;
				break;
			}
		}
	}

	$method = isset($args['method']) ? $args['method'] : 'GET';
	file_put_contents(
		WP_CONTENT_DIR . '/lwp-http-log.txt',
		gmdate('c') . "\t{$method}\t{$url}\t{$caller}" . ($blocked ? "\tBLOCKED" : '') . "\n",
		FILE_APPEND | LOCK_EX
	);

	if ( $blocked ) {
		return new WP_Error('lwp_http_blocked', 'Blocked by localwp-test skill: ' . $host);
	}
	return $preempt;
}, 1, 3);
