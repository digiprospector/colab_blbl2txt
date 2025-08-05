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

    # 启动时检查文件是否存在。如果不存在，则创建示例文件并退出。
    if not input_filename.exists():
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

    while True:
        # 在每次循环开始时，都重新读取文件以获取最新内容
        with open(input_filename, 'r', encoding='utf-8') as f:
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
                # 为了防止覆盖在处理期间用户对文件的修改（例如添加了新行），
                # 我们在这里重新读取文件，然后只移除我们刚刚处理完的这一行。
                try:
                    with open(input_filename, 'r', encoding='utf-8') as f:
                        current_lines = f.readlines()

                    # 尝试从最新的文件内容中移除我们刚刚处理的行。
                    # list.remove() 只会移除第一个匹配项，这正是我们想要的。
                    try:
                        current_lines.remove(line_with_newline)
                    except ValueError:
                        # 如果在处理期间，用户已经手动删除了这一行，.remove() 会抛出 ValueError。
                        # 这是正常情况，我们忽略它，但仍然继续执行写入，以保留用户可能添加的其他新行。
                        print(f"提示: 任务 '{line}' 在处理完成前已被从文件中移除。")

                    with open(input_filename, 'w', encoding='utf-8') as f:
                        f.writelines(current_lines)
                    print(f"已成功处理并从 {input_filename.name} 中删除行: {line}")
                except Exception as e:
                    print(f"错误: 更新 {input_filename.name} 时发生错误: {e}")

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
    print("所有待处理行已完成，程序退出。")