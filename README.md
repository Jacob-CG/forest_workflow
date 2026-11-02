# forest_workflow

森林工作流的 Claude skills。大家用同一套 skills，工作流就统一了。由陈刚维护，其他人只读；有想加的 skill 或改进，直接在群里提。

## 有哪些 skill

| skill | 做什么 | 怎么用 |
|---|---|---|
| `feishu-task` | 以本人身份建飞书任务（给自己或指派同事）、看自己的任务、发群消息 | 对 Claude 说「把这几件事建成飞书任务，周五前」 |
| `feishu-weekly-report` | 从飞书任务整理周报（本周完成 + 未完成/下周计划），确认后发到「森林游戏」群并 @陈刚 | 每周五对 Claude 说「写周报」 |

## 安装

需要 Node.js（用来跑 `npx`）和 Python 3.9+。

```bash
npx skills add Jacob-CG/forest_workflow -g -a claude-code -s '*' -y
```

装完重启 Claude Code（或新开会话）。

## 更新

陈刚更新仓库后，在群里通知，大家运行：

```bash
npx skills update -g -y
```

## 首次配置

第一次用任一飞书 skill 时，Claude 会：
1. 向你要 App ID 和 App Secret（私聊陈刚要，不要发群里）；
2. 打开浏览器让你点一次「授权」。

配置存在 `~/.config/feishu_task/`，两个 skill 共用，只需配一次。

## 维护（陈刚）

- 新 skill：在 `skills/<名字>/SKILL.md` 里写，frontmatter 要有 `name` 和 `description`。
- 公共脚本 `shared/feishu_task.py` 改完后运行 `sh tools/sync_shared.sh`，把它同步到各 skill 的 `scripts/` 再提交（`npx skills` 按目录安装，每个 skill 要自带脚本）。
- 推送后在群里通知大家 `npx skills update -g -y`。
