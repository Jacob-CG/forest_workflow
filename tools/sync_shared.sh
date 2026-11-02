#!/bin/sh
# 把 shared/ 下的公共脚本同步到用到它的各个 skill（每个 skill 必须自带脚本，npx skills 是按目录安装的）。
# 改完 shared/feishu_task.py 后运行：sh tools/sync_shared.sh
set -e
cd "$(dirname "$0")/.."
for s in feishu-task feishu-weekly-report; do
  mkdir -p "skills/$s/scripts"
  cp shared/feishu_task.py "skills/$s/scripts/feishu_task.py"
done
echo "synced"
