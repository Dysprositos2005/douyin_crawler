import requests
import csv
import pandas as pd
from urllib.parse import urlparse
from datetime import datetime
import re

# 用户配置
CSV_PATH = r'C:\Users\18394\Desktop\douyin_crawler\data\地理_search\results_20250630_154315.csv'
with open(r'C:\Users\18394\Desktop\cookie.txt', 'r') as f:
    COOKIE = f.readline().strip()

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Cookie': COOKIE,
    'Referer': 'https://www.douyin.com/'
}


def fetch_user_info_html(sec_user_id):
    """直接访问用户主页 HTML 并解析"""
    url = f'https://www.douyin.com/user/{sec_user_id}'

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        html = resp.text

        # 用正则匹配作品数和获赞数
        aweme_count = re.search(r'"aweme_count":(\d+)', html)
        total_favorited = re.search(r'"total_favorited":(\d+)', html)

        # 主页里一般没有收藏夹数，这里就写未知
        return {
            'address': '未知',
            'age': '未知',
            'aweme_count': aweme_count.group(1) if aweme_count else '未知',
            'total_favorited': total_favorited.group(1) if total_favorited else '未知',
            'favoriting_count': '未知'
        }

    except Exception as e:
        print(f"解析用户主页失败: {str(e)}")
        return {
            'address': '未知',
            'age': '未知',
            'aweme_count': '未知',
            'total_favorited': '未知',
            'favoriting_count': '未知'
        }


def extract_sec_user_id(url):
    """从主页链接提取 sec_user_id"""
    parsed = urlparse(url)
    if parsed.path.startswith('/user/'):
        return parsed.path.split('/user/')[-1]
    return None


if __name__ == "__main__":
    try:
        df = pd.read_csv(CSV_PATH, encoding='utf-8')
        df.columns = df.columns.str.strip().str.replace('\ufeff', '')
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

    all_data = []

    for sec_user_id in sec_user_ids:
        print(f"\n正在采集用户 {sec_user_id}...")

        user_info = fetch_user_info_html(sec_user_id)

        user_record = {
            'user_id': sec_user_id,
            'address': user_info['address'],
            'age': user_info['age'],
            'aweme_count': user_info['aweme_count'],
            'total_favorited': user_info['total_favorited'],
            'favoriting_count': user_info['favoriting_count']
        }
        all_data.append(user_record)

    if all_data:
        with open('douyin_summary.csv', 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = [
                'user_id', 'address', 'age',
                'aweme_count', 'total_favorited', 'favoriting_count'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_data)
        print(f"\n数据采集完成！共获取 {len(all_data)} 条记录，已保存到 douyin_summary.csv")
    else:
        print("\n未获取到任何有效数据")
