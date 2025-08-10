#!/bin/bash

# 脚本所在的当前工作目录
SCRIPT_DIR=$(pwd)
# 'io' git 仓库的路径
IO_DIR="$SCRIPT_DIR/io"

# 定义源和目标目录
AUDIO_TXT_DIR="/content/drive/MyDrive/audio2txt"
IO_OUTPUT_DIR="$IO_DIR/output"

# 循环处理所有输入文件，直到 get_input.sh 找不到新文件（返回非0值）为止
while /content/drive/MyDrive/github/colab_blbl2txt/get_input.sh; do
    echo "---"
    echo "成功获取新输入文件，开始处理..."
    # get_input.sh 成功执行，返回码为 0

    # 转换音频文件
    python3 /content/drive/MyDrive/github/colab_blbl2txt/main.py

    # 进入 git 仓库目录
    echo "进入目录: $IO_DIR"
    cd "$IO_DIR"
 
    # 使用循环来处理潜在的推送冲突
    while true; do
        echo "正在拉取远程仓库的最新更改..."
        git fetch --all
        git reset --hard @{u}
        git clean -dfx
 
        # --- 新增逻辑：复制并提交输出文件 ---
        echo "--- 开始处理输出文件 ---"
 
        echo "正在从 $AUDIO_TXT_DIR 复制处理结果到 $IO_OUTPUT_DIR"
        # 使用 find 复制文件，排除 input.txt 和 input_*.txt
        # -maxdepth 1 确保我们只查找 AUDIO_TXT_DIR 中的文件，而不是子目录
        # 使用 -exec ... + 提高效率，一次性复制所有找到的文件
        find "$AUDIO_TXT_DIR" -maxdepth 1 -type f ! -name 'input.txt' ! -name 'input_*.txt' -exec cp -t "$IO_OUTPUT_DIR/" {} +
 
        echo "正在将输出文件添加到 git..."
        git add output/
 
        # 检查是否有文件被实际添加（避免空提交）
        if ! git diff --staged --quiet; then
            echo "发现新的输出文件，正在提交..."
            git commit -m "Add processed output files from $(date)"
            echo "正在推送到远程仓库..."
            if git push; then
                echo "推送成功。"
                break # 成功，退出循环
            else
                echo "推送失败。远程仓库可能已被更新。5秒后重试..."
                sleep 5
            fi
        else
            echo "没有新的输出文件需要提交。"
            break # 没有要提交的内容，退出循环
        fi
    done
 
    # 返回原始目录（好习惯）
    cd "$SCRIPT_DIR"
    echo "--- 输出文件处理完成 ---"

    # 清理工作目录，为下一次循环做准备
    echo "清理 $AUDIO_TXT_DIR 目录..."
    rm -f $AUDIO_TXT_DIR/*
done

echo "---"
echo "所有任务处理完毕，脚本退出。"
