# -*- coding: utf-8 -*-
"""
工具函数
"""
import re
from typing import Dict


def extract_text_from_html(html: str) -> str:
    """从HTML中提取纯文本，移除所有标签"""
    if not html:
        return ""
    # 移除script和style元素
    clean_html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL)
    # 移除所有其他标签
    clean_text = re.sub(r'<[^>]+>', '', clean_html).strip()
    return clean_text


def convert_str_cookie_to_dict(cookie_str: str) -> Dict[str, str]:
    """将Cookie字符串转换为字典"""
    cookie_dict: Dict[str, str] = {}
    if not cookie_str:
        return cookie_dict
    for cookie in cookie_str.split(";"):
        cookie = cookie.strip()
        if not cookie:
            continue
        cookie_list = cookie.split("=", 1)
        if len(cookie_list) != 2:
            continue
        cookie_dict[cookie_list[0]] = cookie_list[1]
    return cookie_dict


def judge_zhihu_url(url: str) -> str:
    """判断知乎URL类型"""
    if "/question/" in url and "/answer/" in url:
        return "answer"
    elif "/p/" in url or "/zhuanlan.zhihu.com/p/" in url:
        return "article"
    elif "/zvideo/" in url:
        return "zvideo"
    else:
        return "unknown"

