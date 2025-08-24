
from dp_logging import setup_logger
from pathlib import Path
import shutil
import json
from dp_bilibili_api import dp_bilibili, download_file_with_resume
import time

logger = setup_logger(Path(__file__).stem)

# Get the directory where the script is located
SCRIPT_DIR = Path(__file__).parent.resolve()
BASE_DIR = Path('/content').absolute()
F_MP3 = BASE_DIR / "audio.mp3"
F_JSON = F_MP3.with_suffix(".json")
F_SRT = F_MP3.with_suffix(".srt")
F_TEXT = F_MP3.with_suffix(".text")
F_TXT = F_MP3.with_suffix(".txt")

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

def fetch_audio_link_from_json(bv_info):
    dp_blbl = dp_bilibili()
    dl_url = dp_blbl.get_audio_download_url(bv_info['bvid'], bv_info['cid'])
    logger.info(f"视频 {bv_info['title']} 的下载链接: {dl_url}")
    logger.info(f"正在下载 {dl_url} 到 {F_MP3}")
    download_file_with_resume(dp_blbl.session, dl_url, F_MP3)

def main():
    src_file = Path(config.get("bv_list_file", "/content/drive/MyDrive/audio2txt/input.txt"))
    whisper = '/content/drive/MyDrive/Faster-Whisper-XXL/faster-whisper-xxl'

    # 启动时检查文件是否存在。如果不存在，则创建示例文件并退出。
    if not src_file.exists():
        print(f"错误：未找到输入文件 '{src_file}'。")
        return False
    
    while True:
        # 在每次循环开始时，都重新读取文件以获取最新内容
        with open(src_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 寻找第一个有效行进行处理
        line_with_newline = None
        for current_line_obj in lines:
            if current_line_obj.strip() and not current_line_obj.strip().startswith('#'):
                line_with_newline = current_line_obj
                break

        # 如果没有找到有效行，说明所有任务都已处理完毕，退出循环
        if line_with_newline is None:
            break

        line = line_with_newline.strip()

        print("-" * 40)
        print(f"开始处理: {line}")
        try:
            print("--- 开始删除音频文件 ---")
            files_to_delete = [F_MP3, F_JSON]
            for f_path in files_to_delete:
                try:
                    f_path.unlink()
                    print(f"已删除音频文件: {f_path}")
                except FileNotFoundError:
                    pass  # 文件不存在，是正常情况
                except Exception as e:
                    print(f"删除音频文件 {f_path} 时出错: {e}")
            print("--- 删除音频文件完成 ---")
            # 步骤 1: 下载音频
            print(f"正在下载: {line}")
            max_attempts = 10
            delay = 5
            try:
                bv_info = json.loads(line)
                print(f'该行是有效的 JSON 字符串。{bv_info.get("bvid")}, {bv_info.get("cid")}')
                fetch_audio_link_from_json(bv_info)
            except json.JSONDecodeError:
                print("该行不是有效的 JSON 字符串。")
            status, audio_link, audio_json = fetch_audio_link_from_line(line, max_attempts, delay)

        except Exception as e:
            print(f"处理 {line} 时出错: {e}")
            continue
        
        time.sleep(10)

if __name__ == "__main__":
    main()