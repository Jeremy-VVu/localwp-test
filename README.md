# localwp-test

English | [繁體中文](README.zh-TW.md)

A [Claude Code](https://claude.com/claude-code) skill for testing WordPress plugins and themes on [LocalWP](https://localwp.com/) (Local by Flywheel) development sites.

Everything goes through a single entry point, `bin/lwp`, so one permission rule in Claude Code is enough to skip the confirmation prompt on every call.

> **Note:** `SKILL.md` (the instructions Claude reads) and the tool's output messages are written in Traditional Chinese. Claude understands them regardless of the language you chat in.

## Features

- **WP-CLI** using LocalWP's bundled PHP, php.ini and WP-CLI. Destructive operations are blocked unless `--lwp-yes` is passed explicitly.
- **Read-only SQL**: only SELECT / SHOW / DESCRIBE / EXPLAIN are allowed.
- **PHP lint across versions**: checks with the site's PHP version and any others you list (e.g. 7.4, 8.4).
- **Authenticated page requests**: generates an admin login cookie and reports the HTTP status and any PHP errors on the page.
- **Headless browser smoke tests**: can crawl every page in the wp-admin sidebar, catching console errors, uncaught exceptions and 4xx/5xx responses. Repeated messages are merged and known environment noise is filtered out.
- **Custom browser scripts** via `require('lwp-browser')`, built on puppeteer.
- **WP_DEBUG_LOG toggle and grouped summary**: turning it off restores a byte-identical copy of the original `wp-config.php`.
- **Outbound HTTP request logging and blocking**, **database snapshots and restore**, and **temporary test file management**.

## Supported platforms

| | Windows (Git Bash) | Linux | macOS |
|---|---|---|---|
| Local data directory | `%APPDATA%\Local` | `~/.config/Local` | `~/Library/Application Support/Local` |
| Browser | Edge → Chrome | Edge → Chrome → Chromium | Edge → Chrome → Chromium |

Requirements: bash, python3 (`python` on Windows), node, curl, and one of Edge, Chrome or Chromium.

## Installation

```bash
git clone https://github.com/Jeremy-VVu/localwp-test.git ~/.claude/skills/localwp-test
cd ~/.claude/skills/localwp-test
npm ci            # installs puppeteer-core inside the skill directory only
chmod +x bin/lwp
```

Add a permission rule to `~/.claude/settings.json` so Claude Code can call lwp without asking each time:

```json
{
  "permissions": {
    "allow": [
      "Bash(~/.claude/skills/localwp-test/bin/lwp)",
      "Bash(~/.claude/skills/localwp-test/bin/lwp *)"
    ]
  }
}
```

## Usage

```bash
lwp list                                   # list all Local sites
lwp <site> info                            # PHP, database and plugin status
lwp <site> debug on                        # enable debug logging
lwp <site> smoke --all-admin --no-shots /  # crawl the front page and the whole wp-admin menu
lwp <site> debug summary                   # group debug.log entries by type and file
lwp <site> cleanup                         # restore wp-config.php, stop the browser, etc.
```

Run `lwp help` for the full command list. The operating rules, safety rules and known-noise list that Claude follows are in [`SKILL.md`](SKILL.md).

## Notes

- lwp only works on local sites registered in LocalWP's `sites.json`. It cannot, and should never be used to, touch production sites.
- Output (cookies, screenshots, snapshots) goes to `<site>/app/.lwp-test/`, outside the site's public directory.
- The browser profile lives in the user cache directory (e.g. `~/.cache/localwp-test/`) and can be deleted at any time.

## License

[MIT](LICENSE)
