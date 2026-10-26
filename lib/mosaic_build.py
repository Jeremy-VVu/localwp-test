"""lwp mosaic-build 的輔助程式：產生／檢查 mosaic-headless 的 session 設定、列出 site spec 的頁面。
憑證從環境變數讀，不放在命令列參數裡。"""
import json
import os
import sys
from urllib.parse import urlparse


def host_ok(url, domain):
    h = (urlparse(url).hostname or "").lower()
    return h == domain.lower()


def write_cfg(out, cfg):
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh)
    try:
        os.chmod(out, 0o600)
    except OSError:
        pass


def main():
    cmd = sys.argv[1]
    if cmd == "mint":
        # 環境變數：MB_SITEURL MB_COOKIE MB_NONCE MB_THEME MB_VERSION MB_DOMAIN；參數：輸出檔
        e = os.environ
        if not host_ok(e["MB_SITEURL"], e["MB_DOMAIN"]):
            sys.exit("lwp: 產生的 session 網址 %s 不是站台網域 %s，停止" % (e["MB_SITEURL"], e["MB_DOMAIN"]))
        write_cfg(sys.argv[2], {"base": e["MB_SITEURL"].rstrip("/"), "cookie": e["MB_COOKIE"], "nonce": e["MB_NONCE"],
                                "themeID": e["MB_THEME"], "version": e["MB_VERSION"]})
    elif cmd == "check":
        # 參數：使用者給的設定檔 輸出檔 站台網域 themeID version
        src, out, domain, theme, version = sys.argv[2:7]
        cfg = json.load(open(src, encoding="utf-8"))
        base = str(cfg.get("base", ""))
        if not host_ok(base, domain):
            sys.exit("lwp: 設定檔的 base 是 %r，不是這個本機站台（%s）。mosaic-build 只寫入本機站台，停止。" % (base, domain))
        for k in ("cookie", "nonce"):
            if not cfg.get(k):
                sys.exit("lwp: 設定檔缺少 %s" % k)
        if cfg.get("themeID") not in (None, theme):
            print("lwp: 設定檔的 themeID %s 不是啟用中的 Mosaic 佈景主題，改用 %s" % (cfg["themeID"], theme), file=sys.stderr)
        if cfg.get("version") not in (None, version):
            print("lwp: 設定檔的 version %s 與外掛版本不同，改用 %s" % (cfg["version"], version), file=sys.stderr)
        cfg.update(themeID=theme, version=version)
        write_cfg(out, cfg)
    elif cmd == "pages":
        # 列出 site spec 要寫的頁面：post_id<TAB>slug<TAB>title
        site = json.load(open(sys.argv[2], encoding="utf-8"))
        print("master\t%s" % site.get("master", "Site shell"))
        print("components\t%d" % len(site.get("components") or {}))
        for p in site.get("pages") or []:
            print("page\t%s\t%s\t%s" % (p.get("post_id", ""), p.get("slug", ""), p.get("title", "")))
    else:
        sys.exit("unknown: %s" % cmd)


if __name__ == "__main__":
    main()
