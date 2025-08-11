#!/bin/bash

# 脚本所在的当前工作目录
SCRIPT_DIR=$(pwd)
# 'io' git 仓库的路径
IO_DIR="$SCRIPT_DIR/queue"

# 定义源和目标目录
AUDIO_TXT_DIR="/content/drive/MyDrive/audio2txt"
IO_OUTPUT_DIR="$IO_DIR/output"

# 循环处理所有输入文件，直到 server_out_queue.sh 找不到新文件（返回非0值）为止
while /content/drive/MyDrive/github/colab_blbl2txt/server_out_queue.sh; do
    echo "---"
    echo "成功获取新输入文件，开始处理..."
    # server_out_queue.sh 成功执行，返回码为 0

    # 转换音频文件
    python3 /content/drive/MyDrive/github/colab_blbl2txt/main.py
done

#已经处理完全部的文件,开始提交
echo "成功处理所有文件,开始提交"
while ! /content/drive/MyDrive/github/colab_blbl2txt/server_in_queue.sh; do
    echo "---"
    echo "提交处理结果失败，等待下一轮..."
    # server_in_queue.sh 执行失败 (返回码非0)，将等待5秒后重试

    # 等待一段时间后继续检查
    sleep 5
done

# 返回原始目录（好习惯）
cd "$SCRIPT_DIR"
echo "--- 输出文件处理完成 ---"

# 清理工作目录，为下一次循环做准备
echo "清理 $AUDIO_TXT_DIR 目录..."
rm -f $AUDIO_TXT_DIR/*

echo "---"
echo "所有任务处理完毕，脚本退出。"
