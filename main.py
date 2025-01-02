import os
import yaml
import re
import requests
from loguru import logger
from tqdm import tqdm
from retry import retry

# 仅保留新机场订阅列表
new_sub_list = []

@logger.catch
def yaml_check(path_yaml):
    if os.path.isfile(path_yaml):  # 存在，非第一次
        with open(path_yaml, encoding="UTF-8") as f:
            dict_url = yaml.load(f, Loader=yaml.FullLoader)
    else:
        dict_url = {"机场订阅": []}
    logger.info('读取文件成功')
    return dict_url

@logger.catch
def get_config():
    with open('./config.yaml', encoding="UTF-8") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    list_tg = data['tgchannel']
    new_list = [f'https://t.me/s/{url.split("/")[-1]}' for url in list_tg]
    return new_list

@logger.catch
def get_channel_http(channel_url):
    try:
        response = requests.get(channel_url)  # 修改为GET请求
        data = response.text
        url_list = re.findall(r"https?://[^\s]+", data)  # 使用正则表达式查找订阅链接并创建列表
        logger.info(f'{channel_url}\t获取成功')
    except Exception as e:
        logger.warning(f'{channel_url}\t获取失败: {e}')
        url_list = []
    return url_list

@logger.catch
def sub_check(url, bar):
    headers = {'User-Agent': 'ClashforWindows/0.18.1'}
    try:
        res = requests.get(url, headers=headers, timeout=5)  # 设置5秒超时防止卡死
        if res.status_code == 200:
            # 检查是否为有效的订阅链接
            if "subscription-userinfo" in res.headers or "proxies:" in res.text:
                new_sub_list.append(url)
    except Exception:
        pass  # 忽略网络请求失败的情况
    finally:
        bar.update(1)

if __name__ == '__main__':
    path_yaml = pre_check()
    dict_url = yaml_check(path_yaml)
    list_tg = get_config()
    logger.info('读取config成功')

    # 循环获取频道订阅
    url_list = []
    for channel_url in list_tg:
        temp_list = get_channel_http(channel_url)
        url_list.extend(temp_list)
    logger.info('开始筛选---')

    thread_max_num = threading.Semaphore(32)  # 32线程
    bar = tqdm(total=len(url_list), desc='订阅筛选：')
    thread_list = []
    for url in url_list:
        t = threading.Thread(target=sub_check, args=(url, bar))
        thread_list.append(t)
        t.setDaemon(True)
        t.start()
    for t in thread_list:
        t.join()
    bar.close()
    logger.info('筛选完成')

    old_sub_list = dict_url['机场订阅']
    new_sub_list.extend(old_sub_list)
    new_sub_list = list(set(new_sub_list))

    # 只输出机场订阅的https链接
    for url in new_sub_list:
        if url.startswith("https://"):
            print(url)
