'''
Author: 择安网络
Code function: 
Date: 2025-04-27 19:52:25
FilePath: /爬虫仓/新闻/CCTV.py
LastEditTime: 2025-04-29 11:14:55
'''

import aiohttp
import asyncio
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import re
def get_search_results_sync(query, page=1):
    url = f"https://search.cctv.com/search.php"
    params = {
        "qtext": query,
        "type": "web",
        "sort": "relevance",
        "vtime": "",  
        "datepid": "1",
        "channel": "",  
        "page": page
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Referer": "https://news.cctv.com/",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cookie":''
    }
    try:
        response = requests.get(url, params=params, headers=headers)
        response.encoding = 'utf-8'
        return response.text
    except Exception as e:
        print(f"获取第 {page} 页时发生错误: {str(e)}")
        return ""
async def get_search_results(session, query, page=1, semaphore=None):
    url = f"https://search.cctv.com/search.php"
    params = {
        "qtext": query,
        "type": "web",
        "sort": "relevance",
        "vtime": "",  
        "datepid": "1",
        "channel": "",  
        "page": page
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Referer": "https://news.cctv.com/",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    if semaphore:
        async with semaphore:
            await asyncio.sleep(random.uniform(0.5, 1.5))
            try:
                async with session.get(url, params=params, headers=headers) as response:
                    return await response.text()
            except Exception as e:
                print(f"获取第 {page} 页时发生错误: {str(e)}")
                return ""
    else:
        try:
            async with session.get(url, params=params, headers=headers) as response:
                return await response.text()
        except Exception as e:
            print(f"获取第 {page} 页时发生错误: {str(e)}")
            return ""
def parse_search_page(html_content):
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    items = soup.select(".tuwenjg .outer ul li")
    for item in items:
        result = {}
        title_elem = item.select_one("h3.tit a")
        if title_elem:
            result['title'] = title_elem.get_text(strip=True)
            link = title_elem.get('href')
            if 'targetpage=' in link:
                target_url = urllib.parse.unquote(link.split('targetpage=')[1].split('&')[0])
                result['url'] = target_url
            else:
                result['url'] = link
        desc_elem = item.select_one("p.bre")
        if desc_elem:
            result['description'] = desc_elem.get_text(strip=True)
        source_elem = item.select_one("span.src")
        if source_elem:
            result['source'] = source_elem.get_text(strip=True).replace("来源：", "")
        date_elem = item.select_one("span.tim")
        if date_elem:
            result['publish_date'] = date_elem.get_text(strip=True).replace("发布时间：", "")
        img_elem = item.select_one("img")
        if img_elem and 'src' in img_elem.attrs and not img_elem['src'].endswith('timg.gif'):
            result['image_url'] = img_elem['src']
        results.append(result)
    return results
def get_total_pages(html_content):
    if not html_content:
        return 0
    soup = BeautifulSoup(html_content, 'html.parser')
    max_page = 1
    try:
        total_info = soup.select_one(".lmdhd span")
        if total_info:
            total_text = total_info.get_text(strip=True)
            match = re.search(r'共(\d+)条', total_text)
            if match:
                total_count = int(match.group(1))
                print(f"搜索结果总条数: {total_count}")
                estimated_pages = (total_count + 9) // 10
                print(f"根据总条数估算的页数: {estimated_pages}")
                if estimated_pages > max_page:
                    max_page = estimated_pages
    except Exception as e:
        print(f"获取总条数时出错: {str(e)}")
    try:
        page_area = soup.select_one("div.page")
        if page_area:
            page_links = page_area.find_all('a')
            for link in page_links:
                if link.text.isdigit():
                    page_num = int(link.text)
                    if page_num > max_page:
                        max_page = page_num
                elif link.get('href'):
                    href = link.get('href')
                    page_match = re.search(r'page=(\d+)', href)
                    if page_match:
                        page_num = int(page_match.group(1))
                        if page_num > max_page:
                            max_page = page_num
    except Exception as e:
        print(f"从页面链接解析分页信息时出错: {str(e)}")
    try:
        paging_pattern = r'上一页.*?(\d+).*?下一页'
        all_text = soup.get_text()
        pagination_match = re.search(paging_pattern, all_text, re.DOTALL)
        if pagination_match:
            pagination_text = pagination_match.group(0)
            print(f"找到分页文本: {pagination_text}")
            page_numbers = re.findall(r'\d+', pagination_text)
            if page_numbers:
                largest_page = max([int(num) for num in page_numbers if num.isdigit()])
                print(f"从分页文本中提取的最大页码: {largest_page}")
                if largest_page > max_page:
                    max_page = largest_page
    except Exception as e:
        print(f"从文本中提取分页数据时出错: {str(e)}")
    if "page=15" in html_content or ">15<" in html_content:
        if 15 > max_page:
            max_page = 15
            print(f"从HTML内容直接发现页码15")
    if "page=19" in html_content or ">19<" in html_content:
        if 19 > max_page:
            max_page = 19
            print(f"从HTML内容直接发现页码19")
    print(f"最终确定的最大页码数: {max_page}")
    return max_page
def test_page_access(query, test_page=15):
    print(f"测试访问第 {test_page} 页...")
    html_content = get_search_results_sync(query, test_page)
    if not html_content:
        print(f"无法获取第 {test_page} 页内容")
        return False
    soup = BeautifulSoup(html_content, 'html.parser')
    items = soup.select(".tuwenjg .outer ul li")
    if not items:
        print(f"第 {test_page} 页没有找到搜索结果列表")
        return False
    print(f"成功访问第 {test_page} 页，找到 {len(items)} 条结果")
    return True
async def scrape_cctv_search_async(query, max_pages=5, max_concurrent=10):
    all_results = []
    print("正在获取第一页并分析总页数...")
    first_page_html = get_search_results_sync(query, 1)
    total_pages = get_total_pages(first_page_html)
    if total_pages == 0:
        print("无法获取总页数，请检查网络连接或网站结构是否变化")
        return []
    if total_pages > 10:
        can_access_higher_pages = test_page_access(query, 15)
        if not can_access_higher_pages:
            print("警告：无法访问超过10页的内容，将限制爬取范围到10页")
            total_pages = 10
        else:
            print("确认可以访问更高页码，将继续爬取所有页面")
    first_page_results = parse_search_page(first_page_html)
    print(f"第一页获取到 {len(first_page_results)} 条结果")
    all_results.extend(first_page_results)
    pages_to_scrape = min(total_pages, max_pages)
    print(f"将爬取从第 2 页到第 {pages_to_scrape} 页，共 {pages_to_scrape-1} 页")
    semaphore = asyncio.Semaphore(max_concurrent)
    executor = ThreadPoolExecutor(max_workers=max_concurrent)
    pages = list(range(2, pages_to_scrape + 1))
    batch_size = 50
    results_count = len(first_page_results)
    for i in range(0, len(pages), batch_size):
        batch_pages = pages[i:i+batch_size]
        print(f"开始处理第 {i//batch_size + 1} 批，页码 {batch_pages[0]} 到 {batch_pages[-1]}，共 {len(batch_pages)} 页")
        pbar = tqdm(total=len(batch_pages), desc=f"批次 {i//batch_size + 1} 爬取进度")
        connector = aiohttp.TCPConnector(limit_per_host=max_concurrent, force_close=True)
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async def process_page(page):
                try:
                    html_content = await get_search_results(session, query, page, semaphore)
                    loop = asyncio.get_event_loop()
                    results = await loop.run_in_executor(executor, parse_search_page, html_content)
                    pbar.update(1)
                    return page, results
                except Exception as e:
                    print(f"爬取第 {page} 页时出错: {str(e)}")
                    pbar.update(1)
                    return page, []
            tasks = [process_page(page) for page in batch_pages]
            batch_results = await asyncio.gather(*tasks)
            pbar.close()
            successful_pages = 0
            empty_pages = 0
            for page, page_results in batch_results:
                if page_results:
                    all_results.extend(page_results)
                    results_count += len(page_results)
                    successful_pages += 1
                    print(f"第 {page} 页: 获取到 {len(page_results)} 条结果")
                else:
                    empty_pages += 1
            print(f"批次 {i//batch_size + 1} 完成: 成功页数 {successful_pages}, 空页数 {empty_pages}, 当前总结果数: {results_count}")
        if i + batch_size < len(pages):
            sleep_time = random.uniform(3, 5)
            print(f"等待 {sleep_time:.2f} 秒后继续下一批...")
            await asyncio.sleep(sleep_time)
    return all_results
def save_to_csv(results, filename):
    df = pd.DataFrame(results)
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"数据已保存至 {filename}")
async def main():
    search_query = "智慧城市"
    pages_to_scrape = 460
    max_concurrent = 12
    print(f"开始爬取CCTV搜索结果，关键词：{search_query}，计划爬取 {pages_to_scrape} 页")
    start_time = time.time()
    search_results = await scrape_cctv_search_async(search_query, pages_to_scrape, max_concurrent)
    end_time = time.time()
    print(f"共爬取到 {len(search_results)} 条搜索结果")
    print(f"耗时: {end_time - start_time:.2f} 秒")
    if search_results:
        save_to_csv(search_results, f"cctv_{search_query}_results.csv")
        print("爬取完成！")
    else:
        print("未获取到任何结果，请检查网络连接或脚本逻辑")
if __name__ == "__main__":
    asyncio.run(main()) 