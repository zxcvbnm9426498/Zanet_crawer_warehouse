# -*- coding: utf-8 -*-
"""
知乎API签名
"""
import os
import execjs
from typing import Dict

# 全局变量存储编译后的JS
_ZHIHU_SIGN_JS = None


def sign(url: str, cookies: str) -> Dict:
    """
    知乎签名算法
    Args:
        url: 请求URL（包含查询参数）
        cookies: 请求Cookie字符串（必须包含d_c0）
    Returns:
        包含签名信息的字典
    """
    global _ZHIHU_SIGN_JS
    if not _ZHIHU_SIGN_JS:
        js_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "libs", "zhihu.js")
        with open(js_path, mode="r", encoding="utf-8-sig") as f:
            _ZHIHU_SIGN_JS = execjs.compile(f.read())
    
    return _ZHIHU_SIGN_JS.call("get_sign", url, cookies)

