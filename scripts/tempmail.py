# -*- coding: utf-8 -*-
"""tempmail — 通用临时邮箱查询 CLI（配合 cloudflare_temp_email 自部署实例）。

所有配置从本脚本同目录 config.json 读取：
  {
    "base_url": "https://your-mail.example.com",   # 你的 cloudflare_temp_email 部署地址
    "password": "your-site-password",              # 站点访问密码 (x-custom-auth)
    "address":  "tmpwhatever@your.domain",         # 当前收件地址
    "jwt":      "eyJ...",                          # 该地址的访问 JWT
    "register_password": "..."                     # 可选：注册外部网站账号时统一使用的密码
  }
参考 config.example.json。

用法:
  python tempmail.py check          最新邮件（默认 5 封，自动提取验证码）
  python tempmail.py check -n 10    最新 10 封
  python tempmail.py code           只在最新邮件里找验证码
  python tempmail.py mails -n 20    列出邮件（id/发件人/主题/时间）
  python tempmail.py read 17        按 id 查看完整正文
  python tempmail.py address        显示当前邮箱地址
  python tempmail.py new [名字]     新建地址（留空=随机），并更新配置里的 jwt/地址
  python tempmail.py password       显示注册外部网站账号时统一使用的密码

服务端项目: https://github.com/dreamhunter2333/cloudflare_temp_email
"""
import sys, os, json, re, argparse, email
from email import policy
from email.header import decode_header

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) tempmail-cli/1.0"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def load_cfg():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_cfg(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def api(cfg, method, path, payload=None):
    import urllib.request
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        cfg["base_url"] + path,
        data=data,
        headers={
            "x-custom-auth": cfg["password"],
            "Authorization": "Bearer " + cfg.get("jwt", ""),
            "Content-Type": "application/json",
            "User-Agent": UA,
        },
        method=method,
    )
    return urllib.request.urlopen(req, timeout=30)


def decode_mime(s):
    if not s:
        return ""
    try:
        out = []
        for b, c in decode_header(s):
            if isinstance(b, bytes):
                out.append(b.decode(c or "utf-8", "ignore"))
            else:
                out.append(str(b))
        return "".join(out)
    except Exception:
        return str(s)


def parse_raw(raw):
    msg = email.message_from_string(raw, policy=policy.default)
    frm = decode_mime(msg.get("From", ""))
    subj = decode_mime(msg.get("Subject", ""))
    date = msg.get("Date", "")
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct in ("text/plain", "text/html"):
                try:
                    body = part.get_content()
                except Exception:
                    continue
                if ct == "text/plain":
                    break
    else:
        try:
            body = msg.get_content()
        except Exception:
            body = raw
    if isinstance(body, bytes):
        body = body.decode("utf-8", "ignore")
    return frm, subj, date, body


CODE_RE = re.compile(
    r"(?:验证码|verification code|code is|code:|OTP|pin|确认码)[^0-9A-Z]{0,20}([0-9A-Z]{4,8})",
    re.IGNORECASE,
)


def find_code(text):
    for m in CODE_RE.finditer(text):
        return m.group(1)
    for m in re.finditer(r"\b(\d{4,8})\b", text):
        return m.group(1)
    return None


def cmd_list(cfg, n, only_code=False):
    try:
        data = json.loads(api(cfg, "GET", f"/api/mails?limit={n}&offset=0").read())
    except Exception as e:
        body = getattr(e, "read", lambda: b"")()
        print(f"查询失败: {e} {body[:200]}")
        if "401" in str(e):
            print("JWT 已失效。用 `python tempmail.py new` 重建地址。")
        return
    results = data.get("results", [])
    if not results:
        print(f"收件箱为空（当前地址 {cfg['address']}）")
        return
    for row in results:
        frm, subj, date, body = parse_raw(row.get("raw", ""))
        print(f"--- id={row['id']} | {date} ---")
        print(f"From: {frm}")
        print(f"Subject: {subj}")
        text = re.sub(r"<[^>]+>", " ", body)
        text = re.sub(r"\s+", " ", text).strip()
        if only_code:
            code = find_code(subj) or find_code(body)
            if code:
                print(f"验证码: {code}")
        else:
            print(text[:400])
            code = find_code(subj) or find_code(body)
            if code:
                print(f"[可能验证码: {code}]")


def cmd_read(cfg, mail_id):
    d = json.loads(api(cfg, "GET", f"/api/mail/{mail_id}").read())
    if not d:
        print(f"没有 id={mail_id} 的邮件（或属于其他地址）")
        return
    frm, subj, date, body = parse_raw(d.get("raw", ""))
    print(f"From: {frm}\nDate: {date}\nSubject: {subj}\n")
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", body)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t\r]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    print(text.strip())


def cmd_new(cfg, name=None):
    d = json.loads(api(cfg, "POST", "/api/new_address",
                       {"name": name or "", "domain": None}).read())
    cfg["address"] = d["address"]
    cfg["jwt"] = d["jwt"]
    save_cfg(cfg)
    print(f"新地址: {d['address']}（已设为当前地址）")


def main():
    ap = argparse.ArgumentParser(description="查询临时邮箱")
    ap.add_argument("cmd", nargs="?", default="check",
                    choices=["check", "mails", "read", "code", "address", "new", "password"])
    ap.add_argument("-n", type=int, default=5)
    ap.add_argument("arg", nargs="?", default=None)
    args = ap.parse_args()
    cfg = load_cfg()
    if args.cmd == "address":
        print(cfg["address"])
    elif args.cmd == "password":
        pwd = cfg.get("register_password", "")
        if pwd:
            print(pwd)
        else:
            print("config.json 未设置 register_password。请向用户索取统一注册密码，不要自己另设。")
    elif args.cmd == "new":
        cmd_new(cfg, args.arg)
    elif args.cmd == "read":
        cmd_read(cfg, args.arg)
    elif args.cmd == "code":
        cmd_list(cfg, args.n, only_code=True)
    else:
        cmd_list(cfg, args.n)


if __name__ == "__main__":
    main()
