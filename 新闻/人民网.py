'''
Author: 择安网络
Code function: 
Date: 2025-04-29 09:30:02
FilePath: /新闻网爬虫/人民网.py
LastEditTime: 2025-04-29 11:08:51

Log:
- 增加异步多线程
- 增加对时间、并发数、页数、关键词的限制
- 增加对正文的提取
- 增加对正文的异步

'''

import requests
import json
import csv
import time
from datetime import datetime
import argparse
import asyncio
import aiohttp
import threading
from queue import Queue
import os
from bs4 import BeautifulSoup
import concurrent.futures
class CSVWriter:
    def __init__(self, filename, fieldnames):
        self.filename = filename
        self.fieldnames = fieldnames
        self.file = open(filename, 'w', encoding='utf-8-sig', newline='')
        self.writer = csv.DictWriter(self.file, fieldnames=fieldnames)
        self.writer.writeheader()
        self.lock = threading.Lock()
        self.record_count = 0
    def write_row(self, row):
        with self.lock:
            self.writer.writerow(row)
            self.record_count += 1
            if self.record_count % 500 == 0:
                self.file.flush()
                print(f"已写入 {self.record_count} 条记录到CSV文件")
    def close(self):
        with self.lock:
            self.file.flush()  
            self.file.close()
            print(f"CSV文件已关闭，共写入 {self.record_count} 条记录")
def convert_date_to_timestamp(date_str):
    if not date_str:
        return 0
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        timestamp = int(dt.timestamp() * 1000)
        print(f"日期 {date_str} 转换为时间戳: {timestamp}")
        return timestamp
    except ValueError:
        print(f"日期格式错误: {date_str}，应为YYYY-MM-DD格式")
        return 0
def search_people_cn(keyword, page=1, limit=10, start_date=None, end_date=None):
    url = "http://search.people.cn/search-platform/front/search"
    start_time = convert_date_to_timestamp(start_date)
    end_time = convert_date_to_timestamp(end_date)
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/json;charset=UTF-8",
        "Host": "search.people.cn",
        "Origin": "http://search.people.cn",
        "Pragma": "no-cache",
        "Referer": "http://search.people.cn/s?keyword=%E9%A3%9F%E7%89%A9%E4%B8%AD%E6%AF%92&st=0&_=1745890163341",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    }
    payload = {
        "endTime": end_time,
        "hasContent": True,
        "hasTitle": True,
        "isFuzzy": True,
        "key": keyword,
        "limit": limit,
        "page": page,
        "sortType": 2,
        "startTime": start_time,
        "type": 0
    }
    if page == 1:
        print(f"请求参数: {json.dumps(payload, ensure_ascii=False)}")
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        return response.json()
    else:
        print(f"请求失败，状态码: {response.status_code}")
        return None
async def async_search_people_cn(session, keyword, page=1, limit=10, start_date=None, end_date=None):
    url = "http://search.people.cn/search-platform/front/search"
    start_time = convert_date_to_timestamp(start_date) if page == 1 else 0  
    end_time = convert_date_to_timestamp(end_date) if page == 1 else 0
    if page != 1:  
        if start_date:
            start_time = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
        if end_date:
            end_time = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/json;charset=UTF-8",
        "Host": "search.people.cn",
        "Origin": "http://search.people.cn",
        "Pragma": "no-cache",
        "Referer": "http://search.people.cn/s?keyword=%E9%A3%9F%E7%89%A9%E4%B8%AD%E6%AF%92&st=0&_=1745890163341",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    }
    payload = {
        "endTime": end_time,
        "hasContent": True,
        "hasTitle": True,
        "isFuzzy": True,
        "key": keyword,
        "limit": limit,
        "page": page,
        "sortType": 2,
        "startTime": start_time,
        "type": 0
    }
    try:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                print(f"请求失败，状态码: {response.status}，页码: {page}")
                return None
    except Exception as e:
        print(f"请求异常，页码: {page}, 错误: {str(e)}")
        return None
def fetch_all_pages(keyword, max_pages=None, limit=10, delay=1, start_date=None, end_date=None):
    all_records = []
    current_page = 1
    total_pages = None
    date_range_str = ""
    if start_date or end_date:
        date_range_str = f"（日期范围: {start_date or '不限'} 至 {end_date or '不限'}）"
    print(f"开始抓取关键词 '{keyword}' {date_range_str} 的搜索结果...")
    while True:
        print(f"正在抓取第 {current_page} 页...")
        result = search_people_cn(keyword, page=current_page, limit=limit, 
                                 start_date=start_date, end_date=end_date)
        if not result or result.get("code") != "0":
            print(f"获取第 {current_page} 页失败，跳过继续")
            break
        if total_pages is None:
            total_pages = result.get("data", {}).get("pages", 0)
            total_records = result.get("data", {}).get("total", 0)
            print(f"检测到共有 {total_records} 条记录，{total_pages} 页结果")
            if max_pages is not None:
                total_pages = min(total_pages, max_pages)
                print(f"根据设置，将抓取 {total_pages} 页")
        records = result.get("data", {}).get("records", [])
        if start_date or end_date:
            if current_page == 1:
                for i, record in enumerate(records[:3]):
                    display_time = record.get("displayTime")
                    if display_time:
                        date_str = convert_timestamp_to_date(display_time)
                        print(f"样本记录 {i+1}: {date_str}")
        all_records.extend(records)
        print(f"已抓取 {len(records)} 条记录，总计 {len(all_records)} 条")
        if current_page >= total_pages:
            print("已抓取所有页面")
            break
        if max_pages is None and current_page >= 100:
            user_input = input("已抓取100页，是否继续？(y/n): ")
            if user_input.lower() != 'y':
                print("用户选择停止抓取")
                break
        current_page += 1
        time.sleep(delay)
    return all_records
def extract_article_content(url):
    try:
        response = requests.get(url, timeout=10)
        content_bytes = response.content
        encodings = ['gbk', 'gb2312', 'gb18030', 'utf-8']
        text = None
        for encoding in encodings:
            try:
                text = content_bytes.decode(encoding, errors='ignore')
                break
            except:
                continue
        if text is None:
            print(f"无法确定编码: {url}")
            return ""
        soup = BeautifulSoup(text, 'html.parser')
        content_div = soup.find('div', class_='rm_txt_con cf')
        if content_div:
            paragraphs = content_div.find_all('p')
            content = []
            for p in paragraphs:
                text = p.get_text().strip()
                if text and not text.startswith('分享让更多人看到'):
                    content.append(text)
            return '\n'.join(content)
        return ""
    except Exception as e:
        print(f"提取文章内容失败: {url}, 错误: {str(e)}")
        return ""
async def async_extract_article_content(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            content_bytes = await response.read()
            encodings = ['gbk', 'gb2312', 'gb18030', 'utf-8']
            text = None
            for encoding in encodings:
                try:
                    text = content_bytes.decode(encoding, errors='ignore')
                    break
                except:
                    continue
            if text is None:
                print(f"无法确定编码: {url}")
                return ""
            soup = BeautifulSoup(text, 'html.parser')
            content_div = soup.find('div', class_='rm_txt_con cf')
            if content_div:
                paragraphs = content_div.find_all('p')
                content = []
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text and not text.startswith('分享让更多人看到'):
                        content.append(text)
                return '\n'.join(content)
            return ""
    except Exception as e:
        print(f"异步提取文章内容失败: {url}, 错误: {str(e)}")
        return ""
async def batch_extract_contents(urls, max_concurrency=20):
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(max_concurrency)
        async def extract_with_semaphore(url):
            async with semaphore:
                return (url, await async_extract_article_content(session, url))
        print(f"开始异步批量提取 {len(urls)} 篇文章内容，并发数 {max_concurrency}")
        tasks = [extract_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks)
        return dict(results)
def convert_timestamp_to_date(timestamp):
    if timestamp:
        return datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M:%S')
    return ""
def clean_html(text):
    if not text:
        return ""
    import re
    clean_text = re.sub(r'<[^>]+>', '', text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text
def process_and_write_record(record, csv_writer):
    url = record.get('url', '')
    article_content = ""
    if url:
        print(f"正在提取文章内容: {url}")
        article_content = extract_article_content(url)
    row = {
        'title': clean_html(record.get('title', '')),
        'content': clean_html(record.get('content', '')),
        'url': url,
        'displayTime': convert_timestamp_to_date(record.get('displayTime')),
        'author': record.get('author', ''),
        'editor': record.get('editor', ''),
        'originName': record.get('originName', ''),
        'belongsName': record.get('belongsName', ''),
        'articleContent': article_content
    }
    csv_writer.write_row(row)
async def fetch_page(session, keyword, page, limit, start_date, end_date, result_queue, semaphore):
    async with semaphore:
        print(f"正在抓取第 {page} 页...")
        result = await async_search_people_cn(session, keyword, page, limit, 
                                            start_date, end_date)
        if result and result.get("code") == "0":
            records = result.get("data", {}).get("records", [])
            content_tasks = []
            for i, record in enumerate(records):
                url = record.get('url', '')
                if url:
                    task = asyncio.create_task(async_extract_article_content(session, url))
                    content_tasks.append((i, task))
            for i, task in content_tasks:
                try:
                    article_content = await task
                    records[i]['articleContent'] = article_content
                except Exception as e:
                    print(f"获取文章内容异常: {records[i].get('url', '')}, {str(e)}")
                    records[i]['articleContent'] = ""
            result_queue.put((page, records))
            print(f"第 {page} 页抓取成功，获取 {len(records)} 条记录")
        else:
            print(f"第 {page} 页抓取失败")
            result_queue.put((page, []))
async def async_fetch_all_pages(keyword, max_pages, limit, concurrency, start_date, end_date):
    async with aiohttp.ClientSession() as session:
        first_page = await async_search_people_cn(session, keyword, 1, limit, start_date, end_date)
        if not first_page or first_page.get("code") != "0":
            print("获取第一页失败，无法确定总页数")
            return []
        total_pages = first_page.get("data", {}).get("pages", 0)
        total_records = first_page.get("data", {}).get("total", 0)
        print(f"检测到共有 {total_records} 条记录，{total_pages} 页结果")
        if max_pages is not None:
            total_pages = min(total_pages, max_pages)
            print(f"根据设置，将抓取 {total_pages} 页")
        records = first_page.get("data", {}).get("records", [])
        if start_date or end_date and records:
            for i, record in enumerate(records[:3]):
                display_time = record.get("displayTime")
                if display_time:
                    date_str = convert_timestamp_to_date(display_time)
                    print(f"样本记录 {i+1}: {date_str}")
        content_tasks = []
        for i, record in enumerate(records):
            url = record.get('url', '')
            if url:
                task = asyncio.create_task(async_extract_article_content(session, url))
                content_tasks.append((i, task))
        for i, task in content_tasks:
            try:
                article_content = await task
                records[i]['articleContent'] = article_content
            except Exception as e:
                print(f"获取文章内容异常: {records[i].get('url', '')}, {str(e)}")
                records[i]['articleContent'] = ""
        result_queue = Queue()
        result_queue.put((1, records))
        print(f"第 1 页抓取成功，获取 {len(records)} 条记录")
        semaphore = asyncio.Semaphore(concurrency)
        tasks = []
        for page in range(2, total_pages + 1):
            task = asyncio.create_task(
                fetch_page(session, keyword, page, limit, start_date, end_date, result_queue, semaphore)
            )
            tasks.append(task)
        if tasks:
            await asyncio.gather(*tasks)
        return result_queue
def consumer_worker(result_queue, csv_writer, total_pages):
    processed_pages = 0
    total_records = 0
    processed_page_numbers = set()
    while processed_pages < total_pages:
        try:
            page_num, records = result_queue.get(timeout=60)  
            if page_num in processed_page_numbers:
                continue
            processed_page_numbers.add(page_num)
            processed_pages += 1
            for record in records:
                process_and_write_record(record, csv_writer)
                total_records += 1
            print(f"已处理 {processed_pages}/{total_pages} 页，当前总计 {total_records} 条记录")
            result_queue.task_done()
        except Exception as e:
            print(f"消费者处理异常: {str(e)}")
            time.sleep(1)  
    print(f"所有页面处理完成，共处理 {total_records} 条记录")
async def main_async(args):
    start_date = args.start_date
    end_date = args.end_date
    if args.year:
        try:
            year = int(args.year)
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            print(f"设置为抓取 {year} 年的数据")
        except ValueError:
            print(f"年份格式错误: {args.year}，应为数字")
    date_range = ""
    if start_date:
        date_range += f"_{start_date}"
    if end_date:
        date_range += f"至{end_date}"
    output_filename = f"{args.keyword}{date_range}_人民网新闻_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    fieldnames = [
        'title', 'content', 'url', 'displayTime', 'author', 
        'editor', 'originName', 'belongsName', 'articleContent'
    ]
    date_range_str = ""
    if start_date or end_date:
        date_range_str = f"（日期范围: {start_date or '不限'} 至 {end_date or '不限'}）"
    print(f"开始异步抓取关键词 '{args.keyword}' {date_range_str} 的搜索结果...")
    print(f"并发数: {args.concurrency}，最大页数: {args.max_pages or '全部'}")
    csv_writer = CSVWriter(output_filename, fieldnames)
    try:
        result_queue = await async_fetch_all_pages(
            args.keyword, args.max_pages, args.limit, args.concurrency, start_date, end_date
        )
        if result_queue.empty():
            print("没有找到任何结果")
            csv_writer.close()
            return
        total_pages = min(args.max_pages or float('inf'), result_queue.qsize())
        processed_pages = 0
        total_records = 0
        processed_page_numbers = set()
        while processed_pages < total_pages:
            try:
                page_num, records = result_queue.get(timeout=60)
                if page_num in processed_page_numbers:
                    continue
                processed_page_numbers.add(page_num)
                processed_pages += 1
                for record in records:
                    row = {
                        'title': clean_html(record.get('title', '')),
                        'content': clean_html(record.get('content', '')),
                        'url': record.get('url', ''),
                        'displayTime': convert_timestamp_to_date(record.get('displayTime')),
                        'author': record.get('author', ''),
                        'editor': record.get('editor', ''),
                        'originName': record.get('originName', ''),
                        'belongsName': record.get('belongsName', ''),
                        'articleContent': record.get('articleContent', '')
                    }
                    csv_writer.write_row(row)
                    total_records += 1
                print(f"已处理 {processed_pages}/{total_pages} 页，当前总计 {total_records} 条记录")
                result_queue.task_done()
            except Exception as e:
                print(f"处理记录异常: {str(e)}")
                time.sleep(1)
        print(f"所有页面处理完成，共处理 {total_records} 条记录")
    finally:
        csv_writer.close()
        print(f"数据抓取完成，结果保存到 {output_filename}")
def save_to_csv(records, filename):
    fieldnames = [
        'title', 'content', 'url', 'displayTime', 'author', 
        'editor', 'originName', 'belongsName', 'articleContent'
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        print("开始并发提取文章内容...")
        url_content_map = {}
        futures = []
        for record in records:
            url = record.get('url', '')
            if url:
                future = executor.submit(extract_article_content, url)
                futures.append((url, future))
        for url, future in futures:
            try:
                content = future.result()
                url_content_map[url] = content
            except Exception as e:
                print(f"获取提取结果异常: {url}, {str(e)}")
                url_content_map[url] = ""
    with open(filename, 'w', encoding='utf-8-sig', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            url = record.get('url', '')
            article_content = url_content_map.get(url, "")
            row = {
                'title': clean_html(record.get('title', '')),
                'content': clean_html(record.get('content', '')),
                'url': url,
                'displayTime': convert_timestamp_to_date(record.get('displayTime')),
                'author': record.get('author', ''),
                'editor': record.get('editor', ''),
                'originName': record.get('originName', ''),
                'belongsName': record.get('belongsName', ''),
                'articleContent': article_content
            }
            writer.writerow(row)
    print(f"已将 {len(records)} 条新闻记录保存到 {filename}")
def main():
    parser = argparse.ArgumentParser(description='人民网搜索爬虫')
    parser.add_argument('-k', '--keyword', default='食物中毒', help='搜索关键词')
    parser.add_argument('-m', '--max_pages', type=int, default=None, help='最大抓取页数，默认不限制')
    parser.add_argument('-l', '--limit', type=int, default=10, help='每页结果数，默认为10')
    parser.add_argument('-d', '--delay', type=float, default=1.0, help='请求间隔(秒)，默认为1秒')
    parser.add_argument('-s', '--start_date', help='开始日期 (YYYY-MM-DD格式)')
    parser.add_argument('-e', '--end_date', help='结束日期 (YYYY-MM-DD格式)')
    parser.add_argument('-y', '--year', help='指定年份，会自动设置该年度的开始和结束日期')
    parser.add_argument('-a', '--async_mode', action='store_true', help='使用异步模式抓取')
    parser.add_argument('-c', '--concurrency', type=int, default=5, help='异步模式下的并发数，默认为5')
    args = parser.parse_args()
    if args.async_mode:
        if args.concurrency < 1:
            args.concurrency = 1
        elif args.concurrency > 20:
            print("警告: 并发数过高可能导致请求被封，已限制为最大20")
            args.concurrency = 20
        asyncio.run(main_async(args))
    else:
        start_date = args.start_date
        end_date = args.end_date
        if args.year:
            try:
                year = int(args.year)
                start_date = f"{year}-01-01"
                end_date = f"{year}-12-31"
                print(f"设置为抓取 {year} 年的数据")
            except ValueError:
                print(f"年份格式错误: {args.year}，应为数字")
        all_records = fetch_all_pages(
            keyword=args.keyword, 
            max_pages=args.max_pages, 
            limit=args.limit,
            delay=args.delay,
            start_date=start_date,
            end_date=end_date
        )
        date_range = ""
        if start_date:
            date_range += f"_{start_date}"
        if end_date:
            date_range += f"至{end_date}"
        output_filename = f"{args.keyword}{date_range}_人民网新闻_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        save_to_csv(all_records, output_filename)
        print(f"数据抓取完成，共抓取 {len(all_records)} 条新闻")
if __name__ == "__main__":
    main()