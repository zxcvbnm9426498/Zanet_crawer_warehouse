# -*- coding: utf-8 -*-
"""
Scrapy settings for scrapy_zhihu project
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BOT_NAME = 'scrapy_zhihu'

SPIDER_MODULES = ['scrapy_zhihu.spiders']
NEWSPIDER_MODULE = 'scrapy_zhihu.spiders'

# 遵守robots.txt
ROBOTSTXT_OBEY = False

# 并发设置
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# 下载延迟
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

# 自动限流
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# 请求头
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'

# 默认请求头
DEFAULT_REQUEST_HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.zhihu.com/',
    'Origin': 'https://www.zhihu.com',
    'Priority': 'u=1, i',
    'x-api-version': '3.0.91',
    'x-app-za': 'OS=Web',
    'x-requested-with': 'fetch',
    'x-zse-93': '101_3_3.0',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
}

# 中间件
DOWNLOADER_MIDDLEWARES = {
    'scrapy_zhihu.middlewares.ZhihuSignMiddleware': 543,
    'scrapy_zhihu.middlewares.ZhihuCookieMiddleware': 544,
}

# Pipeline
ITEM_PIPELINES = {
    'scrapy_zhihu.pipelines.ZhihuPipeline': 300,
}

# 日志级别
LOG_LEVEL = 'INFO'

# 扩展
EXTENSIONS = {
    'scrapy.extensions.telnet.TelnetConsole': None,
}

# 重试设置
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# HTTP错误处理（允许403和404，以便spider处理）
HTTPERROR_ALLOWED_CODES = [403, 404]  # 允许403和404，不忽略，让spider处理

# Cookie设置
COOKIES_ENABLED = True

# 下载超时
DOWNLOAD_TIMEOUT = 30

