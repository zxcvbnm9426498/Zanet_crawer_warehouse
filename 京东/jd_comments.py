'''
Author: 择安网络
Code function: 
Date: 2025-05-03 11:10:39
FilePath: /爬虫仓/京东/jd_comments.py
LastEditTime: 2025-06-04 09:46:13

功能：
    爬取京东商品信息
    用requests和bs4请求网页解析json获得商品数据

    更新需要cookie

'''
import requests
from bs4 import BeautifulSoup
import csv
import json
import re

url = 'https://re.jd.com/search?keyword=%e4%ba%ac%e4%b8%9c%e5%ae%98%e7%bd%91&keywordid=172887082138&re_dcp=202m0QjIIg==&traffic_source=1004&enc=utf8&bd_vid=PjRkrjmLnWRvnjDkrjRsrHfYn7tkrj0kg17xnH0s&cu=true&utm_source=baidu-search&utm_medium=cpc&utm_campaign=t_262767352_baidusearch&utm_term=172887082138_0_2d35c613672c4f849e2aa68e3b474b84'
headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cache-Control':'max-age=0',
    'Connection': 'keep-alive',
    'Cookie': '',
    'Host':'re.jd.com',
    'Sec-Ch-Ua': '"Chromium";v="9", "Not?A_Brand";v="8"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 SLBrowser/9.0.6.2081 SLBChan/111 SLBVPV/64-bit'
}

try:
    response = requests.get(url,headers=headers)
    response.raise_for_status()
    
    response.encoding = 'UTF-8'
    
    soup = BeautifulSoup(response.text,'html.parser')
    head = soup.find('head')
    script = head.find_all('script')
    script_content = script[2].text.replace("var pageData = ",'').replace(";"[-1],'')
    json_data = json.loads(script_content)
    json_data = json_data['result']
    
    all_data = []
    
    for item in json_data:
        sku_id = item['sku_id'] if 'sku_id' in item else None
        ad_title = item['ad_title'] if 'ad_title' in item else None
        ad_title_text = item['ad_title_text'] if 'ad_title_text' in item else None
        image_url = item['image_url'] if 'image_url' in item else None
        commentnum = item['commentnum'] if 'commentnum' in item else None
        good_count = item['good_count'] if 'good_count' in item else None
        price = item['price'] if 'price' in item else None
        
        all_data.append({
            'sku_id': sku_id,
            'ad_title': ad_title,
            'ad_title_text': ad_title_text,
            'image_url': image_url,
            'commentnum': commentnum,
            'good_count': good_count,
            'price': price
        })
    
    csv_file = 'jd_data.csv'
    csv_headers = ['sku_id', 'ad_title', 'ad_title_text', 'image_url', 'commentnum', 'good_count', 'price']
    
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(all_data)
    
    print(f"数据已成功保存到 {csv_file}，共 {len(all_data)} 条记录")
        
except requests.RequestException as e:
    print(f"请求发生错误: {e}")
except Exception as e:
    print(f"发生其他异常: {e}")
    import traceback
    traceback.print_exc()