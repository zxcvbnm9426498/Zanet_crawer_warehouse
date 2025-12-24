# -*- coding: utf-8 -*-
"""
Scrapy中间件
"""
import sys
import os
from urllib.parse import urlparse, urlencode

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapy import signals
from scrapy.http import Request
from zhihu_core.sign import sign
from zhihu_core.utils import convert_str_cookie_to_dict
from config import zhihu_config


class ZhihuCookieMiddleware:
    """Cookie中间件"""
    
    def __init__(self):
        self.cookies = convert_str_cookie_to_dict(zhihu_config.COOKIES)
        self.cookie_str = zhihu_config.COOKIES
        if not self.cookie_str:
            import warnings
            warnings.warn("Cookie未配置！请在config/zhihu_config.py中设置COOKIES")
    
    def process_request(self, request, spider):
        """处理请求，添加Cookie"""
        if self.cookie_str:
            request.headers['Cookie'] = self.cookie_str
            # 同时设置cookies参数（Scrapy会自动处理）
            request.cookies = self.cookies
        else:
            spider.logger.warning("Cookie未配置，请求可能被拒绝")
        return None


class ZhihuSignMiddleware:
    """知乎API签名中间件"""
    
    def __init__(self):
        self.cookies = convert_str_cookie_to_dict(zhihu_config.COOKIES)
        self.cookie_str = zhihu_config.COOKIES
    
    def process_request(self, request, spider):
        """处理请求，添加签名"""
        # 只对API请求进行签名
        if '/api/v4/' in request.url or '/api/v5/' in request.url:
            # 签名需要使用相对路径（不包含域名）
            parsed = urlparse(request.url)
            # 构建相对路径：路径 + 查询参数
            relative_path = parsed.path
            if parsed.query:
                relative_path += '?' + parsed.query
            
            # 获取签名
            try:
                if not self.cookie_str:
                    spider.logger.warning(f"[ZhihuSignMiddleware] Cookie为空，无法签名: {request.url}")
                    return None
                
                sign_res = sign(relative_path, self.cookie_str)
                # 添加签名到请求头
                request.headers['x-zst-81'] = sign_res.get('x-zst-81', '')
                request.headers['x-zse-96'] = sign_res.get('x-zse-96', '')
                spider.logger.debug(f"[ZhihuSignMiddleware] 已为请求添加签名: {relative_path[:100]}")
            except Exception as e:
                spider.logger.error(f"[ZhihuSignMiddleware] 签名失败: {e}, URL: {relative_path[:100]}")
        
        return None

