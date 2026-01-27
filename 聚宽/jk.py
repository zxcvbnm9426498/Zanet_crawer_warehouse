'''

需要在根目录创建.env文件,内容如下:
JOINQUANT_USERNAME=你的账号
JOINQUANT_PASSWORD=你的密码

配置环境:pip install requests pillow AntiCAP weworkbot

需要在.env文件中添加（可选）:
WEBHOOK_URL=你的企业微信机器人webhook地址

'''

import requests
import base64
from io import BytesIO
from PIL import Image
import sys
import os
import hashlib
import math
import AntiCAP
from datetime import datetime

try:
    from weworkbot import Bot as wBot
    WEWORK_AVAILABLE = True
except ImportError:
    WEWORK_AVAILABLE = False
    print("Warning: weworkbot not installed, push notifications will be disabled")

headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Origin": "https://www.joinquant.com",
    "Pragma": "no-cache",
    "Referer": "https://www.joinquant.com/view/user/floor?type=mainFloor",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": "\"Google Chrome\";v=\"120\", \"Chromium\";v=\"120\", \"Not?A_Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\""
}

def get_token(session):
    url = "https://www.joinquant.com/user/account/getToken"
    try:
        response = session.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error getting token: {e}")
    return None

def generate_secret(token):
    e = len(token)
    n = e - math.floor(e / 3 * 2)
    r = e - math.floor(e / 3)
    
    scrambled = token[r:] + token[n:r] + token[:n]
    return hashlib.md5(scrambled.encode()).hexdigest()

def get_captcha(session):
    url = "https://www.joinquant.com/common/verifyCode/captchar"

    response = session.post(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get captcha: {response.status_code}")
        return None

def reconstruct_image(captcha_data):
    point = captcha_data['point']
    bg_img_w = captcha_data['bgImgW']
    bg_img_h = captcha_data['bgImgH']
    block_w = captcha_data['blockW']
    block_h = captcha_data['blockH']
    bg_img_b64 = captcha_data['bgImg']

    if ',' in bg_img_b64:
        bg_img_b64 = bg_img_b64.split(',')[1]
    
    bg_img_bytes = base64.b64decode(bg_img_b64)
    source_img = Image.open(BytesIO(bg_img_bytes))
    target_img = Image.new('RGB', (bg_img_w, bg_img_h))
    
    cols = bg_img_w // block_w
    
    for i, item in enumerate(point):
        x_offset = int(item[0])
        y_offset = int(item[1])
        src_x = -x_offset
        src_y = -y_offset
        col = i % cols
        row = i // cols
        dst_x = col * block_w
        dst_y = row * block_h
        box = (src_x, src_y, src_x + block_w, src_y + block_h)
        region = source_img.crop(box)
        target_img.paste(region, (dst_x, dst_y))
        
    img_byte_arr = BytesIO()
    target_img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

def detect_gap(bg_img_bytes, hq_img_b64):
    if ',' in hq_img_b64:
        hq_img_b64 = hq_img_b64.split(',')[1]
        
    bg_img_b64 = base64.b64encode(bg_img_bytes).decode('utf-8')
    
    try:
        Atc = AntiCAP.Handler(show_banner=False)
    except AttributeError:
        from AntiCAP.core import Handler
        Atc = Handler(show_banner=False)

    result = Atc.Slider_Match(target_base64=hq_img_b64, background_base64=bg_img_b64)
    
    if isinstance(result, dict) and 'target' in result:
        bbox = result['target']
        if isinstance(bbox, list) and len(bbox) >= 1:
            return bbox[0]
    elif isinstance(result, dict) and 'x' in result:
         return result['x']
    return None

def validate_captcha(session, token, axis_x):
    url = "https://www.joinquant.com/common/verifyCode/validate"
    data = {
        "token": token,
        "axisX": axis_x
    }
    
    form_headers = headers.copy()
    form_headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    
    response = session.post(url, headers=form_headers, data=data)
    print("Validate response:", response.text)
    return response.json()

def do_login(session, username, password, valide_code):
    url = "https://www.joinquant.com/user/login/doLoginByText"
    data = {
        "username": username,
        "pwd": password,
        "valideCode": valide_code
    }
    
    form_headers = headers.copy()
    form_headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    
    response = session.post(url, headers=form_headers, data=data)
    return response.json()

def check_login(session):
    url = "https://www.joinquant.com/user/index/isLogin"
    response = session.get(url, headers=headers)
    print("Check login response:", response.text)
    return response.json().get('data', {}).get('isLogin') == 1

def get_task_info(session):
    url = "https://www.joinquant.com/credits/task/getTaskInfo"
    response = session.get(url, headers=headers)
    print("Task Info response:", response.text)
    return response.json()

def receive_credits(session, valide_code, app_key, app_secret):
    url = "https://www.joinquant.com/credits/task/receiveCredits"
    data = {
        "appKey": app_key,
        "appSecret": app_secret,
        "ruleKey": "login",
        "valideCode": valide_code
    }
    
    form_headers = headers.copy()
    form_headers["Content-Type"] = "application/x-www-form-urlencoded"
    
    response = session.post(url, headers=form_headers, data=data)
    print("Sign in response:", response.text)
    return response.json()

def send_notification(message, msg_type='text'):
    """发送企业微信通知"""
    webhook_url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=dd087cea-1c56-4902-b919-e1f0aacd4a1f'
    if not webhook_url or not WEWORK_AVAILABLE:
        return
    
    try:
        if msg_type == 'markdown':
            wBot(webhook_url).set_text(message, type='markdown').send()
        else:
            wBot(webhook_url).set_text(message).send()
    except Exception as e:
        print(f"Failed to send notification: {e}")

def solve_and_validate(session):
    print("Fetching captcha...")
    captcha_resp = get_captcha(session)
    if not captcha_resp or captcha_resp.get('code') != '00000':
        print("Error fetching captcha:", captcha_resp)
        return None

    captcha_data = captcha_resp['data']
    token = captcha_data.get('token')
    
    print("Solving captcha...")
    bg_img_bytes = reconstruct_image(captcha_data)
    axis_x = detect_gap(bg_img_bytes, captcha_data['hqImg'])
    print(f"Detected axisX: {axis_x}")
    
    if axis_x is None:
        print("Failed to detect gap")
        return None

    print("Validating captcha...")
    validate_resp = validate_captcha(session, token, axis_x)
    if validate_resp.get('code') != '00000':
        print("Validation failed:", validate_resp)
        return None
        
    valide_code = validate_resp['data']['token']
    print(f"Got valideCode: {valide_code}")
    return valide_code

def main():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = os.getenv("JOINQUANT_USERNAME")
    password = os.getenv("JOINQUANT_PASSWORD")
    
    session = requests.Session()
    
    print("--- Starting Login Process ---")
    valide_code = solve_and_validate(session)
    if not valide_code:
        error_msg = f"聚宽签到失败\n时间: {current_time}\n原因: 验证码识别失败"
        print("Failed to solve captcha for login")
        send_notification(error_msg)
        return

    print("Logging in...")
    login_resp = do_login(session, username, password, valide_code)
    print("Login response:", login_resp)
    
    if login_resp.get('status') == '1':
        error_msg = f"聚宽签到失败\n时间: {current_time}\n原因: 登录失败 - {login_resp.get('msg', '未知错误')}"
        print("Login failed:", login_resp.get('msg'))
        send_notification(error_msg)
        return

    if check_login(session):
        print("Login successful!")
        
        task_info = get_task_info(session)
        if task_info and task_info.get('data') and task_info['data'].get('taskList'):
            login_task = task_info['data']['taskList'].get('login')
            if login_task:
                print(f"Login Task Status: {login_task.get('status')} (1=Done, 0=Not Done)")
                if str(login_task.get('status')) == '1':
                    success_msg = f"聚宽签到提醒\n时间: {current_time}\n状态: 今日已签到"
                    print("Already signed in today!")
                    send_notification(success_msg)
                    return
            else:
                print("Login task not found in task list")
        
        print("\n--- Starting Daily Sign In Process ---")
        
        print("Fetching Token (appKey)...")
        token_resp = get_token(session)
        app_key = None
        app_secret = None
        
        if token_resp and token_resp.get('code') == '00000':
            app_key = token_resp['data']['token']
            print(f"Got appKey: {app_key}")
            app_secret = generate_secret(app_key)
            print(f"Generated appSecret: {app_secret}")
        else:
            error_msg = f"聚宽签到失败\n时间: {current_time}\n原因: 获取Token失败"
            print("Failed to get token")
            send_notification(error_msg)
            return
        
        valide_code_credits = solve_and_validate(session)
        if valide_code_credits:
            print("Signing in (Receive Credits)...")
            credits_resp = receive_credits(session, valide_code_credits, app_key, app_secret)
            if credits_resp and credits_resp.get('code') == '00000':
                success_msg = f"聚宽签到成功\n时间: {current_time}\n状态: 签到完成"
                print("Sign in successful!")
                send_notification(success_msg)
            else:
                error_msg = f"聚宽签到失败\n时间: {current_time}\n原因: 签到请求失败 - {credits_resp.get('msg', '未知错误') if credits_resp else '无响应'}"
                print("Sign in failed:", credits_resp)
                send_notification(error_msg)
        else:
            error_msg = f"聚宽签到失败\n时间: {current_time}\n原因: 签到验证码识别失败"
            print("Failed to solve captcha for credits")
            send_notification(error_msg)

    else:
        error_msg = f"聚宽签到失败\n时间: {current_time}\n原因: 登录验证失败"
        print("Login check failed.")
        send_notification(error_msg)

if __name__ == '__main__':
    main()
