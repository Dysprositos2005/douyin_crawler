import sys
import io
import asyncio
from datetime import datetime
import os
import httpx
import pandas as pd
from tqdm import tqdm
from urllib.parse import quote
import random

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

COOKIE_FILE = r'C:\Users\18394\Desktop\cookie.txt'
SEARCH_URL = "https://www.douyin.com/aweme/v1/web/search/item/"
TEST_MODE = True  # 测试签名模式（实际项目应用真实签名）


def common(url, params, headers):
    """签名生成函数示例（测试模式用固定签名）"""
    if TEST_MODE:
        signed_params = params.copy()
        signed_params.update({
            "X-Bogus": "DFSzlVuLQxwANSwtliVHXZQrMLbT",
            "_signature": "test_signature"
        })
        return signed_params, headers
    else:
        # 真实签名逻辑（调用签名服务）
        pass


async def safe_fetch(client, url, params, headers):
    try:
        resp = await client.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"\n[请求异常] {type(e).__name__}: {str(e)}")
        return None


async def fetch_search_results(keyword, max_pages):
    cookie = open(COOKIE_FILE, encoding='utf-8').read().strip()

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ]

    async with httpx.AsyncClient() as client:
        results = []
        cursor = 0
        search_id = None
        page_count = 0

        with tqdm(total=max_pages, desc="爬取进度", unit="页") as pbar:
            while page_count < max_pages:
                params = {
                    "device_platform": "webapp",
                    "aid": "6383",
                    "channel": "channel_pc_web",
                    "search_channel": "aweme_video_web",
                    "sort_type": "0",
                    "publish_time": "0",
                    "keyword": keyword,
                    "search_source": "normal_search",
                    "query_correct_type": "1",
                    "is_filter_search": "0",
                    "count": "20",
                    "cursor": cursor,
                }

                if search_id:
                    params["search_id"] = search_id

                headers = {
                    "Cookie": cookie,
                    "Referer": f"https://www.douyin.com/search/{quote(keyword)}?type=video",
                    "User-Agent": random.choice(user_agents),
                }

                signed_params, signed_headers = common(SEARCH_URL, params, headers)

                data = await safe_fetch(client, SEARCH_URL, signed_params, signed_headers)
                if not data or data.get("status_code") != 0:
                    print("\n[提示] 返回空数据，可能到头或被限流。")
                    break

                if page_count == 0:
                    search_id = data.get("extra", {}).get("logid")
                    if not search_id:
                        print("[错误] 无法获取 search_id，可能接口已更新")
                        break

                items = data.get("data", [])
                if not items:
                    print("[提示] 当前页无数据，可能到头。")
                    break

                for item in items:
                    aweme = item.get("aweme_info")
                    if not aweme:
                        continue

                    text_extra = aweme.get("text_extra") or []
                    tags = [t["hashtag_name"] for t in text_extra if t.get("type") == 1]
                    stats = aweme.get("statistics", {})

                    video_id = aweme.get("aweme_id")
                    author_info = aweme.get("author", {})

                    sec_uid = author_info.get("sec_uid", "")
                    homepage_url = f"https://www.douyin.com/user/{sec_uid}" if sec_uid else ""

                    results.append({
                        "video_id": video_id,
                        "desc": aweme.get("desc", "")[:100],
                        "author": author_info.get("nickname"),
                        "author_id": author_info.get("uid"),
                        "author_homepage": homepage_url,
                        "create_time": datetime.fromtimestamp(aweme.get("create_time", 0)),
                        "tags": ", ".join(tags),
                        "digg_count": stats.get("digg_count", 0),
                        "comment_count": stats.get("comment_count", 0),
                        "share_count": stats.get("share_count", 0),
                        "video_url": f"https://www.douyin.com/video/{video_id}" if video_id else ""
                    })

                cursor = data.get("cursor", 0)
                page_count += 1
                pbar.update(1)

                await asyncio.sleep(random.uniform(2, 4))  # 防封

        return results


def save_to_csv(data, keyword):
    if not data:
        print("无有效数据可保存")
        return
    df = pd.DataFrame(data)
    df["create_time"] = pd.to_datetime(df["create_time"])

    save_dir = f"data/{keyword}_search"
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{save_dir}/results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    df.to_csv(filename, index=False, encoding='utf_8_sig')
    print(f"\n✅ 保存成功：{os.path.abspath(filename)} | 共 {len(df)} 条")


async def main():
    keyword = input("请输入搜索关键词：").strip()
    pages = int(input("请输入要爬取的页数："))

    print(f"\n【INFO】开始爬取：关键词={keyword}，页数={pages}")
    results = await fetch_search_results(keyword, pages)
    save_to_csv(results, keyword)


if __name__ == "__main__":
    asyncio.run(main())
