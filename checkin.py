import requests
import json
import os
import sys

from pypushdeer import PushDeer

import re

def sc_send(sendkey, title, desp='', options=None):
    if options is None:
        options = {}
    # 判断 sendkey 是否以 'sctp' 开头，并提取数字构造 URL
    if sendkey.startswith('sctp'):
        match = re.match(r'sctp(\d+)t', sendkey)
        if match:
            num = match.group(1)
            url = f'https://{num}.push.ft07.com/send/{sendkey}.send'
        else:
            raise ValueError('Invalid sendkey format for sctp')
    else:
        url = f'https://sctapi.ftqq.com/{sendkey}.send'
    params = {
        'title': title,
        'desp': desp,
        **options
    }
    headers = {
        'Content-Type': 'application/json;charset=utf-8'
    }
    response = requests.post(url, json=params, headers=headers)
    result = response.json()
    return result


# data = {}
# with open(os.path.join(os.path.dirname(__file__), '..', '.env'), 'r') as f:
#     for line in f:
#         key, value = line.strip().split('=')
#         data[key] = value
# key = data['SENDKEY']

# ret = sc_send(key, '主人服务器宕机了 via python', '第一行\n\n第二行')
# print(ret)

# -------------------------------------------------------------------------------------------
# github workflows
# -------------------------------------------------------------------------------------------
if __name__ == '__main__':
    # pushdeer key 申请地址 https://www.pushdeer.com/product.html
    sckey = os.environ.get("SENDKEY", "")

    # 推送内容
    title = ""
    success, fail, repeats = 0, 0, 0        # 成功账号数量 失败账号数量 重复签到账号数量
    context = ""

    # glados账号cookie 直接使用数组 如果使用环境变量需要字符串分割一下
    cookies = os.environ.get("COOKIES", []).split("&")
    if cookies[0] != "":

        check_in_url = "https://glados.cloud/api/user/checkin"        # 签到地址
        status_url = "https://glados.cloud/api/user/status"          # 查看账户状态

        referer = 'https://glados.cloud/console/checkin'
        origin = "https://glados.cloud"
        useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
        payload = {
            'token': 'glados.cloud'
        }
        
        for cookie in cookies:
            cookie = cookie.strip()
            if not cookie:
                continue

            email = ""
            points = 0
            message_days = "error"
            message_status = ""

            try:
                checkin = requests.post(check_in_url, headers={'cookie': cookie, 'referer': referer, 'origin': origin,
                                        'user-agent': useragent, 'content-type': 'application/json;charset=UTF-8'},
                                        data=json.dumps(payload), timeout=30)
                state = requests.get(status_url, headers={
                                    'cookie': cookie, 'referer': referer, 'origin': origin, 'user-agent': useragent},
                                    timeout=30)
            except requests.RequestException as e:
                fail += 1
                message_status = f"网络请求异常: {e}"
                print("[FAIL] " + message_status)
                context += "账号: 未知, P: 0, 剩余: error | " + message_status + " | "
                continue

            # 先校验登录态：cookie 失效时 status 接口返回 {"code":-2,"message":"没有权限"}，但 HTTP 码仍是 200
            try:
                state_result = state.json()
            except ValueError:
                state_result = {}
            state_data = state_result.get('data') or {}
            if not state_data:
                fail += 1
                err = state_result.get('message') or f"HTTP {state.status_code}"
                message_status = f"Cookie 已失效（{err}），请重新登录 glados.cloud 并更新 COOKIES secret"
                print("[FAIL] " + message_status)
                context += "账号: 未知, P: 0, 剩余: error | " + message_status + " | "
                continue

            leftdays = int(float(state_data['leftDays']))
            email = state_data.get('email', "")
            message_days = f"{leftdays} 天"

            if checkin.status_code == 200:
                # 解析返回的json数据
                result = checkin.json()
                # 获取签到结果
                check_result = result.get('message') or ""
                points = result.get('points') or 0

                print(check_result)
                if "Checkin! Got" in check_result:
                    success += 1
                    message_status = "签到成功，会员点数 + " + str(points)
                elif "Checkin Repeats!" in check_result:
                    repeats += 1
                    message_status = "重复签到，明天再来"
                else:
                    fail += 1
                    message_status = f"签到失败，接口返回: {check_result}"
            else:
                fail += 1
                message_status = f"签到请求URL失败, HTTP {checkin.status_code}"

            context += "账号: " + email + ", P: " + str(points) + ", 剩余: " + message_days + " | " + message_status + " | "

        # 推送内容 
        title = f'Glados, 成功{success},失败{fail},重复{repeats}'
        print("Send Content:" + "\n", context)
        
    else:
        # 推送内容 
        title = f'# 未找到 cookies!'

    # 脱敏输出：公开仓库的 Actions 日志任何人可见，不要把 secret 原值打出来
    print("sckey:", "已配置" if sckey else "未配置")
    print("cookies: 共", len([c for c in cookies if c.strip()]), "个账号(已脱敏)")
    
    # 推送消息
    # 未设置 sckey 则不进行推送
    if not sckey:
        print("Not push")
    else:
        ret = sc_send(sckey, title, context)
        # print(ret)
        # pushdeer = PushDeer(pushkey=sckey) 
        # pushdeer.send_text(title, desp=context)

    # 有账号失败（含 cookie 失效）时以非零码退出，让 workflow 标红并触发 GitHub 的失败通知
    if fail > 0:
        sys.exit(1)



