---
name: feishu-weekly-report
description: 根据飞书任务自动整理本周周报（本周完成 + 未完成/下周计划），确认后以本人身份发到「森林游戏」飞书群并 @陈刚。用户说「写周报」「整理周报」「发周报」「weekly report」时使用。
---

# 飞书周报

每周五把自己在飞书任务里的进展整理成周报，发到「森林游戏」群并 @陈刚。陈刚每周五会过一遍大家的本周完成和下周计划。

脚本：本 skill 目录下的 `scripts/feishu_task.py`（只用 Python 标准库，需要 Python 3.9+）。下文用 `$S` 指它的绝对路径；不确定在哪就运行 `find ~/.claude/skills ~/.agents/skills -name feishu_task.py 2>/dev/null | head -1`。

## 第 0 步：首次配置（只做一次）

检查 `~/.config/feishu_task/config.json` 和 `~/.config/feishu_task/token.json` 是否存在。

- 和 feishu-task skill 共用同一份配置，任一 skill 配过就不用再配。
- 没有 config.json：向用户要 App ID 和 App Secret（找陈刚私聊要，不要发群里），然后运行
  `python3 $S config --app-id <App ID> --app-secret <App Secret>`
  运行后不要在回复里复述 Secret。
- 没有 token.json，或后面任何命令报「token 已过期」/ 99991679 权限不足：运行 `python3 $S auth`。它会打开浏览器让用户点「授权」，并在 127.0.0.1:8765 等回调，最多等几分钟，让用户去浏览器点授权。
- 授权时如果飞书提示「应用不可用 / 不在可用范围」，告诉用户找陈刚把自己加到 Jacob's claude 应用的可用范围。

## 第 1 步：生成草稿

```
python3 $S report --out /tmp/weekly_report.txt
```

脚本会从飞书任务拉取「我负责的」任务，按模板生成草稿：

```
【周报】姓名  MM.DD–MM.DD

一、本周任务
✅ 任务名（MM-DD 完成）

二、未完成 / 下周计划
⏳ 任务名（截止 MM-DD）
⏳ 任务名（⚠️ 已逾期，原定 MM-DD）
⏳ 任务名（截止：未定）
```

- 一、本周任务 = 本周一 00:00 以后在飞书任务里勾选完成的任务。
- 二、未完成 / 下周计划 = 所有还没完成的任务，按截止时间排序。

## 第 2 步：补充说明

在每条任务后面加「 — 一句话说明」，直接改 `/tmp/weekly_report.txt`：
- ✅ 已完成：写结果或产出。
- ⏳ 未完成：写当前进度、下周计划做到哪一步；有卡点、需要协调的写在这里。
- ⚠️ 逾期：写原因和新的预计完成时间。

不知道的就问用户，可以一次把所有需要说明的任务列出来让用户逐条回答。**不要编造进度。** 用户说某条不用写说明，就只留任务名。

如果用户说某个任务其实已经做完了但忘了勾选，提醒他去飞书任务里勾选完成，然后重新跑第 1 步。

## 第 3 步：确认并发送

把最终全文给用户看，等用户明确确认后再发：

```
python3 $S send --chat 森林游戏 --at 陈刚 --file /tmp/weekly_report.txt
```

输出「已发送，message_id=…」就是成功，告诉用户已发到群里。失败时把报错原文告诉用户，不要反复重试。

## 定时提醒（可选）

用户想每周自动提醒的话，可以帮他建一个每周五 17:00 的定时任务，内容是「用 feishu-weekly-report skill 整理本周周报，补充说明前先问我，确认后再发」。不要设成无人确认就自动发送。
