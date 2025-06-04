'''
Author: 择安网络
Code function: 
Date: 2025-06-04 09:42:11
FilePath: /爬虫仓/google_play/google_play_comments_crawler.py
LastEditTime: 2025-06-04 09:45:31

Description:
    通过playwright爬取google play的评论

    同时支持中文和英文

'''



from playwright.sync_api import Playwright, sync_playwright, expect
import pandas as pd
import os
import time
import re
import urllib.parse

# ===== Configuration Parameters =====
# Target app URL
APP_URL = "your google play app url"
# Total number of comments to collect
TOTAL_COMMENTS = 1500
# Estimated comments per page
COMMENTS_PER_PAGE = 20
# Output directory and filename
OUTPUT_DIR = "output"
OUTPUT_FILE = "lazada_reviews.csv"  # Will be updated with language suffix
# Headless mode (True = browser window not visible)
HEADLESS = True
# Wait time after scrolling (seconds)
SCROLL_WAIT_TIME = 3
# Maximum scroll attempts to prevent infinite scrolling
MAX_SCROLL_ATTEMPTS = 100

LANG_CONFIG = {
    "zh": {
        "output_suffix": "_zh",
        "view_ratings_label": "查看“评分和评价”的更多相关信息",
        "unknown_user": "未知用户",
        "messages": {
            "clicking_expand": "正在点击展开评论按钮...",
            "dialog_opened": "评论弹窗已打开，开始收集评论...",
            "collected_reviews": "已收集 {} 条唯一评论，本次新增 {} 条",
            "target_reached": "已达到目标评论数 {}，停止爬取",
            "no_new_reviews": "本次滚动未发现新评论，尝试继续滚动 (尝试 {}/{})",
            "scrolling": "正在滚动加载更多评论...",
            "scroll_summary": "总共滚动了 {} 次，收集到 {} 条唯一评论",
            "truncated": "截取前 {} 条评论",
            "save_success": "成功收集 {} 条评论，已保存到 {}",
            "no_reviews": "未收集到任何评论",
            "parsing_error": "解析评论时出错: {}",
            "crawler_title": "Google Play 评论爬虫",
            "target_app": "目标应用: {}",
            "target_count": "计划爬取评论数: {}",
            "starting": "开始爬取...",
            "language_detected": "检测到语言: 中文"
        }
    },
    "en": {
        "output_suffix": "_en",
        "view_ratings_label": "See more information on Ratings and reviews",
        "unknown_user": "Unknown User",
        "messages": {
            "clicking_expand": "Clicking to expand reviews...",
            "dialog_opened": "Review dialog opened, starting to collect reviews...",
            "collected_reviews": "Collected {} unique reviews, added {} new reviews",
            "target_reached": "Reached target review count ({}), stopping collection",
            "no_new_reviews": "No new reviews found in this scroll, continuing to scroll (attempt {}/{})",
            "scrolling": "Scrolling to load more reviews...",
            "scroll_summary": "Scrolled {} times, collected {} unique reviews",
            "truncated": "Truncated to {} reviews",
            "save_success": "Successfully collected {} reviews, saved to {}",
            "no_reviews": "No reviews collected",
            "parsing_error": "Error parsing review: {}",
            "crawler_title": "Google Play Review Crawler",
            "target_app": "Target app: {}",
            "target_count": "Target review count: {}",
            "starting": "Starting collection...",
            "language_detected": "Language detected: English"
        }
    }
}


def detect_language():
    """Detect language from APP_URL"""
    parsed_url = urllib.parse.urlparse(APP_URL)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    
    # Default language if 'hl' not in URL
    lang = "en"
    
    if 'hl' in query_params:
        # Get the first value of 'hl' parameter
        lang_param = query_params['hl'][0].lower()
        # Currently we only support 'en' and 'zh'
        if lang_param.startswith('zh'):
            lang = "zh"
        else:
            # Default to English for other languages
            lang = "en"
    
    return lang


def run(playwright: Playwright) -> None:
    # Detect language from URL
    lang = detect_language()
    config = LANG_CONFIG[lang]
    
    # Update output filename with language suffix
    output_filename = OUTPUT_FILE.replace('.csv', f"{config['output_suffix']}.csv")
    
    print(config["messages"]["language_detected"])
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    browser = playwright.chromium.launch(headless=HEADLESS)
    context = browser.new_context()
    page = context.new_page()
    page.goto(APP_URL)
    
    print(config["messages"]["clicking_expand"])
    page.get_by_label(config["view_ratings_label"]).click()
    page.locator(".RHo1pe > .h3YV2d").first.click()
    
    print(config["messages"]["dialog_opened"])
    
    page.wait_for_selector("div.fysCi")
    time.sleep(2)
    
    all_reviews = []
    unique_reviews = []
    
    previous_reviews_count = 0
    scroll_attempts = 0
    scroll_count = 0
    
    seen_reviews = set()
    
    while len(unique_reviews) < TOTAL_COMMENTS and scroll_attempts < MAX_SCROLL_ATTEMPTS:
        current_page_reviews = collect_reviews(page, config)
        new_unique_reviews = 0
        
        for review in current_page_reviews:
            identifier = f"{review['reviewer_name']}:{review['content'][:50]}"
            
            if identifier not in seen_reviews:
                seen_reviews.add(identifier)
                unique_reviews.append(review)
                new_unique_reviews += 1
        
        print(config["messages"]["collected_reviews"].format(len(unique_reviews), new_unique_reviews))
        
        if len(unique_reviews) >= TOTAL_COMMENTS:
            print(config["messages"]["target_reached"].format(TOTAL_COMMENTS))
            break
        
        if new_unique_reviews == 0:
            scroll_attempts += 1
            print(config["messages"]["no_new_reviews"].format(scroll_attempts, MAX_SCROLL_ATTEMPTS))
        else:
            scroll_attempts = 0
        
        print(config["messages"]["scrolling"])
        scroll_count += 1
        
        page.evaluate("document.querySelector('div.fysCi').scrollTo(0, document.querySelector('div.fysCi').scrollHeight)")
        
        time.sleep(SCROLL_WAIT_TIME)
    
    print(config["messages"]["scroll_summary"].format(scroll_count, len(unique_reviews)))
    
    if len(unique_reviews) > TOTAL_COMMENTS:
        unique_reviews = unique_reviews[:TOTAL_COMMENTS]
        print(config["messages"]["truncated"].format(TOTAL_COMMENTS))
    
    if unique_reviews:
        df = pd.DataFrame(unique_reviews)
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(config["messages"]["save_success"].format(len(unique_reviews), output_path))
    else:
        print(config["messages"]["no_reviews"])

    context.close()
    browser.close()


def collect_reviews(page, config):
    """Collect reviews from the current page"""
    reviews = []
    
    review_elements = page.query_selector_all('div.RHo1pe')
    
    for review in review_elements:
        try:
            reviewer_name_element = review.query_selector('div.X5PpBb')
            reviewer_name = reviewer_name_element.text_content() if reviewer_name_element else config["unknown_user"]
            
            date_element = review.query_selector('span.bp9Aid')
            date = date_element.text_content() if date_element else ""
            
            rating_element = review.query_selector('div.iXRFPc')
            rating = ""
            if rating_element:
                rating_label = rating_element.get_attribute('aria-label')
                rating_match = re.search(r'(\d+)', rating_label) if rating_label else None
                rating = rating_match.group(1) if rating_match else "0"
            
            content_element = review.query_selector('div.h3YV2d')
            content = content_element.text_content() if content_element else ""
            
            review_data = {
                'reviewer_name': reviewer_name,
                'date': date,
                'rating': rating,
                'content': content
            }
            
            if content.strip():
                reviews.append(review_data)
                
        except Exception as e:
            print(config["messages"]["parsing_error"].format(e))
    
    return reviews


def main():
    # Detect language from URL
    lang = detect_language()
    config = LANG_CONFIG[lang]
    
    print("=" * 60)
    print(config["messages"]["crawler_title"])
    print(config["messages"]["target_app"].format(APP_URL))
    print(config["messages"]["target_count"].format(TOTAL_COMMENTS))
    print("=" * 60)
    
    print("\n" + config["messages"]["starting"])
    
    with sync_playwright() as playwright:
        run(playwright)


if __name__ == "__main__":
    main()