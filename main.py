import sys
import os
import subprocess
from blbldl.blbldl import fetch_audio_link_from_line, download_audio_and_create_json
import json
from datetime import datetime # Import datetime
from pathlib import Path
import shutil
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="下载B站视频的音频")
    parser.add_argument("-m", "--max-duration", type=int, default=0, help="最大下载时长（秒）")
    args = parser.parse_args()

    audio2txt_dir = '/content/drive/MyDrive/audio2txt'
    input_filename = Path(audio2txt_dir) / 'input.txt'
    whisper = '/content/drive/MyDrive/Faster-Whisper-XXL/faster-whisper-xxl'
    pwd = '/content'
    f_mp3 = Path(pwd) / "audio.mp3"
    f_json = f_mp3.with_suffix(".json")
    f_srt = f_mp3.with_suffix(".srt")
    f_text = f_mp3.with_suffix(".text")
    f_txt = f_mp3.with_suffix(".txt")

    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"错误：未找到输入文件 '{input_filename}'。")
        print(f"已为您创建一个示例 '{input_filename}' 文件。")
        with open(input_filename, 'w', encoding='utf-8') as f:
            f.write("# 请在此文件中每行输入一个 Bilibili 视频链接或完整的 blbldl 命令。\n")
            f.write("# 以 '#' 开头的行将被忽略。\n")
            f.write("# 示例链接：\n")
            f.write("# https://www.bilibili.com/video/BV1GJ411x7h7\n")
            f.write("# 示例带参数命令：\n")
            f.write("# -c SESSDATA=... https://www.bilibili.com/video/BV1GJ411x7h7\n")
        sys.exit(f"请向 '{input_filename}' 添加内容后重新运行。")

    # 我们遍历行列表的副本，因为在成功处理后，我们会从原始的 'lines' 列表中移除该行。
    for line_with_newline in lines[:]:
        line = line_with_newline.strip()
        if not line or line.startswith('#'):
            continue

        print("-" * 40)
        print(f"开始处理: {line}")

        try:
            print("--- 开始删除音频文件 ---")
            files_to_delete = [f_mp3, f_json]
            for f_path in files_to_delete:
                try:
                    os.remove(f_path)
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
            status, audio_link, audio_json = fetch_audio_link_from_line(line, max_attempts, delay)
            if status == 'excluded':
                print(f"充电专属,已跳过视频: {line}")
            elif status == 'failed':
                print(f"下载视频失败: {line}")
            elif status == 'error':
                print(f"下载视频错误: {line}")
            else:
                if args.max_duration and audio_json.get('duration') > args.max_duration:
                    print(f"{line} 视频长度超过 {args.max_duration}秒, 跳过视频")
                    status = 'toolong'
                else:
                    status = download_audio_and_create_json(audio_link, audio_json, f_mp3)
                    if status == 'ok':
                        print("--- 开始删除文本文件 ---")
                        files_to_delete = [f_srt, f_text, f_txt]
                        for f_path in files_to_delete:
                            try:
                                os.remove(f_path)
                                print(f"已删除文本文件: {f_path}")
                            except FileNotFoundError:
                                pass  # 文件不存在，是正常情况
                            except Exception as e:
                                print(f"删除文本文件 {f_path} 时出错: {e}")
                        print("--- 删除文本文件完成 ---")

                        # 步骤 2: 调用 faster-whisper-xxl 处理音频
                        if os.path.exists(f_mp3):
                            print(f"--- 开始使用 faster-whisper-xxl 转录音频 ---")
                            whisper_command = [
                                whisper,
                                f_mp3,
                                '-m', 'large-v2',
                                '-l', 'Chinese',
                                '--vad_method', 'pyannote_v3',
                                '--ff_vocal_extract', 'mdx_kim2',
                                '--sentence',
                                '-v', 'true',
                                '-o', 'source',
                                '-f', 'txt', 'srt', 'text'
                            ]
                            subprocess.run(whisper_command, check=True)
                            print("--- 音频转录完成 ---")
                        else:
                            print(f"警告: 未找到音频文件 '{f_mp3}'，跳过转录步骤。")

                        with open(f_json, "r", encoding='utf-8') as f:
                            j = json.load(f)
                            title = j.get('title', 'Untitled')
                            # 替换在Windows和Linux文件名中不合法的字符
                            invalid_chars = '<>:"/\\|?*'
                            sanitized_title = title.translate(str.maketrans(invalid_chars, '_' * len(invalid_chars)))[0:50]
                            fn = f"[{datetime.fromtimestamp(j.get('datetime')).strftime('%Y-%m-%d_%H-%M-%S')}][{j.get('owner')}][{sanitized_title}][{j.get('bvid')}]"
                            shutil.copy(f_srt, Path(audio2txt_dir) / f"{fn}.srt")
                            shutil.copy(f_txt, Path(audio2txt_dir) / f"{fn}.txt")
                            shutil.copy(f_text, Path(audio2txt_dir) / f"{fn}.text")
                            print(f"--- 复制文件{fn}完成 ---")

            # status in 'ok', 'failed', 'toolong', 'excluded', 'error'
            if status != 'failed':
                # 处理成功，从列表中删除该行并重写输入文件
                lines.remove(line_with_newline)
                with open(input_filename, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"已成功处理并从 {input_filename.name} 中删除行: {line}")

            post_input_path = None
            if status == 'ok':
                post_input_path = input_filename.parent / 'input_finish.txt'
            elif status == 'toolong':
                post_input_path = input_filename.parent / 'input_long.txt'
            elif status == 'excluded':
                post_input_path = input_filename.parent / 'input_epower.txt'
            elif status == 'error':
                post_input_path = input_filename.parent / 'input_error.txt'

            if post_input_path:
                with open(post_input_path, 'a', encoding='utf-8') as f:
                    f.write(line + '\n')
                
        except Exception as e:
            print(f"处理 '{line}' 期间发生严重错误: {e}")
        finally:
            # 步骤 3: 清理本次循环产生的临时文件，为下一次做准备
            print("--- 执行循环后清理 ---")
            for f_path in files_to_delete:
                if os.path.exists(f_path):
                    try:
                        os.remove(f_path)
                        print(f"已删除临时文件: {f_path}")
                    except Exception as e:
                        print(f"删除文件 {f_path} 时出错: {e}")

    print("-" * 40)
    print("所有行处理完毕。")