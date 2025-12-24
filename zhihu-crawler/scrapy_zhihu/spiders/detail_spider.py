# -*- coding: utf-8 -*-
"""
详情模式爬虫 - 爬取指定内容的详情和评论
"""
import sys
import os
import json
from urllib.parse import urlparse

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import scrapy
from scrapy_zhihu.items import ZhihuContentItem, ZhihuCommentItem
from zhihu_core.extractor import ZhihuExtractor
from zhihu_core.utils import judge_zhihu_url
from zhihu_core.constants import ZHIHU_URL, ZHIHU_ZHUANLAN_URL
from config import zhihu_config


class DetailSpider(scrapy.Spider):
    """详情模式爬虫"""
    
    name = 'detail'
    allowed_domains = ['zhihu.com', 'zhuanlan.zhihu.com']
    
    def __init__(self, *args, **kwargs):
        super(DetailSpider, self).__init__(*args, **kwargs)
        self.extractor = ZhihuExtractor()
        self.enable_comments = zhihu_config.ENABLE_GET_COMMENTS
        self.enable_sub_comments = zhihu_config.ENABLE_GET_SUB_COMMENTS
    
    def start_requests(self):
        """生成初始请求"""
        for url in zhihu_config.ZHIHU_SPECIFIED_ID_LIST:
            # 移除查询参数
            url = url.split("?")[0]
            yield scrapy.Request(url=url, callback=self.parse_content)
    
    def parse_content(self, response):
        """解析内容详情"""
        url = response.url
        note_type = judge_zhihu_url(url)
        
        if note_type == "answer":
            # 解析回答
            question_id = url.split("/")[-3]
            answer_id = url.split("/")[-1]
            yield scrapy.Request(
                url=f"{ZHIHU_URL}/api/v4/questions/{question_id}/answers/{answer_id}",
                callback=self.parse_answer,
                meta={'question_id': question_id, 'answer_id': answer_id}
            )
        elif note_type == "article":
            # 解析文章
            article_id = url.split("/")[-1]
            yield scrapy.Request(
                url=f"{ZHIHU_ZHUANLAN_URL}/api/posts/{article_id}",
                callback=self.parse_article,
                meta={'article_id': article_id}
            )
        elif note_type == "zvideo":
            # 解析视频
            video_id = url.split("/")[-1]
            yield scrapy.Request(
                url=f"{ZHIHU_URL}/api/v4/zvideos/{video_id}",
                callback=self.parse_video,
                meta={'video_id': video_id}
            )
    
    def parse_answer(self, response):
        """解析回答"""
        try:
            data = json.loads(response.text)
            answer_data = data.get('data', {})
            
            # 提取回答内容
            content_dict = self.extractor.extract_answer_content(answer_data)
            item = ZhihuContentItem(**content_dict)
            yield item
            
            # 如果启用评论，爬取评论
            if self.enable_comments:
                content_id = content_dict['content_id']
                yield scrapy.Request(
                    url=f"{ZHIHU_URL}/api/v4/comment_v5/answers/{content_id}/root_comment",
                    callback=self.parse_comments,
                    meta={'content_id': content_id, 'content_type': 'answer'}
                )
        except Exception as e:
            self.logger.error(f"解析回答失败: {e}")
    
    def parse_article(self, response):
        """解析文章"""
        try:
            data = json.loads(response.text)
            
            # 提取文章内容
            content_dict = self.extractor.extract_article_content(data)
            item = ZhihuContentItem(**content_dict)
            yield item
            
            # 如果启用评论，爬取评论
            if self.enable_comments:
                content_id = content_dict['content_id']
                yield scrapy.Request(
                    url=f"{ZHIHU_URL}/api/v4/comment_v5/articles/{content_id}/root_comment",
                    callback=self.parse_comments,
                    meta={'content_id': content_id, 'content_type': 'article'}
                )
        except Exception as e:
            self.logger.error(f"解析文章失败: {e}")
    
    def parse_video(self, response):
        """解析视频"""
        try:
            data = json.loads(response.text)
            video_data = data.get('data', {})
            
            # 提取视频内容
            content_dict = self.extractor.extract_video_content(video_data)
            item = ZhihuContentItem(**content_dict)
            yield item
            
            # 如果启用评论，爬取评论
            if self.enable_comments:
                content_id = content_dict['content_id']
                yield scrapy.Request(
                    url=f"{ZHIHU_URL}/api/v4/comment_v5/zvideos/{content_id}/root_comment",
                    callback=self.parse_comments,
                    meta={'content_id': content_id, 'content_type': 'zvideo'}
                )
        except Exception as e:
            self.logger.error(f"解析视频失败: {e}")
    
    def parse_comments(self, response):
        """解析评论"""
        try:
            data = json.loads(response.text)
            comments_data = data.get('data', [])
            content_id = response.meta['content_id']
            content_type = response.meta['content_type']
            
            # 提取评论
            for comment_data in comments_data:
                if comment_data.get('type') == 'comment':
                    comment_dict = self.extractor.extract_comment(
                        comment_data, content_id, content_type
                    )
                    item = ZhihuCommentItem(**comment_dict)
                    yield item
                    
                    # 如果启用二级评论且有子评论
                    if self.enable_sub_comments and comment_dict.get('sub_comment_count', 0) > 0:
                        comment_id = comment_dict['comment_id']
                        yield scrapy.Request(
                            url=f"{ZHIHU_URL}/api/v4/comment_v5/comment/{comment_id}/child_comment",
                            callback=self.parse_sub_comments,
                            meta={'content_id': content_id, 'content_type': content_type}
                        )
            
            # 检查是否有下一页
            paging = data.get('paging', {})
            if not paging.get('is_end', True):
                next_url = paging.get('next')
                if next_url:
                    yield scrapy.Request(url=next_url, callback=self.parse_comments, meta=response.meta)
        except Exception as e:
            self.logger.error(f"解析评论失败: {e}")
    
    def parse_sub_comments(self, response):
        """解析二级评论"""
        try:
            data = json.loads(response.text)
            comments_data = data.get('data', [])
            content_id = response.meta['content_id']
            content_type = response.meta['content_type']
            
            for comment_data in comments_data:
                if comment_data.get('type') == 'comment':
                    comment_dict = self.extractor.extract_comment(
                        comment_data, content_id, content_type
                    )
                    item = ZhihuCommentItem(**comment_dict)
                    yield item
            
            # 检查是否有下一页
            paging = data.get('paging', {})
            if not paging.get('is_end', True):
                next_url = paging.get('next')
                if next_url:
                    yield scrapy.Request(url=next_url, callback=self.parse_sub_comments, meta=response.meta)
        except Exception as e:
            self.logger.error(f"解析二级评论失败: {e}")

