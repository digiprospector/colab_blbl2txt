#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from pathlib import Path
import shutil
import git
from git.exc import GitCommandError
import argparse

from dp_logging import setup_logger
from git_utils import reset_repo, push_changes, set_logger as git_utils_set_logger

logger = setup_logger(Path(__file__).stem)
git_utils_set_logger(logger)

# --- Configuration ---
# Get the directory where the script is located
SCRIPT_DIR = Path(__file__).parent.resolve()

# Define directories relative to the script's location
LIST_DIR = SCRIPT_DIR / "list"
ID_FILE= SCRIPT_DIR / "id"

def get_config():
    """Get the queue directory from the config file."""
    config_file = SCRIPT_DIR / "config.json"
    if not config_file.exists():
        logger.error(f"配置文件 {config_file} 不存在。")
        shutil.copy(SCRIPT_DIR / "config_sample.json", config_file)
        logger.info(f"已将 config_sample.json 复制到 {config_file}")

    import json
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    return config
config = get_config()

def get_queue_directory(config):
    queue_path = Path(config.get("queue_directory", "queue"))

    if queue_path.is_absolute():
        # 如果是绝对路径，直接使用
        return queue_path
    else:
        # 如果是相对路径，则解析为相对于脚本目录的绝对路径
        return (SCRIPT_DIR / queue_path).resolve()

def out_queue():
    queue_dir = get_queue_directory(config)
    dst_file = Path(config.get("dst_file", "/content/drive/MyDrive/audio2txt/input.txt"))
    
    src_dir = queue_dir / "to_stt"
    output_to_input_txt = False
    
    while True:
            reset_repo(queue_dir)
            input_files = sorted([f for f in src_dir.glob("*") if not f.name.startswith(".") and f.is_file()])
            if not input_files:
                logger.info(f"{src_dir} 目录中没有待处理的文件，退出")
                break
            input_file = input_files[0]
            input_path = input_file.resolve()
            if input_file.stat().st_size == 0:
                logger.info(f"文件 {input_path} 是空文件，已删除")
                input_file.unlink()
            else:
                output_to_input_txt = True
                with input_file.open('r', encoding='utf-8') as f:
                    lines = f.readlines()
                if lines:
                    first_line = lines[0]
                    remaining_lines = lines[1:]
                    with dst_file.open('w', encoding='utf-8') as f_dst:
                        f_dst.write(first_line)
                    with input_file.open('w', encoding='utf-8') as f_in:
                        f_in.writelines(remaining_lines)
                else:
                    logger.info(f"文件 {input_path} 没有内容，已跳过")
                    return
            
            id = ""
            if ID_FILE.exists():
                with ID_FILE.open('r', encoding='utf-8') as f_id:
                    id = f"{f_id.read().strip()}, "
            if output_to_input_txt:
                commit_msg = f"{id}处理 {input_path.name} 里的 {first_line}"
            else:
                commit_msg = f"{id}删除孔文件 {input_path.name}"
            
            push_changes(queue_dir, commit_msg)
            break

if __name__ == "__main__":
    out_queue()