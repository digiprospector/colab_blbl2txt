#!/bin/bash

# 如果任何命令失败，立即退出脚本
set -e

# --- 配置 ---
# 脚本所在的当前工作目录
SCRIPT_DIR=$(pwd)
# 'queue' git 仓库的路径
QUEUE_DIR="/content/drive/MyDrive/github/colab_blbl2txt/queue"
# 'queue' 仓库中存放输入文件的目录
QUEUE_INPUT_DIR="$QUEUE_DIR/input"
# 处理成功后，最终输出文件的路径和名称
TARGET_INPUT_FILE="/content/drive/MyDrive/audio2txt/input.txt"
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
    
    FILE_TO_PROCESS=""
    if [ "$1" == "large" ]; then
        echo "检测到 'large' 参数，优先搜索 'large' 文件。"
        # 优先查找 'large' 文件。-print -quit 比 `| head -n 1` 更高效。
        FILE_TO_PROCESS=$(find "$QUEUE_INPUT_DIR" -type f -name "investment_videos_*large*.txt" -print -quit)
        
        if [ -z "$FILE_TO_PROCESS" ]; then
            echo "未找到 'large' 文件，开始搜索常规文件。"
            # 如果没有 'large' 文件，则查找常规文件
            FILE_TO_PROCESS=$(find "$QUEUE_INPUT_DIR" -type f -name "investment_videos_*.txt" -not -name "*large*" -print -quit)
        fi
    else
        echo "未检测到 'large' 参数，将搜索不包含 'large' 的文件。"
        # 只查找常规文件
        FILE_TO_PROCESS=$(find "$QUEUE_INPUT_DIR" -type f -name "investment_videos_*.txt" -not -name "*large*" -print -quit)
    fi

    if [ -z "$FILE_TO_PROCESS" ]; then
        echo "在 '$QUEUE_INPUT_DIR' 目录中未找到需要处理的输入文件。返回1"
        exit 1
    fi

    echo "已选择待处理文件: $FILE_TO_PROCESS"
    # 如果FILE_TO_PROCESS是空文件,就删除
    if [ ! -s "$FILE_TO_PROCESS" ]; then
        echo "文件 '$FILE_TO_PROCESS' 是空文件，删除..."
        rm "$FILE_TO_PROCESS"
    else
        FILENAME=$(basename "$FILE_TO_PROCESS")
        # 将文件移动到当前目录作为临时暂存区
        STAGED_FILE_PATH="$SCRIPT_DIR/$FILENAME"
        
        # 获取FILE_TO_PROCESS的第一行
        FIRST_LINE=$(head -n 1 "$FILE_TO_PROCESS")
        
        # 将第一行写入STAGED_FILE_PATH
        echo "$FIRST_LINE" > "$STAGED_FILE_PATH"
        
        # 从FILE_TO_PROCESS删除第一行
        sed -i '1d' "$FILE_TO_PROCESS"

        # 如果FILE_TO_PROCESS是空文件,就删除
        if [ ! -s "$FILE_TO_PROCESS" ]; then
            echo "文件 '$FILE_TO_PROCESS' 变为空文件，删除..."
            rm "$FILE_TO_PROCESS"
        fi
    fi

    # 4. 提交并推送文件被移除的这个更改
    echo "进入目录: $QUEUE_DIR"
    cd "$QUEUE_DIR"

    echo "正在暂存(stage)文件删除操作..."
    git add .
    
    echo "正在提交(commit)..."
    git commit -m "处理输入文件: $FILENAME"

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
        echo "推送失败。远程仓库可能已被更新。重试..."
        cd "$SCRIPT_DIR"
        rm "$STAGED_FILE_PATH"
    fi
done