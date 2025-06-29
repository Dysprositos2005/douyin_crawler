import time
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ======================
# 可调参数
SCROLL_TIMES = 10
SCROLL_PAUSE = 2

# ======================
# 启动 Chrome
options = Options()
options.add_argument("--start-maximized")
# options.add_argument("--headless")  # 如果需要无头模式就取消注释
options.add_argument("--disable-blink-features=AutomationControlled")

# 替换为你的 ChromeDriver 路径
driver_path = r"C:\Users\18394\.cache\selenium\chromedriver\win64\134.0.6998.88\chromedriver.exe"
driver = webdriver.Chrome(service=Service(driver_path), options=options)

# ======================
# 输入关键词
keyword = input("请输入搜索关键词：")
search_url = f"https://www.douyin.com/search/{keyword}"
driver.get(search_url)

wait = WebDriverWait(driver, 15)

# ======================
# 等页面加载
print(f"👉 打开搜索页：{search_url}")
time.sleep(5)

# ======================
# 模拟多次下滑
for i in range(SCROLL_TIMES):
    print(f"👉 正在滑动第 {i + 1} 次...")
    ActionChains(driver).send_keys(Keys.PAGE_DOWN).perform()
    time.sleep(SCROLL_PAUSE)

print(f"【INFO】开始提取搜索结果...")

# ======================
# 自己对照抖音网页检查选择器！
# 下面示例选择器是演示，请替换为真实类名！
# 例如：抖音搜索视频卡片外层 div 的 class
card_selector = "div.xgplayer"   # <<< 替换为真实类名

cards = driver.find_elements(By.CSS_SELECTOR, card_selector)
print(f"共找到卡片数：{len(cards)}")

results = []

for idx, card in enumerate(cards, 1):
    try:
        # 自己对照抖音页面修改选择器
        # 假设外层是 div.xgplayer, 内部视频链接是 <a>，作者是 <span> 或 <p>
        link_element = card.find_element(By.TAG_NAME, "a")
        link = link_element.get_attribute("href")
        
        # 假设标题在卡片 text 中第 1 行
        title = card.text.split("\n")[0]
        
        author = ""
        try:
            author_element = card.find_element(By.CSS_SELECTOR, "p.author-name")  # 替换
            author = author_element.text
        except:
            pass

        print(f"[{idx}] {title} | {author} | {link}")
        results.append({
            "title": title,
            "author": author,
            "link": link
        })
    except Exception as e:
        print(f"[跳过] 报错：{e}")
        continue

# ======================
# 保存 CSV
if not results:
    print("❌ 没有提取到任何结果，请检查选择器是否正确！")
else:
    dt = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = f"./data/{keyword}_selenium"
    save_path = f"{save_dir}/results_{dt}.csv"

    import os
    os.makedirs(save_dir, exist_ok=True)

    with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "author", "link"])
        writer.writeheader()
        writer.writerows(results)

    print(f"✅ 已保存到：{save_path} | 共 {len(results)} 条")

# 关闭浏览器
driver.quit()
