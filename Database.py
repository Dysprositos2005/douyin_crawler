import os
import csv
import asyncio
from datetime import datetime
from pymongo import MongoClient

# ======================
# MongoDB PATH & 配置
mongo_bin_path = r"E:\Program Files\MongoDB\Server\8.0\bin"
os.environ["PATH"] = mongo_bin_path + os.pathsep + os.environ.get("PATH", "")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB", "douyin")
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# ======================
# Selenium 爬虫 + MongoDB 入库
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time


def run_selenium(keyword, scroll_times=10, pause=2):
    options = Options()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver_path = os.path.join(mongo_bin_path, 'chromedriver.exe')
    driver = webdriver.Chrome(service=Service(driver_path), options=options)

    url = f"https://www.douyin.com/search/{keyword}"
    driver.get(url)
    time.sleep(5)
    for _ in range(scroll_times):
        ActionChains(driver).send_keys(Keys.PAGE_DOWN).perform()
        time.sleep(pause)

    # 定位视频卡片
    cards = driver.find_elements(By.CSS_SELECTOR, "div.video-card-selector")  # 替换为真选择器
    results = []
    for card in cards:
        try:
            video_url = card.find_element(By.TAG_NAME, "a").get_attribute("href")
            video_id = card.get_attribute("data-id")  # 或从 URL 提取
            title = card.find_element(By.CSS_SELECTOR, "h3.video-title").text
            author_name = card.find_element(By.CSS_SELECTOR, "p.author-name").text
            author_id = card.find_element(By.CSS_SELECTOR, "p.author-name").get_attribute("data-user-id")
            create_time = datetime.now()  # 若页面提供元素，可替换为具体获取
            tags_elem = card.find_elements(By.CSS_SELECTOR, "span.tag")
            tags = [t.text for t in tags_elem]
            # 以下字段需根据页面结构定位
            digg = int(card.find_element(By.CSS_SELECTOR, "span.digg-count").text)
            comment = int(card.find_element(By.CSS_SELECTOR, "span.comment-count").text)
            play = int(card.find_element(By.CSS_SELECTOR, "span.play-count").text)
            share = int(card.find_element(By.CSS_SELECTOR, "span.share-count").text)
            duration = card.find_element(By.CSS_SELECTOR, "span.duration").text  # 格式 mm:ss
            duration_sec = sum(int(x) * 60 ** i for i, x in enumerate(reversed(duration.split(':'))))

            doc = {
                "video_id": video_id,
                "video_name": title,
                "author_name": author_name,
                "author_id": author_id,
                "create_time": create_time,
                "tags": tags,
                "duration": duration_sec,
                "digg_count": digg,
                "comment_count": comment,
                "play_count": play,
                "share_count": share,
                "video_url": video_url
            }
            results.append(doc)
        except Exception:
            continue
    driver.quit()

    # CSV & MongoDB
    dt = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(f"data/{keyword}_selenium", exist_ok=True)
    csv_path = f"data/{keyword}_selenium/selenium_{dt}.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"Selenium CSV: {csv_path}")

    if results:
        coll = db["user_web_results"]
        coll.insert_many(results)
        print(f"Selenium 写入 MongoDB: {len(results)} 条")

# ======================
# HTTPX 异步 API 爬虫 + MongoDB 入库
def run_httpx(keyword, pages=5):
    import httpx
    import pandas as pd
    from tqdm import tqdm
    from urllib.parse import quote
    import random

    COOKIE_FILE = r"C:\Users\18394\Desktop\cookie.txt"
    SEARCH_URL = "https://www.douyin.com/aweme/v1/web/search/item/"
    TEST_MODE = True

    async def fetch():
        cookie = open(COOKIE_FILE, encoding='utf-8').read().strip()
        results = []
        cursor = 0
        search_id = None
        async with httpx.AsyncClient() as client:
            for _ in tqdm(range(pages), desc="HTTPX 爬取"):
                params = {
                    "device_platform": "webapp",
                    "aid": "6383",
                    "channel": "channel_pc_web",
                    "search_channel": "aweme_video_web",
                    "sort_type": "0",
                    "publish_time": "0",
                    "keyword": keyword,
                    "count": "20",
                    "cursor": cursor,
                }
                if search_id:
                    params["search_id"] = search_id
                headers = {"Cookie": cookie,
                           "Referer": f"https://www.douyin.com/search/{quote(keyword)}",
                           "User-Agent": random.choice(["UA1", "UA2"]) }
                if TEST_MODE:
                    params.update({"X-Bogus":"xxx","_signature":"sig"})
                resp = await client.get(SEARCH_URL, params=params, headers=headers)
                data = resp.json()
                if data.get("status_code") != 0:
                    break
                if not search_id:
                    search_id = data.get("extra", {}).get("logid")
                for item in data.get("data", []):
                    aw = item.get("aweme_info", {})
                    stats = aw.get("statistics", {})
                    tags = [t.get("hashtag_name") for t in aw.get("text_extra",[]) if t.get("type")==1]
                    doc = {
                        "video_id": aw.get("aweme_id"),
                        "video_name": aw.get("desc","")[:100],
                        "author_name": aw.get("author",{}).get("nickname"),
                        "author_id": aw.get("author",{}).get("uid"),
                        "create_time": datetime.fromtimestamp(aw.get("create_time",0)),
                        "tags": tags,
                        "duration": aw.get("duration",0)//1000,
                        "digg_count": stats.get("digg_count"),
                        "comment_count": stats.get("comment_count"),
                        "play_count": stats.get("play_count"),
                        "share_count": stats.get("share_count"),
                        "video_url": aw.get("share_info",{}).get("share_url")
                    }
                    results.append(doc)
                cursor = data.get("cursor",0)
                await asyncio.sleep(random.uniform(2,4))
        return results

    results = asyncio.run(fetch())
    dt = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(f"data/{keyword}_httpx", exist_ok=True)
    csv_path = f"data/{keyword}_httpx/httpx_{dt}.csv"
    pd.DataFrame(results).to_csv(csv_path, index=False, encoding='utf_8_sig')
    print(f"HTTPX CSV: {csv_path}")

    if results:
        coll = db["webapi_results"]
        coll.insert_many(results)
        print(f"HTTPX 写入 MongoDB: {len(results)} 条")


# ======================
if __name__ == "__main__":
    kw = input("关键词：").strip()
    run_selenium(kw)
    run_httpx(kw, pages=int(input("页数：")))
