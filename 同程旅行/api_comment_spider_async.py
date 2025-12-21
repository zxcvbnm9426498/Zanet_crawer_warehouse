import csv
import json
import os
import random
import threading
import time
from datetime import datetime
import execjs
import requests
API_URL = "https://www.ly.com/tapi/getCommentList"
PROXY_API_URL = ""
PROXY_USERNAME = ""
PROXY_PASSWORD = ""
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_3_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11.6; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15",
]
lock_print = threading.Lock()
def log(msg: str):
    with lock_print:
        print(msg, flush=True)
def ts_to_datetime(ts):
    if not ts:
        return ""
    try:
        if isinstance(ts, str):
            ts = int(ts)
        if ts > 10000000000:
            ts = ts / 1000
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)
def get_proxy():
    try:
        proxy_ip = requests.get(PROXY_API_URL, timeout=10).text.strip()
        if proxy_ip:
            proxies = {
                "http": f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{proxy_ip}/",
                "https": f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{proxy_ip}/",
            }
            log(f"  🌐 获取代理: {proxy_ip}")
            return proxies
    except Exception as e:
        log(f"  ⚠️ 获取代理失败: {e}")
    return None
def get_random_headers(hotel_id: str):
    ua = random.choice(USER_AGENTS)
    platform = '"macOS"' if "Macintosh" in ua else '"Windows"' if "Windows" in ua else '"Android"'
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Referer": f"https://www.ly.com/hotel/hoteldetail?hotelId={hotel_id}&inDate=2025-12-17&outDate=2025-12-18&adultsNumber=1",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": ua,
        "appfrom": "16",
        "lang": "zh-cn",
        "pageName": "hoteldetail",
        "sec-ch-ua": '"Google Chrome";v="120", "Chromium";v="120", "Not A(Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": platform,
        "timeZone": "8",
        "tmapi-client": "tpc",
    }
def load_user_dun_ctx():
    with open("./userDun.js", encoding="utf-8") as f:
        js_code = f.read()
    return execjs.compile(js_code)
def build_params(hotel_id: str, page_index: int, sort_method: str = "latest") -> dict:
    """
    构建请求参数
    :param hotel_id: 酒店ID
    :param page_index: 页码
    :param sort_method: 排序方式，"latest" 为最新排序，"comprehensive" 为综合排序
    """
    # sortingMethod: 0=最新排序, 1=综合排序
    sorting_method = 0 if sort_method == "latest" else 1
    body = {
        "objectId": hotel_id,
        "keyword": "",
        "pageSize": 10,
        "sortingInfo": {"sortingMethod": sorting_method, "sortingDirection": 1},
        "traceToken": "",
        # 之前这里加了 searchFeatures + filterIds=["1"]，相当于做了过滤，只拿到一部分评论
        # 为了和网页默认“全部评论”的数量一致，这里把过滤条件去掉
        "searchFeatures": [],
        "pageIndex": page_index,
    }
    return {"bodyStr": json.dumps(body, ensure_ascii=False)}
def gen_user_dun(ctx, params: dict) -> str:
    query = "&".join([f"{k}={v}" for k, v in params.items()])
    url = f"{API_URL}?{query}"
    return ctx.call("main123", url)
def fetch_page(ctx, hotel_id: str, page_index: int, proxies=None, retry: int = 3, silent: bool = False, sort_method: str = "latest"):
    params = build_params(hotel_id, page_index, sort_method)
    user_dun = gen_user_dun(ctx, params)
    headers = get_random_headers(hotel_id)
    headers["User-Dun"] = user_dun
    for attempt in range(retry):
        try:
            resp = requests.get(
                API_URL,
                headers=headers,
                params=params,
                proxies=proxies,
                timeout=30,
            )
            break
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ProxyError,
            requests.exceptions.ConnectionError,
        ) as e:
            log(f"    ⚠️ 酒店 {hotel_id} 第 {page_index} 页请求失败({e})，重试 {attempt + 2}/{retry}...")
            proxies = get_proxy()
            time.sleep(random.uniform(1, 2))
    else:
        return [], None
    if resp.status_code != 200:
        if not silent:
            log(f"    ❌ 酒店 {hotel_id} 第 {page_index} 页状态码异常: {resp.status_code}")
        return [], None
    try:
        data = resp.json()
    except Exception as e:
        if not silent:
            log(f"    ❌ 酒店 {hotel_id} 第 {page_index} 页 JSON 解析失败: {e}")
        return [], None
    d = data.get("data", {}) or {}
    total = d.get("total") or data.get("total")
    comments = d.get("comments", []) or d.get("commentList", [])
    return comments, total
def scrape_hotel(hotel_id: str, sort_method: str = "latest"):
    hotel_id = hotel_id.strip()
    if not hotel_id:
        return
    sort_name = "最新排序" if sort_method == "latest" else "综合排序"
    log(f"\n===== 开始抓取酒店 {hotel_id} (排序方式: {sort_name}) =====")
    ctx = load_user_dun_ctx()
    proxies = get_proxy()
    comments0, total = fetch_page(ctx, hotel_id, 0, proxies=proxies, sort_method=sort_method)
    if total is None:
        log(f"酒店 {hotel_id} 获取 total 失败，跳过")
        return
    total_pages = (int(total) + 9) // 10
    log(f"酒店 {hotel_id} 总评论数: {total}, 预计页数: {total_pages}")
    os.makedirs("result", exist_ok=True)
    out_path = os.path.join("result", f"{hotel_id}.csv")
    f_csv = open(out_path, "w", newline="", encoding="utf-8-sig")
    writer = csv.writer(f_csv)
    writer.writerow(["酒店ID", "评论ID", "评论内容", "单条评分", "入住时间"])
    total_saved = 0
    for page_index in range(total_pages):
        comments = []
        max_empty_retry = 3
        for empty_attempt in range(max_empty_retry):
            comments, _ = fetch_page(
                ctx,
                hotel_id,
                page_index,
                proxies=proxies,
                sort_method=sort_method,
            )
            if comments:
                break
            log(
                f"    ⚠️ 酒店 {hotel_id} 第 {page_index} 页返回 0 条数据，重试 {empty_attempt + 1}/{max_empty_retry}..."
            )
            time.sleep(random.uniform(0.5, 1.0))
        if not comments:
            log(f"  酒店 {hotel_id} 第 {page_index} 页多次无数据，跳过该页")
            continue
        page_saved = 0
        for c in comments:
            comment_ext = c.get("commentExt") or {}
            order_info = comment_ext.get("order") or {}
            check_in_ts = order_info.get("checkInTime") or c.get("checkInDate") or c.get("date")
            cid = c.get("id") or c.get("commentId") or c.get("cid") or ""
            content = (c.get("content") or c.get("comment") or "").strip()
            score = c.get("commentScore") or c.get("score") or c.get("rating") or ""
            check_in_str = ts_to_datetime(check_in_ts)
            writer.writerow([hotel_id, cid, content, score, check_in_str])
            page_saved += 1
            total_saved += 1
        f_csv.flush()
        log(f"  酒店 {hotel_id} 第 {page_index} 页保存 {page_saved} 条，累计 {total_saved} 条")
        time.sleep(random.uniform(0.2, 0.6))
    f_csv.close()
    log(f"===== 酒店 {hotel_id} 抓取完成，共保存 {total_saved} 条，文件: {out_path} =====")
def main():
    ids_path = "hotel_ids.txt"
    if not os.path.exists(ids_path):
        log(f"未找到 {ids_path}")
        return
    with open(ids_path, encoding="utf-8") as f:
        hotel_ids = [line.strip() for line in f if line.strip()]
    if not hotel_ids:
        log("hotel_ids.txt 中没有有效酒店 ID")
        return
    log("\n请选择排序方式：")
    log("1. 最新排序 (默认)")
    log("2. 综合排序")
    choice = input("请输入选项 (1/2，直接回车默认选择1): ").strip()
    if choice == "2":
        sort_method = "comprehensive"
        sort_name = "综合排序"
    else:
        sort_method = "latest"
        sort_name = "最新排序"
    log(f"\n已选择排序方式: {sort_name}")
    log(f"共读取到 {len(hotel_ids)} 个酒店 ID，开始依次抓取（单线程，降低对代理的压力）...")
    for hid in hotel_ids:
        try:
            scrape_hotel(hid, sort_method=sort_method)
            time.sleep(1.0)
        except Exception as e:
            log(f"酒店 {hid} 抓取异常: {e}")
    log("全部酒店抓取完成。")
if __name__ == "__main__":
    main()