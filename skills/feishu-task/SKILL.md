---
name: feishu-task
description: 以本人身份在飞书任务里创建任务（给自己或指派给同事，可设截止时间）、查看自己的任务、以本人身份发飞书群消息。用户说「建个飞书任务」「把这些记到飞书任务」「给某某派个任务」「看看我的任务」「在群里发个消息」时使用。
---

# 飞书任务

团队的待办统一记在飞书任务里（周报也以飞书任务为准，见 feishu-weekly-report skill）。

脚本：本 skill 目录下的 `scripts/feishu_task.py`（只用 Python 标准库，需要 Python 3.9+）。下文用 `$S` 指它的绝对路径；不确定在哪就运行 `find ~/.claude/skills ~/.agents/skills -name feishu_task.py 2>/dev/null | head -1`。

## 首次配置（只做一次，和周报 skill 共用）

检查 `~/.config/feishu_task/config.json` 和 `~/.config/feishu_task/token.json` 是否存在。

- 没有 config.json：向用户要 App ID 和 App Secret（私聊陈刚要，不要发群里），运行
  `python3 $S config --app-id <App ID> --app-secret <App Secret>`，之后不要在回复里复述 Secret。
- 没有 token.json，或命令报「token 已过期」/ 99991679 权限不足：运行 `python3 $S auth`，让用户在弹出的浏览器里点「授权」。
- 飞书提示「应用不可用 / 不在可用范围」：让用户找陈刚把自己加入 Jacob's claude 应用的可用范围。

## 创建任务

先 `--dry-run` 给用户看一遍要建的任务，确认后去掉 `--dry-run` 正式创建。

```
# 给自己建，一个或多个标题
python3 $S add --due "2026-11-07 18:00" "任务1" "任务2" --dry-run

# 从文件批量建（每行一个标题，# 开头的行忽略）
python3 $S add --due 2026-11-07 --file tasks.txt --dry-run

# 指派给同事（按姓名搜索，重名时会列出 open_id，再用 --to-open-id 指定）
python3 $S add --to 王迪 "任务标题" --dry-run
```

- `--due` 支持 `YYYY-MM-DD HH:MM` 或 `YYYY-MM-DD`（全天）；不给就是无截止时间。用户说「周五前」这类相对时间时，先换算成具体日期再跟用户确认。
- 任务标题要具体、可验收，一条任务一件事。用户口述一大段时，帮他拆成几条再确认。

## 查看我的任务

```
python3 $S report --out /tmp/my_tasks.txt
```

输出本周已完成的任务和所有未完成的任务（按截止时间排，逾期标 ⚠️）。

## 以本人身份发群消息

```
python3 $S send --chat 群名 --text "内容" --dry-run
python3 $S send --chat 群名 --file msg.txt [--at 姓名] [--at-all]
```

发群消息前必须把全文给用户确认；`--at-all` 只在用户明确要求时使用。
