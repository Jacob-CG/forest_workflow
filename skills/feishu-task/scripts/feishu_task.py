#!/usr/bin/env python3
"""以本人身份批量创建飞书任务（任务 v2 接口，user_access_token）。

用法：
  python3 feishu_task.py config --app-id cli_xxx --app-secret xxx
  python3 feishu_task.py auth
  python3 feishu_task.py add --due "2026-11-04 18:00" "任务1" "任务2" ...
  python3 feishu_task.py add --due "2026-11-04 18:00" --file tasks.txt [--dry-run]
  python3 feishu_task.py add --to 王迪 "任务标题"        # 负责人设为他人（按姓名搜索）
  python3 feishu_task.py send --chat 森林游戏 --at-all --file msg.txt [--dry-run]  # 以本人身份发群消息
  python3 feishu_task.py report                                   # 按周报模板整理本人任务 → weekly_report.txt
  python3 feishu_task.py send --chat 森林游戏 --at 陈刚 --file weekly_report.txt   # 发周报并 @陈刚

凭证和 token 存在 ~/.config/feishu_task/（权限 600），不放项目目录。
"""
import argparse
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

BASE = "https://open.feishu.cn/open-apis"
AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
REDIRECT_PORT = 8765
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/callback"
SCOPES = ("task:task:read task:task:write task:tasklist:read contact:user:search "
          "im:chat:read im:message im:message.send_as_user im:resource offline_access")
TZ = ZoneInfo("Asia/Shanghai")

CONF_DIR = os.path.expanduser("~/.config/feishu_task")
CONF_FILE = os.path.join(CONF_DIR, "config.json")
TOKEN_FILE = os.path.join(CONF_DIR, "token.json")


def save_json(path, data):
    os.makedirs(CONF_DIR, mode=0o700, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.chmod(path, 0o600)


def load_json(path, hint):
    if not os.path.exists(path):
        sys.exit(f"缺少 {path}，请先运行：{hint}")
    with open(path) as f:
        return json.load(f)


def request(method, path, body=None, token=None, params=None):
    url = path if path.startswith("http") else BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}") or {"code": e.code, "msg": str(e)}


def store_token(resp):
    if resp.get("code") != 0 or "access_token" not in resp:
        sys.exit(f"获取 token 失败：{json.dumps(resp, ensure_ascii=False)}")
    now = int(time.time())
    save_json(TOKEN_FILE, {
        "access_token": resp["access_token"],
        "expires_at": now + int(resp.get("expires_in", 7200)) - 120,
        "refresh_token": resp.get("refresh_token"),
        "refresh_expires_at": now + int(resp.get("refresh_token_expires_in", 0)),
    })


def cmd_config(args):
    save_json(CONF_FILE, {"app_id": args.app_id, "app_secret": args.app_secret})
    print(f"已保存到 {CONF_FILE}")


def cmd_auth(_args):
    conf = load_json(CONF_FILE, "python3 feishu_task.py config --app-id ... --app-secret ...")
    state = secrets.token_urlsafe(16)
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state and "code" in q:
                result["code"] = q["code"][0]
                msg = "授权成功，可以关闭此页面回到终端。"
            else:
                result["error"] = q.get("error", ["state 不匹配或缺少 code"])[0]
                msg = f"授权失败：{result['error']}"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(msg.encode())

        def log_message(self, *a):
            pass

    url = AUTHORIZE_URL + "?" + urllib.parse.urlencode({
        "client_id": conf["app_id"],
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "response_type": "code",
    })
    server = HTTPServer(("127.0.0.1", REDIRECT_PORT), Handler)
    print("正在打开浏览器授权，如未自动打开请手动访问：\n" + url)
    webbrowser.open(url)
    while not result:
        server.handle_request()
    server.server_close()
    if "code" not in result:
        sys.exit(f"授权失败：{result.get('error')}")

    store_token(request("POST", "/authen/v2/oauth/token", {
        "grant_type": "authorization_code",
        "client_id": conf["app_id"],
        "client_secret": conf["app_secret"],
        "code": result["code"],
        "redirect_uri": REDIRECT_URI,
    }))
    print(f"授权完成，token 已保存到 {TOKEN_FILE}")


def get_token():
    tok = load_json(TOKEN_FILE, "python3 feishu_task.py auth")
    now = int(time.time())
    if now < tok["expires_at"]:
        return tok["access_token"]
    if not tok.get("refresh_token") or now >= tok.get("refresh_expires_at", 0):
        sys.exit("token 已过期，请重新运行：python3 feishu_task.py auth")
    conf = load_json(CONF_FILE, "python3 feishu_task.py config ...")
    store_token(request("POST", "/authen/v2/oauth/token", {
        "grant_type": "refresh_token",
        "client_id": conf["app_id"],
        "client_secret": conf["app_secret"],
        "refresh_token": tok["refresh_token"],
    }))
    return load_json(TOKEN_FILE, "")["access_token"]


def parse_due(text):
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text, fmt).replace(tzinfo=TZ)
            return dt, fmt == "%Y-%m-%d"
        except ValueError:
            pass
    sys.exit(f"无法解析截止时间：{text}（格式 YYYY-MM-DD 或 'YYYY-MM-DD HH:MM'）")


def find_user(token, name):
    r = request("GET", "/search/v1/user", token=token, params={"query": name, "page_size": 20})
    if r.get("code") != 0:
        sys.exit(f"搜索用户失败：{json.dumps(r, ensure_ascii=False)}")
    users = r.get("data", {}).get("users", [])
    exact = [u for u in users if u.get("name") == name]
    if len(exact) == 1:
        return exact[0]["open_id"]
    cands = exact or users
    if not cands:
        sys.exit(f"找不到用户：{name}")
    lines = "\n".join(f"  {u.get('name')} {u.get('department_ids', '')} {u['open_id']}" for u in cands)
    sys.exit(f"「{name}」匹配到多个用户，请用 --to-open-id 指定：\n{lines}")


def cmd_add(args):
    titles = list(args.titles)
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            titles += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    if not titles:
        sys.exit("没有要创建的任务")

    due = None
    if args.due:
        dt, all_day = parse_due(args.due)
        due = {"timestamp": str(int(dt.timestamp() * 1000)), "is_all_day": all_day}

    who = args.to or ("open_id " + args.to_open_id if args.to_open_id else "本人")
    print(f"将创建 {len(titles)} 条任务，截止：{args.due or '无'}，负责人：{who}")
    for i, t in enumerate(titles, 1):
        print(f"  {i}. {t}")
    if args.dry_run:
        print("（dry-run，未实际创建）")
        return

    token = get_token()
    if args.to_open_id:
        open_id = args.to_open_id
    elif args.to:
        open_id = find_user(token, args.to)
    else:
        me = request("GET", "/authen/v1/user_info", token=token)
        if me.get("code") != 0:
            sys.exit(f"获取本人信息失败：{json.dumps(me, ensure_ascii=False)}")
        open_id = me["data"]["open_id"]

    failed = 0
    for t in titles:
        body = {
            "summary": t,
            "members": [{"id": open_id, "type": "user", "role": "assignee"}],
        }
        if due:
            body["due"] = due
        r = request("POST", "/task/v2/tasks", body, token=token,
                    params={"user_id_type": "open_id"})
        if r.get("code") == 0:
            print(f"  ✓ {t}  {r['data']['task'].get('url', '')}")
        else:
            failed += 1
            print(f"  ✗ {t}  code={r.get('code')} msg={r.get('msg')}")
    print(f"完成：成功 {len(titles) - failed}，失败 {failed}")
    sys.exit(1 if failed else 0)


def find_chat(token, name):
    r = request("GET", "/im/v1/chats/search", token=token, params={"query": name, "page_size": 50})
    if r.get("code") != 0:
        sys.exit(f"搜索群失败：{json.dumps(r, ensure_ascii=False)}")
    items = r.get("data", {}).get("items", [])
    exact = [c for c in items if c.get("name") == name]
    if len(exact) == 1:
        return exact[0]["chat_id"]
    names = "\n".join(f"  {c.get('name')} {c['chat_id']}" for c in items) or "  （无）"
    sys.exit(f"群「{name}」匹配不唯一，候选：\n{names}")


def cmd_send(args):
    text = args.text or ""
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read().strip()
    if not text:
        sys.exit("消息内容为空")
    if args.at_all:
        text = '<at user_id="all"></at> ' + text
    print(f"发送到群「{args.chat}」（@{'、'.join(args.at) or '无'}）：\n{text}")
    if args.dry_run:
        print("（dry-run，未实际发送）")
        return
    token = get_token()
    if args.at:
        text = "".join(f'<at user_id="{find_user(token, n)}">{n}</at> ' for n in args.at) + "\n" + text
    chat_id = find_chat(token, args.chat)
    r = request("POST", "/im/v1/messages", {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }, token=token, params={"receive_id_type": "chat_id"})
    if r.get("code") != 0:
        sys.exit(f"发送失败：{json.dumps(r, ensure_ascii=False)}")
    print(f"已发送，message_id={r['data']['message_id']}")


def list_my_tasks(token):
    tasks, page = [], None
    while True:
        params = {"type": "my_tasks", "page_size": 100, "user_id_type": "open_id"}
        if page:
            params["page_token"] = page
        r = request("GET", "/task/v2/tasks", token=token, params=params)
        if r.get("code") != 0:
            sys.exit(f"获取任务失败：{json.dumps(r, ensure_ascii=False)}")
        data = r.get("data", {})
        tasks += data.get("items", [])
        if not data.get("has_more"):
            return tasks
        page = data.get("page_token")


def fmt_ms(ms, fmt="%m-%d"):
    return datetime.fromtimestamp(int(ms) / 1000, TZ).strftime(fmt)


def build_report(name, tasks, now):
    """按周报模板（weekly_report_template.md）生成正文。"""
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_start_ms = int(monday.timestamp() * 1000)
    friday = monday + timedelta(days=4)
    now_ms = int(now.timestamp() * 1000)

    done = [t for t in tasks if int(t.get("completed_at") or 0) >= week_start_ms]
    todo = [t for t in tasks if int(t.get("completed_at") or 0) == 0]
    todo.sort(key=lambda t: int((t.get("due") or {}).get("timestamp") or 2**62))

    lines = [f"【周报】{name}  {monday:%m.%d}–{friday:%m.%d}", "", "一、本周任务"]
    lines += [f"✅ {t['summary']}（{fmt_ms(t['completed_at'])} 完成）" for t in done] or ["（本周无已完成任务）"]
    lines += ["", "二、未完成 / 下周计划"]
    for t in todo:
        due = (t.get("due") or {}).get("timestamp")
        if not due:
            mark = "截止：未定"
        elif int(due) < now_ms:
            mark = f"⚠️ 已逾期，原定 {fmt_ms(due)}"
        else:
            mark = f"截止 {fmt_ms(due)}"
        lines.append(f"⏳ {t['summary']}（{mark}）")
    if not todo:
        lines.append("（无未完成任务）")
    return "\n".join(lines)


def cmd_report(args):
    token = get_token()
    me = request("GET", "/authen/v1/user_info", token=token)
    if me.get("code") != 0:
        sys.exit(f"获取本人信息失败：{json.dumps(me, ensure_ascii=False)}")
    text = build_report(me["data"].get("name", ""), list_my_tasks(token), datetime.now(TZ))
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    print(f"\n已写入 {args.out}（可先补充说明，再用 send --file 发出）")


def main():
    p = argparse.ArgumentParser(description="飞书任务批量创建")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("config", help="保存 App ID / App Secret")
    c.add_argument("--app-id", required=True)
    c.add_argument("--app-secret", required=True)
    c.set_defaults(func=cmd_config)

    a = sub.add_parser("auth", help="浏览器授权，获取 user_access_token")
    a.set_defaults(func=cmd_auth)

    d = sub.add_parser("add", help="创建任务（负责人为本人）")
    d.add_argument("titles", nargs="*")
    d.add_argument("--file", help="每行一个任务标题")
    d.add_argument("--due", help="截止时间，如 '2026-11-04 18:00' 或 2026-11-04（全天）")
    d.add_argument("--to", help="负责人姓名（默认本人）")
    d.add_argument("--to-open-id", help="负责人 open_id")
    d.add_argument("--dry-run", action="store_true")
    d.set_defaults(func=cmd_add)

    m = sub.add_parser("send", help="以本人身份发群消息")
    m.add_argument("--chat", required=True, help="群名称")
    m.add_argument("--text")
    m.add_argument("--file", help="消息内容文件")
    m.add_argument("--at-all", action="store_true", help="@所有人")
    m.add_argument("--at", action="append", default=[], help="@指定成员（姓名，可重复）")
    m.add_argument("--dry-run", action="store_true")
    m.set_defaults(func=cmd_send)

    w = sub.add_parser("report", help="按周报模板整理本人任务")
    w.add_argument("--out", default="weekly_report.txt", help="输出文件")
    w.set_defaults(func=cmd_report)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
