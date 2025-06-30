import requests
import csv
import re
import time
import pandas as pd
from urllib.parse import urlparse
from datetime import datetime

# 用户配置区
CSV_PATH = r'C:\Users\18394\Desktop\douyin_crawler\data\地理_search\results_20250630_154315.csv'  # 修改为你的 CSV 文件路径
with open(r'C:\Users\18394\Desktop\cookie.txt', 'r') as f:
    COOKIE = f.readline().strip()

# 请求头配置
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Cookie': COOKIE,
    'Referer': 'https://www.douyin.com/'
}


def fetch_user_info(sec_user_id):
    """获取用户详细信息（新增函数）"""
    url = 'https://www.douyin.com/aweme/v1/web/user/profile/'
    params = {
        'sec_user_id': sec_user_id,
        'device_platform': 'webapp',
        'aid': 6383,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        user_info = data.get('user', {})
        ip_location = user_info.get('ip_location', '未知') or '未知'
        birthday = user_info.get('birthday')
        age = calculate_age(birthday) if birthday else '未知'

        return {
            'address': ip_location,
            'age': age
        }
    except Exception as e:
        print(f"获取用户信息失败: {str(e)}")
        return {'address': '未知', 'age': '未知'}


def calculate_age(birthday):
    """根据生日计算年龄（新增函数）"""
    try:
        if isinstance(birthday, int):
            birth_year = datetime.fromtimestamp(birthday).year
        else:
            birth_year = int(birthday.split('-')[0])
        current_year = datetime.now().year
        return max(current_year - birth_year, 0)
    except:
        return '未知'


def fetch_data(url, params, data_type, max_count=3):
    """通用数据获取函数"""
    data_list = []
    max_cursor = 0
    retry = 0
    while retry < 3:
        try:
            params['max_cursor'] = max_cursor
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data.get('aweme_list'):
                break

            for item in data['aweme_list']:
                if len(data_list) >= max_count:
                    break

                desc = item.get('desc', '')
                tags = re.findall(r'#([^#\s]+)', desc)
                stats = item.get('statistics', {})

                data_list.append({
                    'type': data_type,
                    'video_id': item.get('aweme_id'),
                    'desc': desc,
                    'tags': ','.join(tags),
                    'like_count': stats.get('digg_count', 0),
                    'collect_count': stats.get('collect_count', 0),
                    'time': item.get('create_time', '')
                })

            if len(data_list) >= max_count:
                break

            if not data.get('has_more', 0):
                break

            max_cursor = data.get('max_cursor', max_cursor)
            time.sleep(1.5)
            retry = 0
        except Exception as e:
            print(f"请求异常: {str(e)}，重试 {retry + 1}/3")
            retry += 1
            time.sleep(2)
    return data_list[:max_count]


def extract_sec_user_id(url):
    """从主页链接提取sec_user_id"""
    parsed = urlparse(url)
    if parsed.path.startswith('/user/'):
        return parsed.path.split('/user/')[-1]
    return None


# 主程序
if __name__ == "__main__":
    try:
        df = pd.read_csv(CSV_PATH, encoding='utf-8')
        urls = df['author_homepage'].tolist()
    except Exception as e:
        print(f"读取CSV文件失败: {str(e)}")
        exit()

    sec_user_ids = []
    for url in urls:
        if not pd.isna(url):
            user_id = extract_sec_user_id(url)
            if user_id:
                sec_user_ids.append(user_id)
            else:
                print(f"无效链接格式: {url}")

    common_params = {
        'count': 20,
        'device_platform': 'webapp',
        'aid': 6383,
        'version_code': '190500'
    }

    all_data = []

    for sec_user_id in sec_user_ids:
        print(f"\n正在采集用户 {sec_user_id}...")

        user_info = fetch_user_info(sec_user_id)

        post_data = fetch_data(
            'https://www.douyin.com/aweme/v1/web/aweme/post/',
            {**common_params, 'sec_user_id': sec_user_id},
            '作品'
        )
        for item in post_data:
            item.update({
                'user_id': sec_user_id,
                'address': user_info['address'],
                'age': user_info['age']
            })
        all_data.extend(post_data)

        fav_data = fetch_data(
            'https://www.douyin.com/aweme/v1/web/aweme/favorite/',
            {**common_params, 'sec_user_id': sec_user_id},
            '点赞'
        )
        for item in fav_data:
            item.update({
                'user_id': sec_user_id,
                'address': user_info['address'],
                'age': user_info['age']
            })
        all_data.extend(fav_data)

    if all_data:
        with open('douyin_data.csv', 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = [
                'user_id', 'type', 'video_id', 'desc', 'tags',
                'like_count', 'collect_count', 'time',
                'address', 'age'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_data)
        print(f"\n数据采集完成！共获取 {len(all_data)} 条记录，已保存到 douyin_data.csv")
    else:
        print("\n未获取到任何有效数据")
