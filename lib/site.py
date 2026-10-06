"""從 LocalWP 的 sites.json 解析單一站台的執行環境，輸出 bash 可 eval 的 export 指令。

用法：
  python site.py list            列出所有站台（名稱、網域、路徑），不輸出任何帳密
  python site.py env <站台>       輸出該站台的環境變數（站台可用名稱、網域、id 或資料夾名稱指定）
"""
import glob
import json
import os
import shlex
import sys

if os.name == 'nt':
    PLATFORM = 'windows'
    LOCAL_DIR = os.path.join(os.environ.get('APPDATA') or os.path.expanduser(r'~\AppData\Roaming'), 'Local')
    WPCLI_CANDIDATES = [
        r'C:\Program Files (x86)\Local\resources\extraResources\bin\wp-cli',
        r'C:\Program Files\Local\resources\extraResources\bin\wp-cli',
        os.path.join(os.environ.get('LOCALAPPDATA', ''), r'Programs\Local\resources\extraResources\bin\wp-cli'),
    ]
    # lightning-services 內各服務執行檔的相對路徑
    PHP_RELS = [r'bin\win64\php.exe', r'bin\win32\php.exe']
    MYSQL_RELS = [r'bin\win64\bin\mysql.exe', r'bin\win32\bin\mysql.exe']
elif sys.platform == 'darwin':
    PLATFORM = 'mac'
    LOCAL_DIR = os.path.expanduser('~/Library/Application Support/Local')
    WPCLI_CANDIDATES = ['/Applications/Local.app/Contents/Resources/extraResources/bin/wp-cli']
    PHP_RELS = ['bin/darwin-arm64/bin/php', 'bin/darwin/bin/php']
    MYSQL_RELS = ['bin/darwin-arm64/bin/mysql', 'bin/darwin/bin/mysql']
else:
    PLATFORM = 'linux'
    LOCAL_DIR = os.path.join(os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'), 'Local')
    WPCLI_CANDIDATES = ['/opt/Local/resources/extraResources/bin/wp-cli']
    PHP_RELS = ['bin/linux/bin/php']
    MYSQL_RELS = ['bin/linux/bin/mysql']
SITES_JSON = os.path.join(LOCAL_DIR, 'sites.json')
SERVICES = os.path.join(LOCAL_DIR, 'lightning-services')
RUN_DIR = os.path.join(LOCAL_DIR, 'run')


def fwd(p):
    return p.replace('\\', '/') if p else ''


def die(msg):
    print(f'echo {shlex.quote("lwp: " + msg)} >&2; exit 2')
    sys.exit(0)


def load_sites():
    if not os.path.isfile(SITES_JSON):
        die(f'找不到 {SITES_JSON}，這台電腦可能沒有安裝 LocalWP')
    with open(SITES_JSON, encoding='utf-8') as f:
        return json.load(f)


def find_site(sites, key):
    key_l = key.lower()
    for sid, s in sites.items():
        names = {sid.lower(), str(s.get('name', '')).lower(), str(s.get('domain', '')).lower(),
                 os.path.basename(str(s.get('path', '')).rstrip('\\/')).lower()}
        if key_l in names:
            return sid, s
    return None, None


def service_bin(kind, version, rel_candidates):
    """在 lightning-services 找符合版本的執行檔（例如 php-8.2.29+0/bin/win64/php.exe）。"""
    dirs = sorted(glob.glob(os.path.join(SERVICES, f'{kind}-{version}*')), reverse=True)
    for d in dirs:
        for rel in rel_candidates:
            p = os.path.join(d, rel)
            if os.path.isfile(p):
                return p
    return ''


def cmd_list():
    sites = load_sites()
    print(f"{'name':24} {'domain':28} path")
    for sid, s in sorted(sites.items(), key=lambda x: str(x[1].get('name', '')).lower()):
        print(f"{str(s.get('name', ''))[:24]:24} {str(s.get('domain', ''))[:28]:28} {s.get('path', '')}")


def cmd_env(key):
    sites = load_sites()
    sid, s = find_site(sites, key)
    if not s:
        die(f'找不到站台「{key}」。可用 lwp list 查看所有站台')
    services = s.get('services', {})
    php_v = services.get('php', {}).get('version') or s.get('phpVersion', '')
    db = services.get('mysql') or services.get('mariadb') or {}
    db_kind = db.get('name', 'mysql')
    db_v = db.get('version', '')
    db_port = (db.get('ports', {}).get('MYSQL') or [''])[0]

    php = service_bin('php', php_v, PHP_RELS)
    mysql = service_bin(db_kind, db_v, MYSQL_RELS)
    wpcli = next((os.path.join(d, 'wp-cli.phar') for d in WPCLI_CANDIDATES if os.path.isfile(os.path.join(d, 'wp-cli.phar'))), '')
    conf = os.path.join(RUN_DIR, sid, 'conf')
    site_path = s.get('path', '')

    if not php:
        die(f'找不到 PHP {php_v} 執行檔（{SERVICES}）')
    if not wpcli:
        die('找不到 Local 內建的 wp-cli.phar')

    env = {
        'LWP_ID': sid,
        'LWP_NAME': s.get('name', ''),
        'LWP_DOMAIN': s.get('domain', ''),
        'LWP_SITE_DIR': fwd(site_path),
        'LWP_PUBLIC': fwd(os.path.join(site_path, 'app', 'public')),
        'LWP_PLATFORM': PLATFORM,
        'LWP_SERVICES': fwd(SERVICES),
        'LWP_PHP': fwd(php),
        'LWP_PHP_VERSION': php_v,
        'LWP_PHP_INI': fwd(os.path.join(conf, 'php', 'php.ini')),
        'LWP_MYSQL_HOME': fwd(os.path.join(conf, 'mysql')),
        'LWP_MYSQL_BIN_DIR': fwd(os.path.dirname(mysql)) if mysql else '',
        'LWP_DB_PORT': str(db_port),
        'LWP_DB_VERSION': f'{db_kind} {db_v}',
        'LWP_WPCLI': fwd(wpcli),
        'LWP_WPCLI_CONFIG': fwd(os.path.join(os.path.dirname(wpcli), 'config.yaml')),
        'LWP_MULTISITE': str(s.get('multiSite', '') or ''),
    }
    for k, v in env.items():
        print(f'export {k}={shlex.quote(v)}')


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'list':
        cmd_list()
    elif len(sys.argv) >= 3 and sys.argv[1] == 'env':
        cmd_env(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)
