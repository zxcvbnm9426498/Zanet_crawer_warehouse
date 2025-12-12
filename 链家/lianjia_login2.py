from playwright.sync_api import sync_playwright
import os
import time
import csv
import requests
import json
from datetime import datetime

# 配置
CITIES_DISTRICTS_FILE = "cities_districts.json"  # 城市区域配置文件
STATE_FILE = "lianjia_login_state.json"
CSV_FILE = "lianjia_rental_data.csv"
STEALTH_JS_FILE = "stealth.min.js"  # 反检测脚本文件

# 新的配置参数
TARGET_CITY = "guangzhou"  # 目标城市: hangzhou, shenzhen, guangzhou, shanghai, beijing
MAX_PAGES_PER_DISTRICT = 40  # 每个区域最大爬取页数
MAX_TOTAL_DATA = 8000  # 总目标数据量（条）
SKIP_EXISTING_DATA = True  # 是否跳过已存在的数据（避免重复爬取）

# 动态设置的变量（将在运行时根据城市设置）
TARGET_URL = ""
CITY_NAME = ""
CITY_DOMAIN = ""

# 代理配置
PROXY_API_URL = "https://dps.kdlapi.com/api/getdps/?secret_id=ovxf56iu4wjafyjugfky&signature=9vma9lh5k4mifmwyj7g6c4y366ri7585&num=1&sep=1"
PROXY_USERNAME = "d4184658806"
PROXY_PASSWORD = "fps11c0w"
USE_PROXY = False  # 是否使用代理，设置为 False 可禁用代理
MAX_RETRY = 3  # 最大重试次数
RETRY_DELAY = 2  # 重试延迟（秒）

def load_city_config(city_code):
    """加载城市配置"""
    try:
        if not os.path.exists(CITIES_DISTRICTS_FILE):
            print(f"[配置] ✗ 未找到城市配置文件: {CITIES_DISTRICTS_FILE}")
            return None, None, []

        with open(CITIES_DISTRICTS_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)

        if city_code not in config['cities']:
            print(f"[配置] ✗ 未找到城市配置: {city_code}")
            print(f"[配置] 可用城市: {list(config['cities'].keys())}")
            return None, None, []

        city_info = config['cities'][city_code]
        city_name = city_info['name']
        city_domain = city_info['domain']
        districts = city_info['districts']

        # 过滤出选中的区域（排除"不限"）
        selected_districts = [d for d in districts if d.get('selected', False) and d['id'] != '0']

        print(f"[配置] ✓ 已加载城市配置: {city_name} ({city_domain})")
        print(f"[配置] ✓ 选中的区域数量: {len(selected_districts)}")

        return city_name, city_domain, selected_districts

    except Exception as e:
        print(f"[配置] ✗ 加载城市配置时发生错误: {str(e)}")
        return None, None, []

def load_existing_data():
    """加载已存在的数据，用于去重"""
    try:
        if not os.path.exists(CSV_FILE):
            return set()

        existing_data = set()
        with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 使用房源编码作为唯一标识
                if row.get('房源编码'):
                    existing_data.add(row['房源编码'])

        print(f"[数据检查] 已存在 {len(existing_data)} 条数据记录")
        return existing_data

    except Exception as e:
        print(f"[数据检查] ⚠ 读取已有数据时发生错误: {str(e)}")
        return set()

def is_new_data(house_code, existing_data):
    """检查是否为新数据"""
    if not SKIP_EXISTING_DATA:
        return True

    return house_code not in existing_data

def load_stealth_script():
    """加载反检测脚本"""
    try:
        if os.path.exists(STEALTH_JS_FILE):
            with open(STEALTH_JS_FILE, 'r', encoding='utf-8') as f:
                script_content = f.read()
            print(f"[反检测] ✓ 已加载反检测脚本: {STEALTH_JS_FILE}")
            return script_content
        else:
            print(f"[反检测] ⚠ 未找到反检测脚本文件: {STEALTH_JS_FILE}")
            return None
    except Exception as e:
        print(f"[反检测] ✗ 加载反检测脚本时发生错误: {str(e)}")
        return None

def get_proxy():
    """获取代理IP"""
    if not USE_PROXY:
        return None
    
    try:
        print("[代理] 正在获取代理IP...")
        response = requests.get(PROXY_API_URL, timeout=10)
        if response.status_code == 200:
            proxy_ip = response.text.strip()
            print(f"[代理] ✓ 获取到代理IP: {proxy_ip}")
            
            # 构建代理配置
            proxy_config = {
                "server": f"http://{proxy_ip}",
                "username": PROXY_USERNAME,
                "password": PROXY_PASSWORD
            }
            return proxy_config
        else:
            print(f"[代理] ✗ 获取代理IP失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"[代理] ✗ 获取代理IP时发生错误: {str(e)}")
        return None

def goto_with_retry(page, url, max_retry=MAX_RETRY, retry_delay=RETRY_DELAY):
    """带重试的页面访问函数"""
    for attempt in range(1, max_retry + 1):
        try:
            print(f"[页面访问] 尝试访问页面 (第 {attempt}/{max_retry} 次)...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"[页面访问] ✓ 成功访问页面: {url}")
            return True
        except Exception as e:
            error_msg = str(e)
            print(f"[页面访问] ✗ 第 {attempt} 次访问失败: {error_msg}")
            
            # 如果是超时错误且还有重试机会
            if attempt < max_retry:
                print(f"[页面访问] 等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"[页面访问] ✗ 已达到最大重试次数 ({max_retry})，访问失败")
                return False
    
    return False

def check_and_wait_captcha(page):
    """检测人机验证并等待用户手动完成"""
    try:
        print("[验证检测] 检测是否有人机验证...")
        time.sleep(2)  # 等待页面完全加载
        
        # 检测验证页面的多种特征
        captcha_indicators = [
            page.locator('#captcha'),
            page.locator('.geetest_captcha'),
            page.locator('text=人机验证'),
            page.locator('text=点击按钮开始验证')
        ]
        
        has_captcha = False
        for indicator in captcha_indicators:
            try:
                if indicator.count() > 0:
                    try:
                        indicator.first.wait_for(state="visible", timeout=2000)
                        has_captcha = True
                        break
                    except:
                        pass
            except:
                continue
        
        # 也可以通过页面标题或URL判断
        page_title = page.title()
        page_url = page.url
        
        if 'captcha' in page_url.lower() or '验证' in page_title:
            has_captcha = True
        
        if has_captcha:
            print("=" * 60)
            print("[验证检测] ⚠ 检测到人机验证页面！")
            print("[验证检测] 请在浏览器中完成人机验证，完成后将自动继续")
            print("=" * 60)
            
            # 等待用户完成验证
            # 通过检测验证元素消失或页面URL变化来判断验证是否完成
            max_wait_time = 300  # 最多等待5分钟
            check_interval = 2  # 每2秒检查一次
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                time.sleep(check_interval)
                elapsed_time += check_interval
                
                # 检查验证是否完成（验证元素消失或页面跳转）
                try:
                    # 检查验证元素是否还存在
                    captcha_exists = False
                    for indicator in captcha_indicators:
                        try:
                            if indicator.count() > 0:
                                try:
                                    indicator.first.wait_for(state="visible", timeout=1000)
                                    captcha_exists = True
                                    break
                                except:
                                    pass
                        except:
                            continue
                    
                    # 如果验证元素不存在，可能验证已完成
                    if not captcha_exists:
                        # 再检查一下页面URL是否变化（可能已跳转到目标页面）
                        current_url = page.url
                        # 检查是否跳转到目标页面或租房相关页面
                        if 'zufang' in current_url.lower() or 'lianjia.com' in current_url.lower():
                            # 确保不是验证页面
                            if 'captcha' not in current_url.lower():
                                print("[验证检测] ✓ 检测到验证已完成，页面已跳转")
                                time.sleep(1)  # 等待页面稳定
                                return True
                    
                    # 每10秒提示一次
                    if elapsed_time % 10 == 0:
                        remaining = max_wait_time - elapsed_time
                        print(f"[验证检测] 等待中... (剩余约 {remaining} 秒)")
                        
                except Exception as check_error:
                    # 如果检查出错，可能页面已变化，认为验证完成
                    print(f"[验证检测] 检测到页面变化，可能验证已完成")
                    time.sleep(1)
                    return True
            
            # 超时后直接返回
            print(f"[验证检测] ⚠ 等待超时 ({max_wait_time} 秒)，仍检测到验证，继续执行后续逻辑")
            return False
        else:
            print("[验证检测] ✓ 未检测到人机验证")
            return True
            
    except Exception as e:
        print(f"[验证检测] ⚠ 检测验证时发生错误: {str(e)}")
        print("[验证检测] 继续执行...")
        return True

def wait_for_login_complete(page, timeout=30):
    """等待登录请求完成"""
    try:
        print("[登录等待] 等待登录请求完成...")
        
        # 记录初始URL
        initial_url = page.url
        print(f"[登录等待] 初始URL: {initial_url}")
        
        # 监听网络请求，等待登录相关的请求完成
        login_keywords = ['login', 'checklogin', 'auth', 'passport', 'user', 'session']
        
        # 设置请求和响应监听器
        login_requests = []
        login_responses = []
        
        def on_request(request):
            url = request.url.lower()
            for keyword in login_keywords:
                if keyword in url and 'api' in url:
                    if request not in login_requests:
                        login_requests.append(request)
                        print(f"[登录等待] 检测到登录请求: {url}")
        
        def on_response(response):
            url = response.url.lower()
            for keyword in login_keywords:
                if keyword in url and 'api' in url:
                    if response not in login_responses:
                        login_responses.append(response)
                        status = response.status
                        print(f"[登录等待] 登录响应完成: {url}, 状态码: {status}")
        
        page.on("request", on_request)
        page.on("response", on_response)
        
        # 等待一段时间，让登录请求完成
        start_time = time.time()
        url_changed = False
        
        while time.time() - start_time < timeout:
            # 检查URL是否变化（登录成功通常会跳转）
            current_url = page.url
            if current_url != initial_url:
                if not url_changed:
                    print(f"[登录等待] ✓ 检测到页面跳转: {current_url}")
                    url_changed = True
            
            # 检查是否有登录请求且已收到响应
            if len(login_requests) > 0:
                # 等待所有登录请求都有响应
                if len(login_responses) >= len(login_requests):
                    print("[登录等待] ✓ 所有登录请求已完成")
                    # 等待页面稳定
                    time.sleep(3)  # 增加等待时间确保状态更新
                    return True
            
            time.sleep(0.5)
        
        # 如果URL变化了，说明可能登录成功
        if url_changed:
            print("[登录等待] ✓ 检测到页面跳转，登录可能已完成")
            time.sleep(3)
            return True
        
        # 如果没有检测到登录请求，等待网络空闲
        print("[登录等待] 未检测到明确的登录请求，等待网络空闲...")
        try:
            page.wait_for_load_state("networkidle", timeout=10)
            print("[登录等待] ✓ 网络已空闲")
            time.sleep(3)  # 额外等待确保状态更新
            return True
        except:
            print("[登录等待] ⚠ 等待网络空闲超时，但继续执行...")
            time.sleep(3)
            return True
            
    except Exception as e:
        print(f"[登录等待] ⚠ 等待登录完成时发生错误: {str(e)}")
        print("[登录等待] 继续执行...")
        time.sleep(3)  # 即使出错也等待一下
        return True

def close_popup(page):
    print("[弹窗处理] 开始处理弹窗关闭操作...")
    try:
        # 不等待 load 状态，直接尝试关闭弹窗（避免超时卡住）
        print("[弹窗处理] 等待页面基本加载完成...")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
        except:
            print("[弹窗处理] ⚠ 等待页面加载超时，继续尝试关闭弹窗...")
        
        print("[弹窗处理] 等待弹窗渲染完成...")
        time.sleep(1)  # 减少等待时间
        
        # 尝试多种选择器
        selectors = [
            ".mask-close",
            '[data-el="guaranteePopupClose"]',
            'img[data-el="guaranteePopupClose"]',
            ".guarantee-popup-close"
        ]
        
        closed = False
        for selector in selectors:
            try:
                print(f"[弹窗处理] 尝试选择器: {selector}")
                close_button = page.locator(selector)
                count = close_button.count()
                
                if count > 0:
                    print(f"[弹窗处理] 找到 {count} 个关闭按钮元素")
                    
                    # 方法1: 尝试正常点击
                    try:
                        close_button.first.wait_for(state="visible", timeout=3000)
                        print("[弹窗处理] 按钮可见，尝试点击...")
                        close_button.first.click()
                        print("[弹窗处理] ✓ 点击成功")
                        closed = True
                        break
                    except:
                        # 方法2: 尝试强制点击
                        try:
                            print("[弹窗处理] 按钮不可见，尝试强制点击...")
                            close_button.first.click(force=True, timeout=3000)
                            print("[弹窗处理] ✓ 强制点击成功")
                            closed = True
                            break
                        except:
                            # 方法3: 使用 JavaScript 直接点击
                            try:
                                print("[弹窗处理] 尝试使用 JavaScript 点击...")
                                # 转义选择器中的特殊字符
                                escaped_selector = selector.replace("'", "\\'")
                                result = page.evaluate(f"""
                                    (function() {{
                                        const btn = document.querySelector('{escaped_selector}');
                                        if (btn) {{
                                            btn.click();
                                            return true;
                                        }}
                                        return false;
                                    }})()
                                """)
                                if result:
                                    print("[弹窗处理] ✓ JavaScript 点击成功")
                                    closed = True
                                    break
                                else:
                                    print("[弹窗处理] JavaScript 未找到元素")
                            except Exception as js_error:
                                print(f"[弹窗处理] JavaScript 点击失败: {str(js_error)}")
                                continue
                else:
                    print(f"[弹窗处理] 选择器 {selector} 未找到元素")
            except Exception as selector_error:
                print(f"[弹窗处理] 选择器 {selector} 出错: {str(selector_error)}")
                continue
        
        if closed:
            time.sleep(0.5)
            print("[弹窗处理] ✓ 弹窗关闭操作完成")
        else:
            print("[弹窗处理] ⚠ 所有方法都失败，弹窗可能不存在或已关闭")
            
    except Exception as e:
        print(f"[弹窗处理] ✗ 关闭弹窗时发生错误: {str(e)}")
        print(f"[弹窗处理] ✗ 错误类型: {type(e).__name__}")
        # 即使出错也继续执行，不阻塞

def parse_rental_data(page, district_name="", existing_data=None):
    """解析页面中的租房数据"""
    print("[数据解析] 开始解析页面数据...")
    rental_data = []

    if existing_data is None:
        existing_data = set()

    try:
        # 等待列表项加载
        print("[数据解析] 等待租房列表加载...")
        page.wait_for_selector('.content__list--item', timeout=10000)
        time.sleep(1)  # 额外等待确保内容渲染完成

        # 获取所有租房列表项
        items = page.locator('.content__list--item').all()
        print(f"[数据解析] 找到 {len(items)} 个租房项目")

        for idx, item in enumerate(items, 1):
            try:
                # 提取标题和链接
                title_elem = item.locator('.content__list--item--title a')
                title = title_elem.inner_text().strip() if title_elem.count() > 0 else ""
                link = title_elem.get_attribute('href') if title_elem.count() > 0 else ""
                if link and not link.startswith('http'):
                    # 使用当前城市的域名
                    link = f"https://{CITY_DOMAIN}{link}"
                
                # 提取描述信息（区域、面积、朝向、房间数）
                des_elem = item.locator('.content__list--item--des')
                des_text = des_elem.inner_text().strip() if des_elem.count() > 0 else ""
                
                # 解析描述信息
                area_info = ""
                size = ""
                orientation = ""
                room_info = ""
                
                if des_text:
                    parts = des_text.split('/')
                    if len(parts) >= 1:
                        area_info = parts[0].strip()
                    if len(parts) >= 2:
                        size = parts[1].strip()
                    if len(parts) >= 3:
                        orientation = parts[2].strip()
                    if len(parts) >= 4:
                        room_info = parts[3].strip()
                
                # 从区域信息中提取区域分类（第一个"-"之前的部分）
                area_category = ""
                if area_info:
                    if '-' in area_info:
                        area_category = area_info.split('-')[0].strip()
                    else:
                        area_category = area_info  # 如果没有"-"，则使用整个区域信息
                
                # 提取价格
                price_elem = item.locator('.content__list--item-price em')
                price = price_elem.inner_text().strip() if price_elem.count() > 0 else ""
                
                # 提取标签
                tags = []
                tag_elems = item.locator('.content__item__tag--gov_certification, .content__item__tag--decoration')
                for tag_elem in tag_elems.all():
                    tag_text = tag_elem.inner_text().strip()
                    if tag_text:
                        tags.append(tag_text)
                tags_str = " | ".join(tags) if tags else ""
                
                # 提取品牌
                brand_elem = item.locator('.brand')
                brand = brand_elem.inner_text().strip() if brand_elem.count() > 0 else ""
                
                # 提取图片链接
                img_elem = item.locator('.content__list--item--aside img')
                img_url = img_elem.get_attribute('src') if img_elem.count() > 0 else ""
                if not img_url:
                    img_url = img_elem.get_attribute('data-src') if img_elem.count() > 0 else ""
                
                # 提取house_code
                house_code = item.get_attribute('data-house_code') or ""

                # 检查是否为新数据
                if not is_new_data(house_code, existing_data):
                    print(f"[数据解析] - 跳过重复数据: {title[:30]}... (房源编码: {house_code})")
                    continue

                # 构建数据字典
                data_item = {
                    '序号': idx,
                    '标题': title,
                    '链接': link,
                    '城市': CITY_NAME,
                    '区域': district_name,
                    '详细区域': area_info,
                    '区域分类': area_category,
                    '面积': size,
                    '朝向': orientation,
                    '房间信息': room_info,
                    '价格(元/月)': price,
                    '标签': tags_str,
                    '品牌': brand,
                    '图片链接': img_url,
                    '房源编码': house_code,
                    '抓取时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                rental_data.append(data_item)
                print(f"[数据解析] ✓ 已解析第 {idx} 项: {title[:30]}... (房源编码: {house_code})")
                
            except Exception as item_error:
                print(f"[数据解析] ⚠ 解析第 {idx} 项时出错: {str(item_error)}")
                continue
        
        print(f"[数据解析] ✓ 共解析 {len(rental_data)} 条数据")
        return rental_data
        
    except Exception as e:
        print(f"[数据解析] ✗ 解析数据时发生错误: {str(e)}")
        print(f"[数据解析] ✗ 错误类型: {type(e).__name__}")
        return []

def get_current_page(page):
    """获取当前页码"""
    try:
        page_num_elem = page.locator('.content__pg a.cur')
        if page_num_elem.count() > 0:
            current_page = page_num_elem.get_attribute('data-page')
            return int(current_page) if current_page else 1
        return 1
    except:
        return 1

def build_next_page_url(page, next_page_num):
    """构造下一页URL，兼容不同城市域名"""
    try:
        pg = page.locator('.content__pg')
        if pg.count() > 0:
            base_path = pg.get_attribute('data-url')  # 例: /zufang/pg{page}/
            if base_path and '{page}' in base_path:
                from urllib.parse import urlsplit, urlunsplit
                parts = urlsplit(page.url)
                path = base_path.replace('{page}', str(next_page_num))
                return urlunsplit((parts.scheme, parts.netloc, path, '', ''))
    except Exception:
        pass

    # 回退：基于当前URL替换 /pgX/
    from urllib.parse import urlsplit, urlunsplit
    import re
    parts = urlsplit(page.url)
    path = parts.path
    if re.search(r'/pg\d+/?', path):
        path = re.sub(r'/pg\d+/?', f'/pg{next_page_num}/', path)
    else:
        if not path.endswith('/'):
            path = f"{path}/"
        path = f"{path}pg{next_page_num}/"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))

def go_to_next_page(page):
    """翻到下一页"""
    try:
        # 翻页前先关闭弹窗，确保按钮可见
        print("[翻页] 翻页前先关闭弹窗，确保按钮可见...")
        close_popup(page)
        time.sleep(1)  # 等待弹窗关闭动画完成
        
        # 获取当前页码
        current_page = get_current_page(page)
        next_page_num = current_page + 1
        next_page_url = build_next_page_url(page, next_page_num)
        
        print(f"[翻页] 当前页码: {current_page}, 目标页码: {next_page_num}")
        print(f"[翻页] 目标URL: {next_page_url}")
        
        # 方法1: 尝试点击下一页按钮
        print("[翻页] 方法1: 尝试点击下一页按钮...")
        next_button = page.locator('.content__pg a.next')
        
        button_clicked = False
        if next_button.count() > 0:
            try:
                # 滚动到底部再定位分页区域，确保按钮渲染可见
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(0.5)
                page.evaluate("document.querySelector('.content__pg')?.scrollIntoView({behavior: 'smooth', block: 'center'})")
                time.sleep(0.5)
                
                # 再次关闭弹窗（滚动可能触发新的弹窗）
                close_popup(page)
                time.sleep(0.5)
                
                # 检查按钮是否可见
                try:
                    next_button.wait_for(state="visible", timeout=3000)
                    print("[翻页] 下一页按钮可见，正在点击...")
                    next_button.click()
                    print("[翻页] ✓ 已点击下一页按钮")
                    button_clicked = True
                except:
                    print("[翻页] ⚠ 下一页按钮不可见或等待超时")
            except Exception as btn_error:
                print(f"[翻页] ⚠ 点击按钮失败: {str(btn_error)}")
        
        # 方法2: 如果按钮点击失败，直接访问URL（带重试）
        if not button_clicked:
            print("[翻页] 方法2: 按钮点击失败，尝试直接访问URL...")
            url_retry_success = False
            for url_retry in range(1, 3):  # 最多重试2次
                try:
                    print(f"[翻页] 尝试直接访问URL (第 {url_retry} 次)...")
                    page.goto(next_page_url, wait_until="domcontentloaded", timeout=30000)
                    print(f"[翻页] ✓ 已直接访问第 {next_page_num} 页")
                    button_clicked = True
                    url_retry_success = True
                    break
                except Exception as url_error:
                    error_msg = str(url_error)
                    print(f"[翻页] ✗ 直接访问URL失败 (第 {url_retry} 次): {error_msg}")
                    
                    # 如果是代理连接失败，等待一下再重试
                    if 'ERR_TUNNEL_CONNECTION_FAILED' in error_msg or 'TUNNEL' in error_msg:
                        print("[翻页] 检测到代理连接失败，等待后重试...")
                        time.sleep(3)
                        if url_retry < 2:
                            continue
                    
                    if url_retry >= 2:
                        print("[翻页] ✗ 直接访问URL重试失败，尝试使用相对路径...")
                        # 尝试使用相对路径
                        try:
                            relative_url = f"/zufang/pg{next_page_num}/#contentList"
                            page.goto(relative_url, wait_until="domcontentloaded", timeout=30000)
                            print(f"[翻页] ✓ 使用相对路径访问成功")
                            button_clicked = True
                            url_retry_success = True
                            break
                        except:
                            pass
            
            if not url_retry_success:
                return False
        
        if button_clicked:
            # 等待页面加载和内容更新
            print("[翻页] 等待新页面加载...")
            try:
                # 等待 URL 变化或内容加载
                page.wait_for_load_state("domcontentloaded", timeout=20000)
                time.sleep(3)  # 增加等待时间，确保内容渲染完成
                
                # 等待列表内容更新（通过检查列表项是否重新加载）
                try:
                    print("[翻页] 等待列表内容更新...")
                    page.wait_for_selector('.content__list--item', timeout=10000)
                    time.sleep(1)
                except:
                    print("[翻页] ⚠ 等待列表内容超时，但继续执行...")
                
            except Exception as load_error:
                print(f"[翻页] ⚠ 等待页面加载时出错: {str(load_error)}")
                time.sleep(2)  # 即使出错也等待一下
            
            # 检测是否因代理/网络导致的错误页（例如 chrome-error）
            current_url_after_load = page.url.lower()
            if "chrome-error" in current_url_after_load or "err_tunnel_connection_failed" in current_url_after_load:
                print("=" * 60)
                print("[翻页] ⚠ 检测到页面加载异常，可能是代理/网络问题")
                print(f"[翻页] 当前URL: {page.url}")
                print("[翻页] 建议：切换/关闭代理，或在浏览器中手动刷新；完成后按 Enter 重试当前页")
                print("=" * 60)
                input()
                try:
                    page.goto(next_page_url, wait_until="domcontentloaded", timeout=20000)
                    time.sleep(2)
                except Exception as reload_err:
                    print(f"[翻页] ⚠ 手动处理后重载仍失败: {str(reload_err)}")
                    return False
            
            # 关闭可能出现的弹窗
            print("[翻页] 翻页后关闭弹窗...")
            close_popup(page)
            
            # 验证是否成功翻页（多次尝试，因为页码可能还没更新）
            print("[翻页] 验证翻页是否成功...")
            for verify_attempt in range(1, 4):  # 最多验证3次
                time.sleep(1)
                new_page = get_current_page(page)
                current_url = page.url
                
                print(f"[翻页] 验证尝试 {verify_attempt}: 当前页码={new_page}, URL={current_url[:80]}...")
                
                # 检查页码或URL是否变化
                if new_page == next_page_num:
                    print(f"[翻页] ✓ 成功翻到第 {new_page} 页")
                    return True
                elif f"pg{next_page_num}" in current_url or f"/pg{next_page_num}/" in current_url:
                    print(f"[翻页] ✓ URL显示已翻到第 {next_page_num} 页")
                    return True
                elif verify_attempt < 3:
                    print(f"[翻页] 页码未更新，等待后重试...")
                    time.sleep(2)
                else:
                    print(f"[翻页] ⚠ 翻页验证失败，当前页码: {new_page}, 期望页码: {next_page_num}")
                    # 即使验证失败，如果URL包含页码，也认为成功
                    if f"pg{next_page_num}" in current_url:
                        print(f"[翻页] 但URL显示已翻页，继续执行...")
                        return True
                    return False
            
            return False
        else:
            print("[翻页] ⚠ 所有翻页方法都失败")
            return False
            
    except Exception as e:
        print(f"[翻页] ✗ 翻页时发生错误: {str(e)}")
        print(f"[翻页] ✗ 错误类型: {type(e).__name__}")
        return False

def save_to_csv(data, filename=CSV_FILE, overwrite=False):
    """将数据保存到CSV文件"""
    if not data:
        print("[CSV保存] ⚠ 没有数据需要保存")
        return

    try:
        # 确定字段名（更新字段顺序）
        fieldnames = ['序号', '城市', '区域', '详细区域', '区域分类', '标题', '链接', '面积',
                     '朝向', '房间信息', '价格(元/月)', '标签', '品牌', '图片链接', '房源编码', '抓取时间']
        
        # 检查文件是否存在，决定是否写入表头
        file_exists = os.path.exists(filename)
        
        # 如果指定覆盖，删除旧文件
        if overwrite and file_exists:
            os.remove(filename)
            file_exists = False
            print(f"[CSV保存] 已删除旧文件，创建新文件: {filename}")
        
        with open(filename, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # 如果文件不存在，写入表头
            if not file_exists:
                writer.writeheader()
                print(f"[CSV保存] 创建新文件: {filename}")
            
            # 写入数据
            writer.writerows(data)
        
        print(f"[CSV保存] ✓ 成功保存 {len(data)} 条数据到 {filename}")
        
    except Exception as e:
        print(f"[CSV保存] ✗ 保存CSV时发生错误: {str(e)}")
        print(f"[CSV保存] ✗ 错误类型: {type(e).__name__}")

def save_login_state():
    print("正在打开页面...")
    print(f"如果需要登录，页面会自动跳转到登录页面")
    print(f"请在浏览器中完成登录，登录完成后脚本会自动保存登录状态")
    print("=" * 50)

    # 加载城市配置以获取初始URL
    city_name, city_domain, districts = load_city_config(TARGET_CITY)
    if city_name:
        initial_url = f"https://{city_domain}/zufang/"
        print(f"[配置] 使用城市 {city_name} 的登录页面: {initial_url}")
    else:
        # 默认使用深圳
        initial_url = "https://sz.lianjia.com/zufang/"
        print("[配置] 使用默认登录页面")

    with sync_playwright() as p:
        # 获取代理配置
        proxy_config = get_proxy()

        # 加载反检测脚本
        stealth_script = load_stealth_script()

        browser = p.chromium.launch(headless=False)

        # 创建浏览器上下文，如果使用代理则配置代理
        if proxy_config:
            print(f"[代理] 使用代理访问: {proxy_config['server']}")
            context = browser.new_context(proxy=proxy_config)
        else:
            context = browser.new_context()

        # 注入反检测脚本
        if stealth_script:
            context.add_init_script(stealth_script)
            print("[反检测] ✓ 已注入反检测脚本到浏览器上下文")

        page = context.new_page()
        try:
            print(f"正在访问: {initial_url}")
            if goto_with_retry(page, initial_url, max_retry=2, retry_delay=RETRY_DELAY):
                print(f"页面已加载，当前 URL: {page.url}")
                # 检测并等待人机验证
                check_and_wait_captcha(page)
                close_popup(page)
                print("请完成登录操作（如果需要）...")
            else:
                print(f"访问页面失败，但浏览器已打开，您可以手动导航到登录页面")
        except Exception as e:
            print(f"访问页面时出现错误: {e}")
            print("浏览器将保持打开，您可以手动导航到登录页面")
        
        print("\n" + "=" * 50)
        print("请在浏览器中完成登录操作")
        print("登录完成后，脚本会自动等待登录请求完成")
        print("=" * 50)
        input("\n登录完成后，请按 Enter 键继续...")
        
        # 等待登录请求完成
        wait_for_login_complete(page, timeout=30)
        
        # 等待页面稳定
        print("[登录等待] 等待页面稳定...")
        time.sleep(2)
        
        storage_state = context.storage_state()

        # 检查保存的状态中是否包含 cookies
        cookies_count = len(storage_state.get('cookies', []))
        print(f"\n[登录状态] 已保存 {cookies_count} 个 cookies")

        # 如果 cookies 数量太少，可能登录不成功
        if cookies_count < 3:
            print("[警告] 保存的 cookies 数量较少，可能登录未成功")
            response = input("是否继续保存状态？(y/n): ").lower()
            if response != 'y':
                print("已取消保存")
                browser.close()
                return

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            import json
            json.dump(storage_state, f, ensure_ascii=False, indent=2)
        print(f"[登录状态] 状态已保存到: {STATE_FILE}")

        # 验证保存的文件
        if os.path.exists(STATE_FILE):
            file_size = os.path.getsize(STATE_FILE)
            print(f"[登录状态] 文件大小: {file_size} 字节")

        browser.close()
        print("浏览器已关闭")
def crawl_multiple_districts():
    """多区域循环爬取数据"""
    # 加载城市配置
    global CITY_NAME, CITY_DOMAIN, TARGET_URL

    city_name, city_domain, districts = load_city_config(TARGET_CITY)
    if not city_name:
        print(f"[错误] 无法加载城市配置: {TARGET_CITY}")
        return

    CITY_NAME = city_name
    CITY_DOMAIN = city_domain

    # 加载已存在数据用于去重
    existing_data = load_existing_data()

    print(f"\n" + "=" * 60)
    print(f"[开始] 准备爬取 {city_name} 的租房数据")
    print(f"[配置] 目标数据量: {MAX_TOTAL_DATA} 条")
    print(f"[配置] 每个区域最多: {MAX_PAGES_PER_DISTRICT} 页")
    print(f"[配置] 选中的区域数量: {len(districts)}")
    print("=" * 60)

    # 检查登录状态
    if not os.path.exists(STATE_FILE):
        print(f"错误: 未找到登录状态文件 {STATE_FILE}")
        print("请先运行 save_login_state() 函数来保存登录状态")
        return

    # 验证登录状态文件
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
        cookies_count = len(state_data.get('cookies', []))
        file_size = os.path.getsize(STATE_FILE)
        print(f"[登录状态] 状态文件大小: {file_size} 字节")
        print(f"[登录状态] 包含 {cookies_count} 个 cookies")

        if cookies_count < 3:
            print("[警告] 登录状态文件中的 cookies 数量较少，可能需要重新登录")
            response = input("是否继续？(y/n): ").lower()
            if response != 'y':
                return
    except Exception as e:
        print(f"[错误] 读取登录状态文件失败: {str(e)}")
        return

    with sync_playwright() as p:
        # 加载反检测脚本
        stealth_script = load_stealth_script()

        browser = p.chromium.launch(headless=False)
        context = None
        page = None
        success = False

        # 建立浏览器上下文
        try:
            # 获取代理配置
            proxy_config = get_proxy()

            if proxy_config:
                print(f"[代理] 使用代理访问: {proxy_config['server']}")
                context = browser.new_context(
                    storage_state=STATE_FILE,
                    proxy=proxy_config
                )
            else:
                print("[代理] 未使用代理访问")
                context = browser.new_context(storage_state=STATE_FILE)

            # 注入反检测脚本
            if stealth_script:
                context.add_init_script(stealth_script)
                print("[反检测] ✓ 已注入反检测脚本到浏览器上下文")

            page = context.new_page()
            success = True

        except Exception as e:
            print(f"[错误] 建立浏览器上下文失败: {str(e)}")
            browser.close()
            return

        if not success:
            print("[错误] 无法建立浏览器连接")
            browser.close()
            return

        # 准备数据收集
        all_rental_data = []
        total_new_data = 0
        saved_once = False
        processed_districts = 0  # 记录实际处理的区域数量

        # 遍历每个区域
        for district_idx, district in enumerate(districts, 1):
            # 检查是否已达到目标数据量
            if total_new_data >= MAX_TOTAL_DATA:
                print(f"\n[完成] 已达到目标数据量 {MAX_TOTAL_DATA} 条，停止爬取")
                break

            district_name = district['name']
            district_url = district['url']

            print(f"\n" + "=" * 60)
            print(f"[区域 {district_idx}/{len(districts)}] 开始处理: {district_name}")
            print(f"[区域] URL: {district_url}")
            print("=" * 60)

            # 访问区域页面
            if not goto_with_retry(page, district_url, max_retry=2, retry_delay=RETRY_DELAY):
                print(f"[区域] ✗ 无法访问区域页面: {district_name}")
                continue

            processed_districts += 1  # 增加已处理区域计数

            print(f"[区域] ✓ 已访问区域页面: {district_name}")
            current_url = page.url

            # 检测是否需要重新登录
            if any(k in current_url.lower() for k in ["login", "clogin"]):
                print("=" * 60)
                print("[警告] 需要重新登录！")
                print(f"[警告] 当前URL: {current_url}")
                print("=" * 60)
                print("请在浏览器中完成登录，登录完成后按 Enter 继续...")
                input()

                # 等待登录完成
                print("[登录] 等待登录完成...")
                wait_for_login_complete(page, timeout=60)

                # 重新保存登录状态
                print("[登录] 更新登录状态文件...")
                storage_state = context.storage_state()
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(storage_state, f, ensure_ascii=False, indent=2)
                print("[登录] 登录状态已更新")

                # 重新访问区域页面
                print(f"[区域] 重新访问区域页面...")
                if not goto_with_retry(page, district_url, max_retry=2, retry_delay=RETRY_DELAY):
                    print(f"[区域] ✗ 重新访问失败，跳过区域: {district_name}")
                    continue

            # 检测并处理验证码
            elif any(k in current_url.lower() for k in ["captcha", "hip.lianjia.com"]):
                print("=" * 60)
                print("[提示] 检测到验证码页面，等待验证...")
                print(f"[提示] 当前URL: {current_url}")
                print("=" * 60)
                check_and_wait_captcha(page)

            # 关闭弹窗
            close_popup(page)

            # 爬取该区域的多页数据
            district_data_count = 0
            for page_num in range(1, MAX_PAGES_PER_DISTRICT + 1):
                # 再次检查数据量
                if total_new_data >= MAX_TOTAL_DATA:
                    print(f"\n[区域] 已达到总目标数据量，停止当前区域的爬取")
                    break

                print(f"\n[区域 {district_name}] === 处理第 {page_num}/{MAX_PAGES_PER_DISTRICT} 页 ===")

                # 如果不是第一页，需要翻页
                if page_num > 1:
                    print(f"[翻页] 准备翻到第 {page_num} 页...")
                    if not go_to_next_page(page):
                        print(f"[翻页] ⚠ 无法翻到第 {page_num} 页，停止当前区域爬取")
                        break

                # 等待页面加载
                time.sleep(2)

                # 处理可能出现的验证码或弹窗
                current_url = page.url
                if any(k in current_url.lower() for k in ["login", "captcha", "clogin"]):
                    print("[翻页] 检测到验证码，等待处理...")
                    check_and_wait_captcha(page)

                close_popup(page)
                time.sleep(1)

                # 解析页面数据
                rental_data = parse_rental_data(page, district_name, existing_data)

                if rental_data:
                    district_data_count += len(rental_data)
                    total_new_data += len(rental_data)

                    print(f"[区域] ✓ 第 {page_num} 页获取 {len(rental_data)} 条新数据")
                    print(f"[区域] 该区域累计: {district_data_count} 条，总计: {total_new_data} 条")

                    # 更新全局序号
                    start_idx = len(all_rental_data)
                    for idx, item in enumerate(rental_data, 1):
                        item['序号'] = start_idx + idx

                    all_rental_data.extend(rental_data)

                    # 添加到已存在数据集，避免重复
                    for item in rental_data:
                        if item.get('房源编码'):
                            existing_data.add(item['房源编码'])

                    # 实时保存数据（避免数据丢失）
                    save_to_csv(rental_data, overwrite=not saved_once)
                    saved_once = True

                    # 如果这一页没有新数据，可能是因为已经爬过了
                    if len(rental_data) == 0:
                        print(f"[区域] 第 {page_num} 页没有新数据，可能已经爬取过，跳过后续页面")
                        break
                else:
                    print(f"[区域] 第 {page_num} 页没有获取到数据")

            print(f"\n[区域] {district_name} 处理完成，共获取 {district_data_count} 条新数据")

            # 区域间稍作休息
            time.sleep(2)

        # 最终总结
        print("\n" + "=" * 60)
        print(f"[完成] 所有区域处理完成！")
        print(f"[统计] 总计获取 {len(all_rental_data)} 条新数据")
        print(f"[统计] 处理了 {processed_districts} 个区域")
        print(f"[文件] 数据已保存到: {CSV_FILE}")
        print("=" * 60)

        # 保存最终完整数据（覆盖模式）
        if all_rental_data:
            save_to_csv(all_rental_data, overwrite=True)

        print("\n浏览器将保持打开状态，您可以查看页面内容")
        print("按 Enter 键关闭浏览器...")
        input()

        try:
            browser.close()
            print("浏览器已关闭")
        except:
            print("关闭浏览器时出现错误，但程序已正常结束")

def load_and_visit_with_state():
    """兼容性函数，调用新的多区域爬取函数"""
    crawl_multiple_districts()
def main():
    #save_login_state()
    print("\n=== 步骤 2: 使用保存的状态访问页面 ===")
    time.sleep(1)
    load_and_visit_with_state()
if __name__ == "__main__":
    main()