#!/bin/bash

# 如果任何命令失败，立即退出脚本
set -e

# --- 配置 ---
# 脚本所在的当前工作目录
SCRIPT_DIR=$(pwd)
# 'io' git 仓库的路径
IO_DIR="$SCRIPT_DIR/io"
# 'io' 仓库中存放输入文件的目录
IO_INPUT_DIR="$IO_DIR/input"
# 处理成功后，最终输出文件的路径和名称
TARGET_INPUT_FILE="/content/drive/MyDrive/audio2txt/input.txt"
# --- 配置结束 ---

# 检查 'io' 目录是否存在并且是一个 git 仓库
if [ ! -d "$IO_DIR/.git" ]; then
    echo "错误: 目录 '$IO_DIR' 不是一个有效的 git 仓库。"
    exit 2
fi

# 主循环，持续尝试处理文件，直到成功
while true; do
    echo "--- 开始新一轮文件处理尝试 ---"

    # 1. 进入 'io' 目录并拉取最新更改
    echo "进入目录: $IO_DIR"
    cd "$IO_DIR"
    
    echo "正在拉取远程仓库的最新更改..."
    git fetch --all
    git reset --hard @{u}
    git clean -dfx

    # 2. 寻找一个待处理的文件
    # 返回到脚本主目录，方便处理路径
    cd "$SCRIPT_DIR"
    
    # 使用 find 和 head 命令来安全地获取第一个匹配的文件名
    FILE_TO_PROCESS=$(find "$IO_INPUT_DIR" -type f -name 'investment_videos_*.txt' | head -n 1)

    if [ -z "$FILE_TO_PROCESS" ]; then
        echo "在 '$IO_INPUT_DIR' 目录中未找到需要处理的输入文件。返回1"
        exit 1
    fi

    echo "已选择待处理文件: $FILE_TO_PROCESS"
    FILENAME=$(basename "$FILE_TO_PROCESS")
    # 将文件移动到当前目录作为临时暂存区
    STAGED_FILE_PATH="$SCRIPT_DIR/$FILENAME"

    # 3. 将文件从 git 仓库移出到暂存区
    # 这个“移动”操作（即从仓库中删除文件）是我们将要提交的更改
    mv "$FILE_TO_PROCESS" "$STAGED_FILE_PATH"
    echo "已将 '$FILENAME' 移动到暂存区: $STAGED_FILE_PATH"

    # 4. 提交并推送文件被移除的这个更改
    echo "进入目录: $IO_DIR"
    cd "$IO_DIR"

    echo "正在暂存(stage)文件删除操作..."
    git add "$IO_INPUT_DIR/$FILENAME"
    
    echo "正在提交(commit)..."
    git commit -m "处理并移除输入文件: $FILENAME"

    echo "正在尝试推送(push)更改到远程仓库..."
    if git push; then
        # --- 成功路径 ---
        echo "推送成功。正在完成文件移动。"
        cd "$SCRIPT_DIR"
        mv "$STAGED_FILE_PATH" "$TARGET_INPUT_FILE"
        echo "成功将 '$FILENAME' 移动到 '$TARGET_INPUT_FILE'."
        echo "操作完成。脚本以状态码 0 退出。"
        exit 0 # 按照要求，成功后返回 0
    else
        # --- 失败路径 ---
        echo "推送失败。远程仓库可能已被更新。正在撤销本地更改并重试..."
        git reset --hard HEAD~1
        cd "$SCRIPT_DIR"
        rm "$STAGED_FILE_PATH"
    fi
done