"""唯讀的檔案鑑識工具（lwp files／stat／forensic 的實作），只讀檔案，不寫入、不刪除、不執行任何站台程式碼。

用法（由 bin/lwp 呼叫，第一個參數是站台的 public 路徑）：
  python forensic.py <public> files [路徑...] [--name=GLOB,...] [--after=YYYY-MM-DD] [--before=YYYY-MM-DD]
                                    [--php] [--hidden] [--ww] [--min-size=N] [--max=N] [--sort=time|path|size]
  python forensic.py <public> stat <檔案...>
  python forensic.py <public> mtimes [路徑...] [--by=day|month|hour] [--min=N] [--on=YYYY-MM-DD] [--depth=N]
  python forensic.py <public> scan [--ioc=正規式] [--since=YYYY-MM-DD]
"""
import collections
import datetime
import fnmatch
import hashlib
import os
import re
import stat as st
import sys

PUBLIC = os.path.normpath(sys.argv[1])
CONTENT = os.path.join(PUBLIC, 'wp-content')
# 可被 PHP 執行的副檔名（含 Apache 常見的替代副檔名）
PHP_EXT = re.compile(r'\.(php\d?|phtml|phar|pht|phps|inc)$', re.I)
# 常見後門寫法：eval／assert 包解碼函式或使用者輸入、preg_replace /e、把輸入當函式呼叫
BACKDOOR = re.compile(
    rb'eval\s*\(\s*(base64_decode|gzinflate|gzuncompress|gzdecode|str_rot13|strrev|hex2bin|\$_(POST|GET|REQUEST|COOKIE|SERVER))'
    rb'|assert\s*\(\s*\$_(POST|GET|REQUEST|COOKIE)'
    rb'|preg_replace\s*\(\s*[\'"](.).*\3[a-z]*e[a-z]*[\'"]\s*,'
    rb'|\$_(POST|GET|REQUEST|COOKIE)\s*\[[^\]\s]{1,40}\]\(\s*\$'
    rb'|create_function\s*\([^)]*\$_(POST|GET|REQUEST|COOKIE)'
    rb'|(move_uploaded_file|file_put_contents)\s*\([^;]{0,120}\$_(FILES|POST|GET|REQUEST)'
    rb'|(eval|assert)\s*\(\s*["\']\\x[0-9a-f]{2}',  # eval("\x65\x76...") 這類十六進位混淆；單純的 \x 字串在加密函式庫很常見，不列入
    re.I)
# 掃描時略過的目錄：快取、備份、版本控制，以及 lwp 自己的輸出
SKIP_DIRS = {'.git', 'node_modules', 'ai1wm-backups', 'updraft', 'cache', 'wflogs', '.lwp-test'}
KNOWN_HIDDEN = {'.htaccess', '.gitignore', '.gitkeep', '.editorconfig', '.DS_Store', '.babelrc', '.eslintrc', '.prettierrc',
                '.distignore', '.gitattributes', '.browserslistrc', '.stylelintrc', '.nvmrc', '.npmignore', '.jshintrc'}
DROPINS = {'advanced-cache.php', 'object-cache.php', 'db.php', 'db-error.php', 'install.php', 'maintenance.php',
           'php-error.php', 'fatal-error-handler.php', 'sunrise.php', 'blog-deleted.php', 'blog-inactive.php', 'blog-suspended.php', 'index.php'}


def rel(p):
    r = os.path.relpath(p, PUBLIC)
    return p.replace('\\', '/') if r.startswith('..') else r.replace('\\', '/')


def resolve(p):
    if os.path.isabs(p) or re.match(r'^[A-Za-z]:', p):
        return p
    return p if os.path.exists(p) else os.path.join(PUBLIC, p)


def walk(roots, skip=True):
    for root in roots:
        if os.path.isfile(root):
            yield root
            continue
        for d, dirs, files in os.walk(root):
            if skip:
                dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for f in files:
                yield os.path.join(d, f)


def ts(t, sec=False):
    return datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S' if sec else '%Y-%m-%d %H:%M')


def mode_str(m):
    # Windows 沒有 Unix 權限，os.stat 一律回傳 666／444，顯示出來反而會誤導
    return '---' if os.name == 'nt' else oct(st.S_IMODE(m))[2:].rjust(3, '0')


def world_writable(m):
    return os.name != 'nt' and bool(m & st.S_IWOTH)


def parse_date(s):
    return datetime.datetime.strptime(s, '%Y-%m-%d').timestamp()


def split_args(args):
    opts, pos = {}, []
    for a in args:
        if a.startswith('--'):
            k, _, v = a[2:].partition('=')
            opts[k] = v if _ else True
        else:
            pos.append(a)
    return opts, pos


def read_head(p, n=4096):
    try:
        with open(p, 'rb') as fh:
            return fh.read(n)
    except OSError:
        return b''


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def cmd_files(args):
    o, pos = split_args(args)
    roots = [resolve(p) for p in pos] or [PUBLIC]
    names = [x for x in str(o.get('name', '')).split(',') if x] if o.get('name') not in (None, True) else []
    after = parse_date(o['after']) if 'after' in o else None
    before = parse_date(o['before']) if 'before' in o else None
    minsize = int(o.get('min-size', 0))
    limit = int(o.get('max', 300))
    rows = []
    for p in walk(roots, skip='all' not in o):
        b = os.path.basename(p)
        if names and not any(fnmatch.fnmatch(b, n) for n in names):
            continue
        if 'php' in o and not PHP_EXT.search(b):
            continue
        if 'hidden' in o and not b.startswith('.'):
            continue
        try:
            s = os.lstat(p)
        except OSError:
            continue
        if after and s.st_mtime < after or before and s.st_mtime >= before or s.st_size < minsize:
            continue
        if 'ww' in o and not world_writable(s.st_mode):
            continue
        rows.append((s.st_mtime, s.st_size, s.st_mode, rel(p)))
    key = {'path': lambda r: r[3], 'size': lambda r: -r[1]}.get(o.get('sort'), lambda r: r[0])
    rows.sort(key=key)
    for m, size, mode, p in rows[:limit]:
        print(f'{ts(m)}  {size:>10}  {mode_str(mode)}  {p}')
    print(f'── 共 {len(rows)} 個檔案' + (f'（只顯示前 {limit} 個，用 --max=N 調整）' if len(rows) > limit else ''))


def cmd_stat(args):
    for a in args:
        p = resolve(a)
        if not os.path.isfile(p):
            print(f'找不到 {p}')
            continue
        s = os.lstat(p)
        head = read_head(p, 400).split(b'\n')
        first = next((x for x in head if x.strip() and x.strip() != b'<?php'), b'').decode('utf-8', 'replace').strip()[:120]
        print(f'{rel(p)}\n  大小 {s.st_size}  權限 {mode_str(s.st_mode)}  md5 {md5(p)}'
              f'\n  修改 {ts(s.st_mtime, True)}  變更 {ts(s.st_ctime, True)}  存取 {ts(s.st_atime, True)}'
              f'\n  首行 {first}')


def cmd_mtimes(args):
    o, pos = split_args(args)
    roots = [resolve(p) for p in pos] or [CONTENT]
    fmt = {'month': '%Y-%m', 'hour': '%Y-%m-%d %H:00'}.get(o.get('by'), '%Y-%m-%d')
    on = o.get('on')
    depth = int(o.get('depth', 3))
    c = collections.Counter()
    for p in walk(roots, skip='all' not in o):
        try:
            m = os.lstat(p).st_mtime
        except OSError:
            continue
        d = datetime.datetime.fromtimestamp(m)
        if on:
            if d.strftime('%Y-%m-%d') == on:
                c['/'.join(rel(p).split('/')[:depth])] += 1
        else:
            c[d.strftime(fmt)] += 1
    if on:
        print(f'== {on} 修改的檔案，依前 {depth} 層路徑分組')
        for k, n in c.most_common(40):
            print(f'{n:>7}  {k}')
    else:
        mn = int(o.get('min', 1))
        hidden = sum(1 for k in c if c[k] < mn)
        print('== 檔案修改時間分布（同一時間大量檔案通常是搬站、還原或更新；零星檔案才值得細看）')
        for k in sorted(c):
            if c[k] >= mn:
                print(f'{c[k]:>7}  {k}')
        if hidden:
            print(f'── 另有 {hidden} 個時段少於 {mn} 個檔案，未顯示')


def section(title):
    print(f'\n== {title}')


def cmd_scan(args):
    o, _ = split_args(args)
    ioc = re.compile(o['ioc'].encode(), re.I) if isinstance(o.get('ioc'), str) else None
    since = parse_date(o['since']) if 'since' in o else None
    up = os.path.join(CONTENT, 'uploads')

    section('uploads 內可執行的 PHP 檔（正常站台不該有，空白 index.php 除外）')
    n = 0
    for p in walk([up], skip=False):
        if PHP_EXT.search(p):
            s = os.lstat(p)
            body = read_head(p, 300)
            tag = '（只有 Silence is golden）' if s.st_size < 120 and b'silence' in body.lower() else '  ← 可疑'
            print(f'  {ts(s.st_mtime)}  {s.st_size:>8}  {rel(p)}{tag}')
            n += 1
    n or print('  （無）')

    section('mu-plugins（後台無法停用，惡意程式常用的位置）')
    mu = os.path.join(CONTENT, 'mu-plugins')
    if os.path.isdir(mu):
        for f in sorted(os.listdir(mu)):
            p = os.path.join(mu, f)
            if os.path.isfile(p):
                s = os.lstat(p)
                head = read_head(p, 1500)
                m = re.search(rb'Plugin Name[ \t]*:[ \t]*([^\r\n]*)', head) or re.search(rb'^[ \t]*\*[ \t]*([A-Za-z][^\r\n]{3,70})', head, re.M)
                label = m.group(1).decode('utf-8', 'replace').strip(' *')[:70] if m else ''
                print(f'  {ts(s.st_mtime)}  {s.st_size:>8}  {f}  {label}')
            else:
                print(f'  (目錄) {f}/')
    else:
        print('  （沒有 mu-plugins 目錄）')

    section('wp-content 根目錄的 PHP（drop-in 以外的都要看）')
    for f in sorted(os.listdir(CONTENT)):
        p = os.path.join(CONTENT, f)
        if os.path.isfile(p) and PHP_EXT.search(f):
            s = os.lstat(p)
            print(f'  {ts(s.st_mtime)}  {s.st_size:>8}  {f}' + ('' if f in DROPINS else '  ← 不是標準 drop-in'))

    section('.htaccess／.user.ini／php.ini 中的 auto_prepend、auto_append、讓 PHP 執行的 Handler')
    n = 0
    pat = re.compile(rb'auto_prepend_file|auto_append_file|(Add|Set)Handler[^\n]*php|AddType[^\n]*php|php_value\s+(include_path|engine)', re.I)
    for p in walk([PUBLIC], skip=False):
        if os.path.basename(p) in ('.htaccess', '.user.ini', 'php.ini'):
            try:
                data = open(p, 'rb').read()
            except OSError:
                continue
            for i, line in enumerate(data.split(b'\n'), 1):
                if pat.search(line):
                    print(f'  {rel(p)}:{i}  {line.decode("utf-8", "replace").strip()[:140]}')
                    n += 1
    n or print('  （無）')

    section('wp-content 內不認識的隱藏檔（.rs_*、.cache.php 這類常是惡意程式的資料檔）')
    n = 0
    for p in walk([CONTENT]):
        b = os.path.basename(p)
        if b.startswith('.') and b not in KNOWN_HIDDEN and not b.startswith('.eslintrc') and '/node_modules/' not in p.replace('\\', '/'):
            s = os.lstat(p)
            print(f'  {ts(s.st_mtime)}  {s.st_size:>8}  {rel(p)}')
            n += 1
            if n >= 60:
                print('  …（超過 60 筆，請用 lwp files --hidden 細看）')
                break
    n or print('  （無）')

    section('權限 777／所有人可寫的檔案')
    if os.name == 'nt':
        print('  （Windows 上沒有 Unix 權限，略過；需到原主機用 find -perm -o+w 檢查）')
    else:
        n = 0
        for p in walk([PUBLIC]):
            if world_writable(os.lstat(p).st_mode):
                print(f'  {rel(p)}')
                n += 1
        n or print('  （無）')

    section('常見後門寫法（eval＋解碼、把輸入當函式呼叫、寫入上傳內容等）' + ('與自訂 IOC' if ioc else ''))
    n = 0
    for p in walk([PUBLIC]):
        if not PHP_EXT.search(p) and not (ioc and p.endswith(('.js', '.html', '.json', '.txt'))):
            continue
        try:
            data = open(p, 'rb').read()
        except OSError:
            continue
        hits = []
        for rx, label in ((BACKDOOR, '後門寫法'), (ioc, 'IOC')):
            if rx is None or (label == '後門寫法' and not PHP_EXT.search(p)):
                continue
            m = rx.search(data)
            if m:
                line = data.count(b'\n', 0, m.start()) + 1
                hits.append(f'{label} 第 {line} 行：{m.group(0)[:60].decode("utf-8", "replace")}')
        for h in hits:
            print(f'  {rel(p)}  {h}')
            n += 1
    n or print('  （無）')
    print('  註：vendor 函式庫（phpseclib、polyfill 等）偶有誤判，要看內容判斷。')

    section('長行或高熵的 PHP（單行超過 5000 字元，可能是混淆程式碼；vendor、語系檔已排除）')
    n = 0
    for p in walk([CONTENT]):
        rp = rel(p)
        if not PHP_EXT.search(p) or re.search(r'/(vendor|vendor_prefixed|lib|libs|languages|unidata)/|\.l10n\.php$', rp):
            continue
        try:
            with open(p, 'rb') as fh:
                if any(len(line) > 5000 for line in fh):
                    print(f'  {rp}')
                    n += 1
        except OSError:
            pass
    n or print('  （無）')

    if since:
        section(f'{o["since"]} 之後修改的 PHP 檔')
        cmd_files(['--php', f'--after={o["since"]}', '--max=100', PUBLIC])

    print('\n提示：檔案時間戳記可能被搬站、還原或攻擊者竄改，判斷要看內容。核心與外掛比對請另跑：'
          '\n  lwp <站台> wp core verify-checksums'
          '\n  lwp <站台> wp plugin verify-checksums --all'
          '\n注意：.wpress／多數備份不含核心檔，還原後的核心是 Local 重新安裝的，核心比對結果不代表原主機狀態。')


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    cmd, args = sys.argv[2], sys.argv[3:]
    fn = {'files': cmd_files, 'stat': cmd_stat, 'mtimes': cmd_mtimes, 'scan': cmd_scan}.get(cmd)
    if not fn:
        print(__doc__)
        sys.exit(1)
    fn(args)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    main()
