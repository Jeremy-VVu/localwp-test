// lwp 瀏覽器子指令：smoke / shot / run
//   node browser.js smoke [--all-admin] [--no-shots] [--raw] <路徑...>
//   node browser.js shot <路徑> [名稱]
//   node browser.js run <腳本.js> [參數...]
const path = require('path');
const lwp = require('lwp-browser');

async function smoke(argv) {
	const allAdmin = argv.includes('--all-admin');
	const noShots = argv.includes('--no-shots');
	let paths = argv.filter(a => !a.startsWith('--'));

	if (allAdmin) {
		// 從後台左側選單收集所有頁面（含子選單），只取同站台的 wp-admin 連結
		const { page, close } = await lwp.open('/wp-admin/', { waitMs: 300 });
		const links = await page.$$eval('#adminmenu a[href]', as => as.map(a => a.href));
		await close();
		const seen = new Set(paths);
		for (const href of links) {
			if (!href.startsWith(lwp.BASE + '/wp-admin/')) continue;
			const p = href.slice(lwp.BASE.length).replace(/#.*$/, '');
			if (!seen.has(p)) { seen.add(p); paths.push(p); }
		}
	}
	if (!paths.length) paths = ['/wp-admin/'];

	// 已知、與站台程式無關的雜訊（見 SKILL.md「判讀結果」）。預設不列入問題，報告檔仍會記錄；--raw 可全部顯示
	const raw = argv.includes('--raw');
	const NOISE = [
		[/Permissions policy violation: unload is not allowed/, 'Chrome 停用 unload 事件的警告'],
		[/Google Maps JavaScript API error: RefererNotAllowedMapError/, 'Google Maps 金鑰未授權 localhost'],
		[/ipapi\.co\/json/, 'Elementor 後台查詢 ipapi.co 被 CORS 擋'],
		[/\/wp-json\/wp\/v2\/plugins\/ai[^ ]*/, 'WP 7.x Connectors 頁查詢未安裝的 AI 外掛'],
		[/kaspersky-labs\.com/, '本機 Kaspersky 注入的 script'],
		[/recaptcha\.net.*report-only Content Security Policy/, 'reCAPTCHA 的 report-only CSP 紀錄'],
	];
	const noiseOf = x => (NOISE.find(([re]) => re.test(x)) || [])[1];
	// 「Failed to load resource」本身沒有網址，無法判斷來源；同一頁其他訊息都是雜訊時才一起視為雜訊
	const splitNoise = list => {
		if (raw) return { real: list, noise: [] };
		const noise = list.filter(noiseOf);
		let real = list.filter(x => !noiseOf(x));
		if (noise.length && real.every(x => /^console: Failed to load resource/.test(x))) { noise.push(...real); real = []; }
		return { real, noise };
	};
	const noiseCount = new Map();

	// 同一頁重複的訊息合併成「×N」；終端只列有問題的頁面，完整結果（含 OK 頁面）寫進報告檔
	const dedupe = list => {
		const m = new Map();
		list.forEach(x => m.set(x, (m.get(x) || 0) + 1));
		return [...m].map(([x, n]) => (n > 1 ? `${x}  ×${n}` : x));
	};
	const report = [];
	const log = line => { report.push(line); console.log(line); };
	let total = 0, ok = 0;
	for (const p of paths) {
		const { page, problems, status, close } = await lwp.open(null).then(async o => {
			try { o.status = await lwp.goto(o.page, p); } catch (e) { o.problems.push('goto: ' + e.message); }
			return o;
		});
		problems.push(...(await lwp.phpErrors(page).catch(() => [])).map(e => 'php: ' + e));
		const title = await page.title().catch(() => '');
		let file = '';
		if (!noShots) file = await lwp.shot(page, 'smoke' + p).catch(() => '');
		const { real, noise } = splitNoise(problems);
		noise.forEach(x => { const k = noiseOf(x) || '其他（同頁的資源載入失敗）'; noiseCount.set(k, (noiseCount.get(k) || 0) + 1); });
		total += real.length;
		const line = `${real.length ? 'PROBLEM' : 'OK     '} ${String(status).padEnd(4)} ${p}  「${title.split('‹')[0].trim()}」`;
		if (real.length) {
			log(line);
			dedupe(real).forEach(x => log('          - ' + x));
		} else {
			ok++;
			report.push(line);
		}
		dedupe(noise).forEach(x => report.push('          (已忽略) ' + x));
		await close();
	}
	const file = path.join(lwp.OUT, 'smoke-report.txt');
	require('fs').writeFileSync(file, report.join('\n') + '\n');
	console.log(`\n${paths.length} 頁（OK ${ok}、有問題 ${paths.length - ok}），問題 ${total} 個；完整報告 ${file}` +
		(noShots ? '' : `；截圖在 ${path.join(lwp.OUT, 'shots')}`));
	if (noiseCount.size) {
		console.log('已忽略的已知雜訊（加 --raw 顯示）：' + [...noiseCount].map(([k, n]) => `${k} ${n} 筆`).join('、'));
	}
	process.exitCode = total ? 1 : 0;
}

async function shot(argv) {
	const [p, name] = argv;
	if (!p) throw new Error('用法：shot <路徑> [名稱]');
	const { page, problems, status, close } = await lwp.open(p);
	const file = await lwp.shot(page, name || 'shot' + p);
	console.log(`${status} ${p} → ${file}`);
	problems.forEach(x => console.log('  - ' + x));
	await close();
}

async function run(argv) {
	const [script, ...rest] = argv;
	if (!script) throw new Error('用法：run <腳本.js> [參數...]');
	process.argv = [process.argv[0], path.resolve(script), ...rest];
	require(path.resolve(script));
}

const [cmd, ...argv] = process.argv.slice(2);
const handlers = { smoke, shot, run };
if (!handlers[cmd]) {
	console.error('用法：browser.js smoke|shot|run ...');
	process.exit(2);
}
Promise.resolve(handlers[cmd](argv)).catch(e => { console.error('錯誤：' + e.message); process.exit(1); });
