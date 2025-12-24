# -*- coding: utf-8 -*-
"""
知乎爬虫配置
"""

# 指定知乎用户URL列表（创作者模式）
ZHIHU_CREATOR_URL_LIST = [
    "https://www.zhihu.com/people/zhangkangkang",
    # 可以添加更多创作者URL
]

# 指定知乎内容URL列表（详情模式）
ZHIHU_SPECIFIED_ID_LIST = [
    # "https://www.zhihu.com/question/826896610/answer/4885821440",  # 回答
    # "https://zhuanlan.zhihu.com/p/673461588",  # 文章
    # "https://www.zhihu.com/zvideo/1539542068422144000",  # 视频
]

# Cookie配置（用于登录）- 必须配置！
COOKIES = ""


# 登录方式: qrcode | phone | cookie
LOGIN_TYPE = "cookie"

# 是否启用无头模式
HEADLESS = False

# 是否爬取评论
ENABLE_GET_COMMENTS = True

# 是否爬取二级评论
ENABLE_GET_SUB_COMMENTS = False

# 爬取间隔时间（秒）
CRAWLER_MAX_SLEEP_SEC = 2

# 并发数量
MAX_CONCURRENCY_NUM = 1

# 数据保存方式: csv | json | db | sqlite | excel
SAVE_DATA_OPTION = "csv"

# 是否启用代理
ENABLE_IP_PROXY = False

# 代理池数量
IP_PROXY_POOL_COUNT = 5
