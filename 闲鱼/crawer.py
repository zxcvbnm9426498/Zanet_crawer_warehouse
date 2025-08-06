import os
import re
import json
import csv
import logging
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv
from playwright.sync_api import Playwright, sync_playwright

load_dotenv()
def setup_logging():
    class ColoredFormatter(logging.Formatter):
        COLORS = {
            'DEBUG': '\033[36m',    
            'INFO': '\033[32m',     
            'WARNING': '\033[33m',  
            'ERROR': '\033[31m',    
            'CRITICAL': '\033[35m', 
            'RESET': '\033[0m'      
        }
        def format(self, record):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            record.asctime = self.formatTime(record, '%H:%M:%S')
            if record.levelname == 'INFO':
                log_format = f"{color}[%(asctime)s] 📋 %(message)s{reset}"
            elif record.levelname == 'WARNING':
                log_format = f"{color}[%(asctime)s] ⚠️  %(message)s{reset}"
            elif record.levelname == 'ERROR':
                log_format = f"{color}[%(asctime)s] ❌ %(message)s{reset}"
            elif record.levelname == 'DEBUG':
                log_format = f"{color}[%(asctime)s] 🔍 %(message)s{reset}"
            else:
                log_format = f"{color}[%(asctime)s] %(levelname)s: %(message)s{reset}"
            formatter = logging.Formatter(log_format)
            return formatter.format(record)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    return logger
logger = setup_logging()
def log_step(step_num, title):
    separator = "=" * 50
    logger.info(f"\n{separator}")
    logger.info(f"🔄 步骤 {step_num}: {title}")
    logger.info(separator)
all_products_data = []
item_details_cache = {}
def convert_timestamp(timestamp: str) -> str:
    if not timestamp:
        return ""
    try:
        dt = datetime.fromtimestamp(int(timestamp) / 1000)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return timestamp
def extract_item_info(item_data: Dict[str, Any]) -> Dict[str, Any]:
    if "main" not in item_data:
        return None
    main = item_data["main"]
    click_param = main.get("clickParam", {})
    args = click_param.get("args", {})
    ex_content = main.get("exContent", {})
    item_info = {
        "序号": "",
        "商品ID": args.get("id", ""),
        "商品标题": "",
        "价格": args.get("price", ""),
        "原价": "",
        "想要人数": args.get("wantNum", ""),
        "卖家ID": args.get("seller_id", ""),
        "卖家名称": "",
        "卖家卖了多少件宝贝": "",  
        "卖家注册年限": "",  
        "卖家最后访问时间": "",  
        "商品主图URLs": "",  
        "发布时间": convert_timestamp(args.get("publishTime", "")),
        "位置": f"{args.get('p_city', '')} {args.get('p_district', '')}".strip(),
        "标签": args.get("tagname", ""),
        "是否视频": "",
        "分类ID": args.get("catId", ""),
        "淘宝分类ID": args.get("tbCatId", ""),
        "子分类ID": args.get("cCatId", ""),
        "图片URL": "",
        "用户头像": "",
        "用户昵称": "",
        "评价数": "",
        "好评率": "",
        "全新标签": "",
        "品牌标签": "",
        "包邮标签": "",
        "特价标签": "",
        "好评标签": "",
        "芝麻信用": args.get("zhimaOffline", ""),
        "目标URL": "",
        "详情页类型": "",
        "是否拍卖": ""
    }
    if "detailParams" in ex_content:
        detail_params = ex_content["detailParams"]
        item_info["商品标题"] = detail_params.get("title", "")
        item_info["卖家名称"] = detail_params.get("userNick", "")
        item_info["是否视频"] = detail_params.get("isVideo", "")
        item_info["商品ID"] = detail_params.get("itemId", item_info["商品ID"])
    if "area" in ex_content:
        item_info["位置"] = ex_content["area"]
    item_info["图片URL"] = ex_content.get("picUrl", "")
    if "oriPrice" in ex_content:
        item_info["原价"] = ex_content["oriPrice"]
    item_info["用户头像"] = ex_content.get("userAvatarUrl", "")
    item_info["用户昵称"] = ex_content.get("userNickName", "")
    item_info["目标URL"] = main.get("targetUrl", "")
    item_info["详情页类型"] = ex_content.get("detailPageType", "")
    item_info["是否拍卖"] = ex_content.get("isAuction", "")
    if "fishTags" in ex_content:
        fish_tags = ex_content["fishTags"]
        for tag_type in ["r1", "r2", "r3", "r4", "r5"]:
            if tag_type in fish_tags and "tagList" in fish_tags[tag_type]:
                for tag in fish_tags[tag_type]["tagList"]:
                    tag_content = tag.get("data", {}).get("content", "")
                    if tag_type == "r1" and "freeShippingIcon" in tag_content:
                        item_info["包邮标签"] = "包邮"
                    elif tag_type == "r2":
                        if "全新" in tag_content:
                            item_info["全新标签"] = "全新"
                        elif "ZTT" in tag_content or "中天" in tag_content:
                            item_info["品牌标签"] = tag_content
                    elif tag_type == "r3" and "¥" in tag_content:
                        item_info["特价标签"] = tag_content
                    elif tag_type == "r4" and "好评" in tag_content:
                        item_info["好评标签"] = tag_content
    if "userFishShopLabel" in ex_content and "tagList" in ex_content["userFishShopLabel"]:
        for tag in ex_content["userFishShopLabel"]["tagList"]:
            tag_content = tag.get("data", {}).get("content", "")
            if "评价" in tag_content:
                item_info["评价数"] = tag_content
            elif "好评率" in tag_content:
                item_info["好评率"] = tag_content
    if not item_info["商品标题"]:
        if "title" in item_data:
            item_info["商品标题"] = item_data["title"]
        elif "richTitle" in ex_content:
            rich_title = ex_content["richTitle"]
            for title_part in rich_title:
                if title_part.get("type") == "Text" and "data" in title_part:
                    item_info["商品标题"] = title_part["data"].get("text", "")
                    break
    item_id = item_info["商品ID"]
    if item_id and item_id in item_details_cache:
        detail_info = item_details_cache[item_id]
        if isinstance(detail_info, dict):
            item_info["卖家卖了多少件宝贝"] = detail_info.get("卖家卖了多少件宝贝", "")
            item_info["卖家注册年限"] = detail_info.get("卖家注册年限", "")
            item_info["卖家最后访问时间"] = detail_info.get("卖家最后访问时间", "")
            item_info["商品主图URLs"] = detail_info.get("商品主图URLs", "")
        else:
            item_info["卖家卖了多少件宝贝"] = detail_info
    return item_info
def process_detail_api_response(response_data: Dict[str, Any], item_id: str):
    try:
        if "data" in response_data:
            detail_info = {}
            if "sellerDO" in response_data["data"]:
                seller_data = response_data["data"]["sellerDO"]
                detail_info["卖家卖了多少件宝贝"] = seller_data.get("itemCount", "")
                user_reg_day = seller_data.get("userRegDay", 0)
                if user_reg_day:
                    years_from_days = user_reg_day / 365.25
                    detail_info["卖家注册年限"] = f"{years_from_days:.1f}年"
                else:
                    detail_info["卖家注册年限"] = ""
                detail_info["卖家最后访问时间"] = seller_data.get("lastVisitTime", "")
            if "itemDO" in response_data["data"] and "imageInfos" in response_data["data"]["itemDO"]:
                image_infos = response_data["data"]["itemDO"]["imageInfos"]
                image_urls = [img.get("url", "") for img in image_infos if img.get("url")]
                detail_info["商品主图URLs"] = ",".join(image_urls)
            else:
                detail_info["商品主图URLs"] = ""
            item_details_cache[item_id] = detail_info
            logger.info(f"✅ 商品 {item_id} 详情获取成功 - 卖家卖了: {detail_info.get('卖家卖了多少件宝贝', '')}件宝贝, 主图数: {len(detail_info.get('商品主图URLs', '').split(',')) if detail_info.get('商品主图URLs') else 0}")
            return detail_info.get("卖家卖了多少件宝贝", "")
        else:
            logger.warning(f"商品 {item_id} 详情响应数据格式异常")
            return ""
    except Exception as e:
        logger.error(f"处理商品 {item_id} 详情数据时出错: {e}")
        return ""
def process_api_response(response_data: Dict[str, Any], page_num: int) -> int:
    items_count = 0
    try:
        if "data" in response_data and "resultList" in response_data["data"]:
            items = response_data["data"]["resultList"]
            for item_data in items:
                if "data" in item_data and "item" in item_data["data"]:
                    item_info = extract_item_info(item_data["data"]["item"])
                    if item_info:
                        item_info["页码"] = page_num
                        all_products_data.append(item_info)
                        items_count += 1
            logger.info(f"第 {page_num} 页处理了 {items_count} 个商品")
        else:
            logger.warning(f"第 {page_num} 页响应数据格式异常")
    except Exception as e:
        logger.error(f"处理第 {page_num} 页数据时出错: {e}")
    return items_count
def save_products_to_csv(keyword: str):
    if not all_products_data:
        logger.warning("没有商品数据需要保存")
        return
    safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '-', '_')).rstrip()
    filename = f"{safe_keyword}_商品数据.csv"
    try:
        with open(filename, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            headers = [
                "序号", "页码", "商品ID", "商品标题", "价格", "原价", "想要人数", "卖家ID", "卖家名称", "卖家卖了多少件宝贝",
                "卖家注册年限", "卖家最后访问时间", "商品主图URLs",
                "发布时间", "位置", "标签", "是否视频", "分类ID", "淘宝分类ID",
                "子分类ID", "图片URL", "用户头像", "用户昵称", "评价数", "好评率",
                "全新标签", "品牌标签", "包邮标签", "特价标签", "好评标签",
                "芝麻信用", "目标URL", "详情页类型", "是否拍卖"
            ]
            writer.writerow(headers)
            for i, item in enumerate(all_products_data, 1):
                item["序号"] = i
                row = []
                for header in headers:
                    value = item.get(header, "")
                    if header in ["商品ID", "卖家ID", "分类ID", "淘宝分类ID", "子分类ID"] and value:
                        value = f"'{value}"
                    row.append(value)
                writer.writerow(row)
        logger.info(f"商品数据已保存到: {filename}")
        logger.info(f"总共保存了 {len(all_products_data)} 个商品")
    except Exception as e:
        logger.error(f"保存CSV文件时出错: {e}")
def fetch_item_details(page, item_ids: List[str]):
    logger.info(f"开始获取 {len(item_ids)} 个商品的详情信息...")
    success_count = 0
    for i, item_id in enumerate(item_ids, 1):
        try:
            if page.is_closed():
                logger.error("页面已关闭，无法继续获取详情")
                break
            detail_url = f"https://www.goofish.com/item?id={item_id}"
            logger.debug(f"访问商品详情页 ({i}/{len(item_ids)}): {item_id}")
            cache_before = len(item_details_cache)
            page.goto(detail_url, timeout=30000)
            page.wait_for_load_state('networkidle', timeout=10000)
            page.wait_for_timeout(2000)  
            cache_after = len(item_details_cache)
            if item_id in item_details_cache:
                detail_info = item_details_cache[item_id]
                if isinstance(detail_info, dict):
                    sold_count = detail_info.get("卖家卖了多少件宝贝", "")
                    logger.info(f"✅ 商品 {item_id} 详情获取成功 (卖家卖了: {sold_count}件宝贝)")
                else:
                    logger.info(f"✅ 商品 {item_id} 详情获取成功 (卖家卖了: {detail_info}件宝贝)")
                success_count += 1
            elif cache_after > cache_before:
                logger.info(f"✅ 获取到详情数据，但商品ID可能不匹配")
                success_count += 1
            else:
                logger.warning(f"⚠️ 商品 {item_id} 详情获取失败")
            if i % 10 == 0:
                logger.info(f"已处理 {i}/{len(item_ids)} 个商品详情，成功 {success_count} 个")
                page.wait_for_timeout(3000)  
            else:
                page.wait_for_timeout(1000)   
        except Exception as e:
            logger.error(f"获取商品 {item_id} 详情时出错: {e}")
            if "closed" in str(e).lower():
                logger.error("页面已关闭，停止获取详情")
                break
            continue
    logger.info(f"商品详情获取完成，成功获取 {success_count} 个商品的详情")
def load_cookies_from_file():
    try:
        if os.path.exists('cookies.json'):
            with open('cookies.json', 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)
                if isinstance(cookies_data, dict) and 'cookies' in cookies_data:
                    cookies = cookies_data['cookies']
                elif isinstance(cookies_data, list):
                    cookies = cookies_data
                else:
                    logger.error("❌ cookies.json格式不正确")
                    return []
                logger.info(f"✅ 成功加载 {len(cookies)} 个cookies")
                return cookies
        else:
            logger.warning("⚠️ cookies.json文件不存在")
            return []
    except Exception as e:
        logger.error(f"❌ 加载cookies.json失败: {e}")
        return []
def run(playwright: Playwright) -> None:
    global all_products_data, item_details_cache
    all_products_data = []  
    item_details_cache = {}  
    logger.info("=" * 60)
    logger.info("🐟 闲鱼商品自动化采集工具")
    logger.info("=" * 60)
    keyword = os.getenv('DEFAULT_KEYWORD', '移动光缆')
    show_browser = os.getenv('SHOW_BROWSER', 'true').lower() == 'true'
    headless_mode = not show_browser
    logger.info(f"搜索关键词: {keyword}")
    logger.info(f"浏览器模式: {'显示界面' if show_browser else '无界面模式'}")
    browser = playwright.chromium.launch(headless=headless_mode)
    cookies = load_cookies_from_file()
    context = browser.new_context()
    if cookies:
        context.add_cookies(cookies)
        logger.info("✅ Cookies已添加到浏览器context")
    page = context.new_page()
    try:
        log_step(1, "访问闲鱼网站")
        page.goto("https://www.goofish.com/")
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)
        logger.info("页面加载完成")
        log_step(2, f"搜索商品: {keyword}")
        search_selectors = [
            'input[class*="search-input"]',
            'input[type="text"][maxlength="100"]',
            'input[type="text"]',
        ]
        search_box = None
        for selector in search_selectors:
            try:
                search_box = page.locator(selector).first
                if search_box.is_visible(timeout=3000):
                    logger.info(f"找到搜索框: {selector}")
                    break
            except:
                continue
        if search_box is None:
            logger.error("无法找到搜索框")
            raise Exception("无法找到搜索框")
        search_box.click()
        search_box.clear()
        search_box.fill(keyword)
        logger.info(f"已输入关键词: {keyword}")
        try:
            search_button = page.get_by_role("button", name="搜索")
            if search_button.is_visible(timeout=2000):
                search_button.click()
                logger.info("点击搜索按钮")
            else:
                search_box.press("Enter")
                logger.info("按回车键搜索")
        except:
            search_box.press("Enter")
            logger.info("使用回车键搜索")
        page.wait_for_load_state('networkidle')
        logger.info("搜索结果加载完成")
        area_province = os.getenv('AREA_PROVINCE', '山西')
        area_city = os.getenv('AREA_CITY', '全山西')
        api_responses = []
        current_page_num = 1
        listen_search_api = True
        def handle_response(response):
            nonlocal current_page_num, listen_search_api
            if listen_search_api and "mtop.taobao.idlemtopsearch.pc.search" in response.url:
                try:
                    if response.status == 200:
                        response_data = response.json()
                        logger.debug(f"捕获到搜索API响应，页码: {current_page_num}")
                        items_count = process_api_response(response_data, current_page_num)
                        if items_count > 0:
                            logger.info(f"第 {current_page_num} 页获取到 {items_count} 个商品")
                        api_responses.append({
                            'page': current_page_num,
                            'data': response_data,
                            'items_count': items_count
                        })
                    else:
                        logger.warning(f"API响应状态码异常: {response.status}")
                except Exception as e:
                    logger.error(f"处理API响应时出错: {e}")
            elif "mtop.taobao.idle.pc.detail" in response.url:
                try:
                    if response.status == 200:
                        response_data = response.json()
                        item_id = None
                        try:
                            post_data = response.request.post_data or ""
                            if "itemId" in post_data:
                                import urllib.parse
                                parsed_data = urllib.parse.parse_qs(post_data)
                                if "data" in parsed_data:
                                    data_json = json.loads(parsed_data["data"][0])
                                    item_id = data_json.get("itemId")
                        except:
                            import re
                            url_match = re.search(r'"itemId":"(\d+)"', post_data)
                            if url_match:
                                item_id = url_match.group(1)
                        if item_id:
                            logger.debug(f"捕获到商品详情API响应，商品ID: {item_id}")
                            process_detail_api_response(response_data, item_id)
                        else:
                            logger.warning("无法从详情API响应中提取商品ID")
                except Exception as e:
                    logger.error(f"处理详情API响应时出错: {e}")
        page.on("response", handle_response)
        log_step(3, f"设置地区筛选 ({area_province} - {area_city})")
        try:
            area_button = page.locator('div[class*="areaText"]').first
            if area_button.is_visible(timeout=3000):
                logger.info("找到区域按钮，进行鼠标悬停")
                area_button.hover()
                page.wait_for_timeout(1000)
                try:
                    page.get_by_text(area_province).click()
                    page.wait_for_timeout(500)
                    logger.info(f"选择省份: {area_province}")
                except Exception as e:
                    logger.warning(f"选择省份 {area_province} 失败: {e}")
                    raise
                try:
                    page.get_by_text(area_city).click()
                    page.wait_for_timeout(1000)
                    logger.info(f"选择城市: {area_city}")
                except Exception as e:
                    logger.warning(f"选择城市 {area_city} 失败: {e}")
                    raise
                try:
                    view_button = page.get_by_text(text=re.compile(r"查看.*件宝贝"))
                    if view_button.is_visible(timeout=3000):
                        button_text = view_button.text_content()
                        view_button.click()
                        page.wait_for_timeout(1000)
                        logger.info(f"点击 {button_text}")
                        logger.info("地区筛选设置完成")
                        page.wait_for_load_state('networkidle')
                        page.wait_for_timeout(2000)  
                    else:
                        logger.warning("未找到查看宝贝按钮")
                except Exception as e:
                    logger.warning(f"点击查看宝贝按钮失败: {e}")
            else:
                logger.warning("未找到区域按钮，跳过地区筛选")
        except Exception as e:
            logger.error(f"地区筛选失败: {e}")
            logger.warning("跳过地区筛选，继续执行")
        log_step(4, "开始翻页浏览")
        try:
            page_info = page.locator('span[class*="search-page-tiny-page"]').first
            if page_info.is_visible(timeout=3000):
                page_text = page_info.text_content()
                total_pages = int(page_text.split('/')[1]) if '/' in page_text else 1
                logger.info(f"检测到总页数: {total_pages}")
            else:
                total_pages = 3
                logger.warning("未检测到页数信息，默认翻3页")
        except:
            total_pages = 3
            logger.warning("页数解析失败，默认翻3页")
        max_pages_setting = os.getenv('MAX_PAGES', '5').lower().strip()
        if max_pages_setting == 'max':
            max_pages = total_pages - 1
            logger.info(f"配置为翻完所有页面 (总共 {total_pages} 页，需翻 {max_pages} 页)")
        else:
            try:
                max_pages_config = int(max_pages_setting)
                max_pages = min(total_pages - 1, max_pages_config)
                logger.info(f"配置翻页 {max_pages} 页 (配置: {max_pages_config}页，总页数: {total_pages}页)")
            except ValueError:
                max_pages = min(total_pages - 1, 5)
                logger.warning(f"配置值 '{max_pages_setting}' 无效，使用默认值翻页 {max_pages} 页")
        for i in range(max_pages):
            try:
                current_page_num = i + 2  
                logger.info(f"📄 翻到第 {current_page_num} 页")
                top_next_button = page.locator('div[class*="search-page-tiny-arrow-right"]').first
                if top_next_button.is_visible(timeout=2000):
                    logger.debug("使用顶部翻页按钮")
                    top_next_button.click()
                    page.wait_for_load_state('networkidle')
                    page.wait_for_timeout(2000)
                    logger.info(f"✅ 已翻到第 {current_page_num} 页")
                    continue
                logger.debug("顶部按钮不可用，尝试底部分页器")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)
                bottom_next_button = page.locator('div[class*="search-pagination-arrow-right"]').first
                if bottom_next_button.is_visible(timeout=3000):
                    logger.debug("使用底部翻页按钮")
                    bottom_next_button.click()
                    page.wait_for_load_state('networkidle')
                    page.wait_for_timeout(2000)
                    logger.info(f"✅ 已翻到第 {current_page_num} 页")
                    page.evaluate("window.scrollTo(0, 0)")
                    page.wait_for_timeout(1000)
                    continue
                try:
                    page_number_button = page.locator(f'div[class*="search-pagination-page-box"]:has-text("{current_page_num}")').first
                    if page_number_button.is_visible(timeout=2000):
                        logger.debug(f"直接点击页码 {current_page_num}")
                        page_number_button.click()
                        page.wait_for_load_state('networkidle')
                        page.wait_for_timeout(2000)
                        logger.info(f"✅ 已翻到第 {current_page_num} 页")
                        continue
                except:
                    pass
                logger.error("所有翻页方法都失败，停止翻页")
                break
            except Exception as e:
                logger.error(f"翻页时出现错误: {e}")
                break
        if all_products_data:
            listen_search_api = False
            logger.debug("已停止监听搜索API，专注于详情API")
            log_step(5, "获取商品详情信息")
            item_ids = []
            for item in all_products_data:
                item_id = item.get("商品ID", "")
                if item_id and item_id not in item_ids:
                    item_ids.append(item_id)
            logger.info(f"需要获取 {len(item_ids)} 个商品的详情信息")
            try:
                fetch_item_details(page, item_ids)
                for item in all_products_data:
                    item_id = item.get("商品ID", "")
                    if item_id and item_id in item_details_cache:
                        detail_info = item_details_cache[item_id]
                        if isinstance(detail_info, dict):
                            item["卖家卖了多少件宝贝"] = detail_info.get("卖家卖了多少件宝贝", "")
                            item["卖家注册年限"] = detail_info.get("卖家注册年限", "")
                            item["卖家最后访问时间"] = detail_info.get("卖家最后访问时间", "")
                            item["商品主图URLs"] = detail_info.get("商品主图URLs", "")
                        else:
                            item["卖家卖了多少件宝贝"] = detail_info
                logger.info(f"成功获取 {len(item_details_cache)} 个商品的详情信息")
            except Exception as e:
                logger.error(f"获取商品详情时出错: {e}")
                logger.warning("跳过商品详情获取，继续保存基础数据")
        logger.info("\n" + "=" * 50)
        logger.info("✅ 所有任务已完成！")
        logger.info("=" * 50)
        if all_products_data:
            save_products_to_csv(keyword)
        else:
            logger.warning("没有采集到商品数据")
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
    finally:
        logger.info("正在清理资源...")
        try:
            context.close()
            browser.close()
        except:
            pass
        logger.info("资源清理完成")
        
if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)