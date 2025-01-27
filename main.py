import re
import os
import yaml
import threading
import base64
import requests
from loguru import logger
from tqdm import tqdm
from retry import retry
from concurrent.futures import ThreadPoolExecutor

from pre_check import pre_check

new_sub_list = []
new_clash_list = []
new_v2_list = []
play_list = []

@logger.catch
def yaml_check(path_yaml):
    if os.path.isfile(path_yaml):
        with open(path_yaml, encoding="UTF-8") as f:
            dict_url = yaml.load(f, Loader=yaml.FullLoader)
    else:
        dict_url = {
            "机场订阅": [],
            "clash订阅": [],
            "v2订阅": [],
            "开心玩耍": []
        }
    logger.info('读取文件成功')
    return dict_url

@logger.catch
def get_config():
    with open('./config.yaml', encoding="UTF-8") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    list_tg = data['tgchannel']
    new_list = []
    for url in list_tg:
        a = url.split("/")[-1]
        url = 'https://t.me/s/' + a
        new_list.append(url)
    return new_list

@logger.catch
def get_channel_http(channel_url):
    try:
        with requests.post(channel_url) as resp:
            data = resp.text
        url_list = re.findall("https?://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]", data)
        logger.info(f"{channel_url}\t获取成功")
    except Exception as e:
        logger.warning(f"{channel_url}\t获取失败")
        logger.error(f"{channel_url}: {str(e)}")
        url_list = []
    return url_list

def filter_base64(text):
    ss = ['ss://', 'ssr://', 'vmess://', 'trojan://']
    for i in ss:
        if i in text:
            return True
    return False

@logger.catch
def check_subscription(url):
    headers = {'User-Agent': 'ClashforWindows/0.18.1'}
    try:
        @retry(tries=2)
        def start_check():
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                try:
                    info = res.headers['subscription-userinfo']
                    info_num = re.findall('\d+', info)
                    if info_num:
                        upload = int(info_num[0])
                        download = int(info_num[1])
                        total = int(info_num[2])
                        unused = (total - upload - download) / 1024 / 1024 / 1024
                        unused_rounded = round(unused, 2)
                        if unused_rounded > 0:
                            new_sub_list.append(url)
                            play_list.append(f'可用流量: {unused_rounded} GB                    {url}')
                except:
                    try:
                        u = re.findall('proxies:', res.text)[0]
                        if u == "proxies:":
                            new_clash_list.append(url)
                    except:
                        try:
                            text = res.text[:64]
                            text = base64.b64decode(text)
                            text = str(text)
                            if filter_base64(text):
                                new_v2_list.append(url)
                        except:
                            pass
        start_check()
    except:
        pass

if __name__ == '__main__':
    path_yaml = pre_check()
    dict_url = yaml_check(path_yaml)
    list_tg = get_config()
    logger.info('读取config成功')

    url_list = []
    for channel_url in list_tg:
        temp_list = get_channel_http(channel_url)
        url_list.extend(temp_list)
    logger.info('开始筛选---')

    bar = tqdm(total=len(url_list), desc='订阅筛选：')
    with ThreadPoolExecutor(max_workers=32) as executor:
        for url in url_list:
            future = executor.submit(check_subscription, url)
            future.add_done_callback(lambda _: bar.update(1))
    bar.close()
    logger.info('筛选完成')

    old_sub_list = dict_url['机场订阅']
    old_clash_list = dict_url['clash订阅']
    old_v2_list = dict_url['v2订阅']
    new_sub_list.extend(old_sub_list)
    new_clash_list.extend(old_clash_list)
    new_v2_list.extend(old_v2_list)
    new_sub_list = list(set(new_sub_list))
    new_clash_list = list(set(new_clash_list))
    new_v2_list = list(set(new_v2_list))
    play_list = list(set(play_list))

    dict_url.update({'机场订阅': new_sub_list})
    dict_url.update({'clash订阅': new_clash_list})
    dict_url.update({'v2订阅': new_v2_list})
    dict_url.update({'开心玩耍': play_list})

    with open(path_yaml, 'w', encoding="utf-8") as f:
        data = yaml.dump(dict_url, f, allow_unicode=True)
