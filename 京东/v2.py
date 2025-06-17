'''
Author: 择安网络
Code function: 
Date: 2025-06-17 17:07:37
FilePath: /爬虫仓/京东/v2.py
LastEditTime: 2025-06-17 17:07:48
Function: 6月12日更新
'''
import requests
import re
import time
import csv
import os
import random
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
class SocialMediaAnalyzer:
    def __init__(self, query_term: str, range_start: int = 1, range_end: int = 5, interval: float = 1.5):
        self.query_term = query_term
        self.range_start = range_start
        self.range_end = range_end
        self.interval = interval
        self.encoded_term = urllib.parse.quote(self.query_term)
        self._auth_token = ''
        self._base_request_config = {
            "browser": {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "accept_language": "zh-CN,zh;q=0.9",
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept_encoding": "gzip, deflate, br, zstd"
            },
            "platform": {
                "host": "s.weibo.com",
                "scheme": "https"
            }
        }
    def _create_browser_headers(self) -> Dict[str, str]:
        return {
            "authority": self._base_request_config["platform"]["host"],
            "accept": self._base_request_config["browser"]["accept"],
            "accept-encoding": self._base_request_config["browser"]["accept_encoding"],
            "accept-language": self._base_request_config["browser"]["accept_language"],
            "cache-control": "no-cache",
            "cookie": self._auth_token,
            "pragma": "no-cache",
            "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": self._base_request_config["browser"]["user_agent"]
        }
    def _create_api_headers(self) -> Dict[str, str]:
        return {
            "authority": "weibo.com",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": self._base_request_config["browser"]["accept_encoding"],
            "accept-language": self._base_request_config["browser"]["accept_language"],
            "cache-control": "no-cache",
            "client-version": "v2.47.72",
            "cookie": self._auth_token,
            "pragma": "no-cache",
            "referer": "https://weibo.com/",
            "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors", 
            "sec-fetch-site": "same-origin",
            "user-agent": self._base_request_config["browser"]["user_agent"],
            "x-requested-with": "XMLHttpRequest"
        }
    def _get_author_profile(self, author_id: str) -> Dict[str, Any]:
        if author_id == "unknown":
            return {"location_info": "未知"}
        try:
            api_endpoint = f"https://weibo.com/ajax/profile/detail?uid={author_id}"
            time.sleep(0.3 + 0.7 * random.random())
            response = requests.get(api_endpoint, headers=self._create_api_headers())
            if response.status_code == 200:
                result = response.json()
                if result.get("ok") == 1 and "data" in result:
                    return result["data"]
            return {"location_info": "未知"}
        except Exception as e:
            print(f"获取作者信息失败 (ID: {author_id}): {str(e)}")
            return {"location_info": "未知"}
    def _extract_region_info(self, location_text: str) -> str:
        if not location_text or location_text == "未知":
            return "未知"
        region_match = re.search(r'IP属地：(.+)', location_text)
        if region_match:
            return region_match.group(1)
        return location_text
    def _extract_hashtags(self, text_content: str) -> List[str]:
        hashtags = []
        hashtag_pattern = re.compile(r'#([^#]+)#')
        matches = hashtag_pattern.findall(text_content)
        return matches
    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    def _parse_content_page(self, page_html: bytes, page_index: int) -> List[Dict[str, Any]]:
        parsed_data = []
        soup = BeautifulSoup(page_html, 'html.parser')
        content_cards = soup.select('.card-wrap')
        print(f"页面 {page_index} 找到 {len(content_cards)} 条内容")
        valid_content_count = 0
        for idx, card in enumerate(content_cards, 1):
            try:
                content_id = card.get('mid', 'unknown')
                if content_id == 'unknown':
                    continue
                valid_content_count += 1
                author_block = card.select_one('.name')
                author_name = author_block.text.strip() if author_block else "未知用户"
                author_link = author_block.get('href') if author_block else None
                author_id = "unknown"
                if author_link:
                    if '//' in author_link:
                        id_match = re.search(r'/(\d+)\?', author_link)
                        if id_match:
                            author_id = id_match.group(1)
                        else:
                            parts = author_link.split('/')
                            if len(parts) > 3:
                                author_id = parts[-1].split('?')[0]
                    else:
                        id_match = re.search(r'(\d+)\?', author_link)
                        if id_match:
                            author_id = id_match.group(1)
                author_profile = self._get_author_profile(author_id)
                region = "未知"
                if "location_info" in author_profile:
                    region = self._extract_region_info(author_profile["location_info"])
                main_content_elem = card.select_one('p[node-type="feed_list_content"]')
                full_content_elem = card.select_one('p[node-type="feed_list_content_full"]')
                content_text = ""
                if full_content_elem:
                    content_text = full_content_elem.text.strip()
                elif main_content_elem:
                    content_text = main_content_elem.text.strip()
                content_text = self._normalize_text(content_text)
                hashtags = self._extract_hashtags(content_text)
                metadata_block = card.select_one('.from')
                publish_time = "未知时间"
                client_source = "未知来源"
                if metadata_block:
                    time_elem = metadata_block.select_one('a')
                    if time_elem:
                        publish_time = time_elem.text.strip()
                    if len(metadata_block.contents) > 1:
                        source_text = metadata_block.contents[-1].text.strip() if hasattr(metadata_block.contents[-1], 'text') else ""
                        if source_text and "来自" in source_text:
                            client_source = source_text.replace("来自", "").strip()
                shares_elem = card.select_one('.woo-box-flex:nth-of-type(1)')
                shares_count = "0"
                if shares_elem:
                    shares_text = shares_elem.text.strip()
                    shares_match = re.search(r'\d+', shares_text)
                    if shares_match:
                        shares_count = shares_match.group(0)
                    elif "转发" in shares_text and not re.search(r'\d+', shares_text):
                        shares_count = "0"
                comments_elem = card.select_one('.woo-box-flex:nth-of-type(2)')
                comments_count = "0"
                if comments_elem:
                    comments_text = comments_elem.text.strip()
                    comments_match = re.search(r'\d+', comments_text)
                    if comments_match:
                        comments_count = comments_match.group(0)
                    elif "评论" in comments_text and not re.search(r'\d+', comments_text):
                        comments_count = "0" 
                reactions_elem = card.select_one('.woo-like-count')
                reactions_count = "0"
                if reactions_elem:
                    reactions_text = reactions_elem.text.strip()
                    if reactions_text.isdigit():
                        reactions_count = reactions_text
                    else:
                        reactions_match = re.search(r'\d+', reactions_text)
                        if reactions_match:
                            reactions_count = reactions_match.group(0)
                has_media = "是" if card.select_one('.media') else "否"
                content_data = {
                    "页面索引": page_index,
                    "序列号": valid_content_count,
                    "作者ID": author_id,
                    "作者名称": author_name,
                    "所在地区": region,
                    "内容正文": content_text,
                    "标签列表": hashtags,
                    "发布时间": publish_time,
                    "客户端": client_source,
                    "分享数": shares_count,
                    "评论数": comments_count,
                    "互动数": reactions_count,
                    "包含媒体": has_media,
                    "内容ID": content_id
                }
                parsed_data.append(content_data)
                print(f"\n----- 页面{page_index} 内容 {valid_content_count} -----")
                print(f"内容ID: {content_id}")
                print(f"作者ID: {author_id}")
                print(f"作者: {author_name}")
                print(f"地区: {region}")
                print(f"正文: {content_text[:50]}..." if len(content_text) > 50 else f"正文: {content_text}")
                print(f"标签: {', '.join(hashtags)}" if hashtags else "标签: 无")
                print(f"发布: {publish_time}")
                print(f"来源: {client_source}")
                print(f"分享: {shares_count}, 评论: {comments_count}, 互动: {reactions_count}")
                print(f"媒体: {has_media}")
            except Exception as e:
                print(f"解析第 {idx} 条内容时发生错误: {str(e)}")
        if not parsed_data:
            print(f"页面 {page_index} 没有找到有效数据！")
            return []
        print(f"页面 {page_index} 成功解析 {len(parsed_data)} 条有效数据")
        return parsed_data
    def collect_data(self) -> None:
        all_results = []
        print(f"开始收集关键词 '{self.query_term}' 的第 {self.range_start}-{self.range_end} 页数据...")
        for page_num in range(self.range_start, self.range_end + 1):
            endpoint = f"https://s.weibo.com/weibo?q={self.encoded_term}&page={page_num}"
            headers = self._create_browser_headers()
            headers["path"] = f"/weibo?q={self.encoded_term}&page={page_num}"
            print(f"\n正在获取第 {page_num} 页...")
            try:
                response = requests.get(endpoint, headers=headers)
                if response.status_code == 200:
                    print(f"成功访问: 状态码 {response.status_code}")
                    page_results = self._parse_content_page(response.content, page_num)
                    if page_results:
                        all_results.extend(page_results)
                    if page_num < self.range_end:
                        wait_time = self.interval + random.uniform(0.5, 1.5)
                        print(f"等待 {wait_time:.2f} 秒后继续...")
                        time.sleep(wait_time)
                else:
                    print(f"请求失败: 状态码 {response.status_code}")
            except Exception as e:
                print(f"处理第 {page_num} 页时出错: {str(e)}")
        self._export_to_csv(all_results)
        print(f"\n数据收集完成! 共获取 {len(all_results)} 条有效数据")
    def _export_to_csv(self, data_collection: List[Dict[str, Any]]) -> None:
        if not data_collection:
            print("没有数据可导出！")
            return
        output_filename = f"{self.query_term}.csv"
        try:
            with open(output_filename, "w", encoding="utf-8-sig", newline="") as f:
                fieldnames = []
                for key in data_collection[0].keys():
                    if key != "标签列表":
                        fieldnames.append(key)
                    else:
                        fieldnames.append("标签_文本")
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for item in data_collection:
                    row = {}
                    for key, value in item.items():
                        if key != "标签列表":
                            row[key] = value
                        else:
                            row["标签_文本"] = "|".join(value) if value else ""
                    writer.writerow(row)
            print(f"已将 {len(data_collection)} 条数据保存到 {output_filename}")
            file_size = os.path.getsize(output_filename)
            if file_size < 1024:
                size_text = f"{file_size} 字节"
            elif file_size < 1024 * 1024:
                size_text = f"{file_size/1024:.2f} KB"
            else:
                size_text = f"{file_size/(1024*1024):.2f} MB"
            print(f"文件大小: {size_text}")
        except Exception as e:
            print(f"导出CSV文件时发生错误: {str(e)}")
if __name__ == "__main__":
    analyzer = SocialMediaAnalyzer("小米手机新品发布", 1, 200, 2)
    analyzer.collect_data() 