# -*- coding: utf-8 -*-
"""
知乎爬虫数据模型
"""
import scrapy
from itemadapter import ItemAdapter


class ZhihuContentItem(scrapy.Item):
    """知乎内容（回答、文章、视频）"""
    content_id = scrapy.Field()
    content_type = scrapy.Field()  # article | answer | zvideo
    content_text = scrapy.Field()
    content_url = scrapy.Field()
    question_id = scrapy.Field()  # 仅回答类型有值
    title = scrapy.Field()
    desc = scrapy.Field()
    created_time = scrapy.Field()
    updated_time = scrapy.Field()
    voteup_count = scrapy.Field()
    comment_count = scrapy.Field()
    source_keyword = scrapy.Field()  # 来源关键词（creator/detail模式为空）
    
    # 作者信息
    user_id = scrapy.Field()
    user_link = scrapy.Field()
    user_nickname = scrapy.Field()
    user_avatar = scrapy.Field()
    user_url_token = scrapy.Field()
    last_modify_ts = scrapy.Field()  # 最后修改时间戳


class ZhihuCommentItem(scrapy.Item):
    """知乎评论"""
    comment_id = scrapy.Field()
    parent_comment_id = scrapy.Field()
    content = scrapy.Field()
    publish_time = scrapy.Field()
    ip_location = scrapy.Field()
    sub_comment_count = scrapy.Field()
    like_count = scrapy.Field()
    dislike_count = scrapy.Field()
    content_id = scrapy.Field()
    content_type = scrapy.Field()
    
    # 评论者信息
    user_id = scrapy.Field()
    user_link = scrapy.Field()
    user_nickname = scrapy.Field()
    user_avatar = scrapy.Field()
    user_url_token = scrapy.Field()


class ZhihuCreatorItem(scrapy.Item):
    """知乎创作者"""
    user_id = scrapy.Field()
    user_link = scrapy.Field()
    user_nickname = scrapy.Field()
    user_avatar = scrapy.Field()
    url_token = scrapy.Field()
    gender = scrapy.Field()
    ip_location = scrapy.Field()
    follows = scrapy.Field()
    fans = scrapy.Field()
    anwser_count = scrapy.Field()
    video_count = scrapy.Field()
    question_count = scrapy.Field()
    article_count = scrapy.Field()
    column_count = scrapy.Field()
    get_voteup_count = scrapy.Field()
    last_modify_ts = scrapy.Field()  # 最后修改时间戳

