import subprocess
import requests
import sys

try:
    # 尝试导入 colab 库，如果失败，则说明不在 Colab 环境中
    from google.colab import auth
except ImportError:
    # 打印提示信息并正常退出，而不是抛出异常
    print("未在 Google Colab 环境中运行，跳过获取邮箱的步骤。")
    sys.exit(0)

# --- 后续代码只会在 Colab 环境中执行 ---

try:
    # 1. 进行身份验证，这会弹出一个窗口，要求你授权。
    print("正在进行 Colab 用户身份验证...")
    auth.authenticate_user()

    # 2. 获取 gcloud 访问令牌。
    # 使用 subprocess 模块代替 IPython 的 '!' 魔法命令，以确保脚本在标准 Python 解释器下也能运行。
    print("正在获取 gcloud 访问令牌...")
    command = ['gcloud', 'auth', 'print-access-token']
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    access_token = result.stdout.strip() # .strip() 用于移除末尾的换行符

    # 3. 使用访问令牌调用 Google API 获取用户信息。
    print("正在调用 Google API 获取用户信息...")
    response = requests.get(
        'https://www.googleapis.com/oauth2/v3/tokeninfo?access_token=' + access_token
    )
    response.raise_for_status() # 如果请求失败（如401, 404, 500等），则抛出异常
    token_info = response.json()

    # 4. 打印用户的电子邮件地址，使用 .get() 避免 KeyError
    email = token_info.get('email')
    if email:
        print(f"成功获取到 Colab 用户邮箱: {email}")
    else:
        print("错误：在 API 响应中未找到电子邮件地址。")

except FileNotFoundError:
    print("错误：找不到 'gcloud' 命令。请确保 Google Cloud SDK 已安装并在 Colab 环境的 PATH 中。")
except subprocess.CalledProcessError as e:
    print(f"错误：执行 'gcloud' 命令失败: {e.stderr}")
except requests.exceptions.RequestException as e:
    print(f"错误：网络请求失败: {e}")
except Exception as e:
    print(f"发生未知错误: {e}")