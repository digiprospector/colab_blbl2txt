#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from pathlib import Path
import shutil
import json

from dp_logging import setup_logger
from git_utils import reset_repo, push_changes, set_logger as git_utils_set_logger

logger = setup_logger(Path(__file__).stem)
git_utils_set_logger(logger)

def set_logger(logger_instance):
    global logger
    logger = logger_instance

# --- Configuration ---
# Get the directory where the script is located
SCRIPT_DIR = Path(__file__).parent.resolve()

# Define directories relative to the script's location
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

def out_queue(duration_limit=1800, limit_type="less_than"):
    if limit_type not in ["less_than", "better_greater_than"]:
        logger.error(f"未知的 limit_type: {limit_type}，应为 'less_than' 或 'better_greater_than'")
        return False
    
    queue_dir = get_queue_directory(config)
    bv_list_file = Path(config.get("bv_list_file", "/content/drive/MyDrive/audio2txt/input.txt"))
    
    src_dir = queue_dir / "to_stt"
    
    while True:
        try:
            reset_repo(queue_dir)
            input_files = sorted([f for f in src_dir.glob("*") if not f.name.startswith(".") and f.is_file()])
            if not input_files:
                logger.info(f"{src_dir} 目录中没有待处理的文件，退出")
                break
            found = False
            second_found = False
            if limit_type == "less_than":
                select_line = ""
                select_line_index = 0
                select_file = ""
                # 逐个检查文件中的每一行，寻找时长小于 duration_limit 的任务
                for input_file in input_files:
                    with open(input_file, 'r', encoding='utf-8') as file:
                        lines = file.readlines()
                    for line_index, line in enumerate(lines):
                        line = line.strip()
                        bv_info = json.loads(line)
                        if bv_info["duration"] < duration_limit:
                            select_line = line
                            select_line_index = line_index
                            select_file = input_file
                            found = True
                            break
                    if found:
                        break
            elif limit_type == "better_greater_than":
                select_line = ""
                select_line_index = 0
                select_file = ""
                second_select_line = ""
                second_select_line_index = 0
                second_select_file = ""
                # 逐个检查文件中的每一行，寻找时长大于 duration_limit 的任务
                for input_file in input_files:
                    with open(input_file, 'r', encoding='utf-8') as file:
                        lines = file.readlines()
                    for line_index, line in enumerate(lines):
                        line = line.strip()
                        bv_info = json.loads(line)
                        if bv_info["duration"] > duration_limit:
                            select_line = line
                            select_line_index = line_index
                            select_file = input_file
                            found = True
                            break
                        elif not second_select_line:
                            second_select_line = line
                            second_select_line_index = line_index
                            second_select_file = input_file
                    if found:
                        break
                
                if not found:
                    logger.info(f"没有找到时长大于 {duration_limit} 秒的视频, 找其他的视频")
                    select_line = second_select_line
                    select_line_index = second_select_line_index
                    select_file = second_select_file
                    second_found = True
                    found = True
            else:
                logger.error(f"未知的 limit_type: {limit_type}")
                break
                                
            # 找到了符合条件的行
            if found:
                if limit_type == "less_than":
                    logger.info(f"找到时长小于 {duration_limit} 秒的任务: {select_line}，从 {select_file.name} 中移除该行")
                elif limit_type == "better_greater_than":
                    if second_found:
                        logger.info(f"没有找到时长大于 {duration_limit} 秒的任务, 选择时长小于 {duration_limit} 秒的任务: {select_line}，从 {select_file.name} 中移除该行")
                    else:
                        logger.info(f"找到时长大于 {duration_limit} 秒的任务: {select_line}，从 {select_file.name} 中移除该行")
                with select_file.open('r', encoding='utf-8') as f:
                    lines = f.readlines()
                remaining_lines = lines[:select_line_index] + lines[select_line_index + 1:]
                if not remaining_lines:
                    logger.info(f"文件 {select_file.name} 是空文件，已删除")
                    select_file.unlink()
                else:
                    with select_file.open('w', encoding='utf-8') as f_in:
                        f_in.writelines(remaining_lines)
                with bv_list_file.open('w', encoding='utf-8') as f_dst:
                    logger.info(f"写入 {select_line} 到 {bv_list_file.name}")
                    f_dst.write(select_line + "\n")
                commit_msg = f"处理 {select_file.name} 里的 {select_line}"
            else:
                logger.info(f"没有找到时长小于 {duration_limit} 秒的任务，退出")
                break
            
            id = ""
            if ID_FILE.exists():
                with ID_FILE.open('r', encoding='utf-8') as f_id:
                    id = f"{f_id.read().strip()}, "
            commit_msg = f"{id}处理 {select_file.name} 里的 {select_line}"
            
            push_changes(queue_dir, commit_msg)
            return found
        except Exception as e:
            logger.error(f"发生错误: {e}")
            time.sleep(10)
            logger.info("10秒后重试...")

if __name__ == "__main__":
    if out_queue():
        exit(0)
    else:
        exit(1)