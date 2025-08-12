#!/bin/bash

# 如果任何命令失败，立即退出脚本
set -e

# --- 配置 ---
# 脚本所在的当前工作目录
SCRIPT_DIR=$(pwd)
# 'queue' git 仓库的路径
QUEUE_DIR="/content/drive/MyDrive/github/colab_blbl2txt/queue"
AUDIO2TXT_DIR="/content/drive/MyDrive/audio2txt"
# 'queue' 仓库中存放输出文件的目录
QUEUE_OUTPUT_DIR="$QUEUE_DIR/output"
# --- 配置结束 ---

# 检查 'queue' 目录是否存在并且是一个 git 仓库
if [ ! -d "$QUEUE_DIR/.git" ]; then
    echo "错误: 目录 '$QUEUE_DIR' 不是一个有效的 git 仓库。"
    exit 2
fi

# 主循环，持续尝试处理文件，直到成功
while true; do
    echo "--- 开始新一轮文件处理尝试 ---"

    
    echo "正在重置并同步仓库..."
    cd "$QUEUE_DIR"
    git fetch --all
    git reset --hard origin/$(git rev-parse --abbrev-ref HEAD)
    git pull origin $(git rev-parse --abbrev-ref HEAD)
    echo "仓库已重置并同步。"

    # 2. 寻找一个待处理的文件
    # 返回到脚本主目录，方便处理路径
    cd "$SCRIPT_DIR"

    cp -rf "$AUDIO2TXT_DIR/"* "$QUEUE_OUTPUT_DIR/"
    echo "已将音频转文本结果复制到队列输出目录: $QUEUE_OUTPUT_DIR"

    # 4. 提交并推送文件被移除的这个更改
    echo "进入目录: $QUEUE_DIR"
    cd "$QUEUE_DIR"

    echo "正在暂存(stage)文件..."
    git add .
    
    # 检查是否有任何已暂存的更改。如果没有，则说明没有新文件需要提交。
    # `git diff --staged --quiet` 如果没有更改，则返回0，否则返回1。
    if git diff --staged --quiet; then
        echo "没有需要提交的更改，任务成功完成。"
        exit 0
    fi

    echo "正在提交(commit)..."
    git commit -m "提交音频转文本结果"

    echo "正在尝试推送(push)更改到远程仓库..."
    if git push; then
        # --- 成功路径 ---
        echo "推送成功。"
        exit 0 # 按照要求，成功后返回 0
    else
        # --- 失败路径 ---
        echo "推送失败。远程仓库可能已被更新。重试..."
    fi
done