# -*- coding: utf-8 -*-
"""
创作者模式爬虫 - 爬取创作者主页的所有内容
"""
import sys
import os
import json
from urllib.parse import urlencode

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import scrapy
from scrapy_zhihu.items import ZhihuContentItem, ZhihuCommentItem, ZhihuCreatorItem
from zhihu_core.extractor import ZhihuExtractor
from zhihu_core.constants import ZHIHU_URL
from config import zhihu_config


class CreatorSpider(scrapy.Spider):
    """创作者模式爬虫"""
    
    name = 'creator'
    allowed_domains = ['zhihu.com']
    
    def __init__(self, *args, **kwargs):
        super(CreatorSpider, self).__init__(*args, **kwargs)
        self.extractor = ZhihuExtractor()
        self.enable_comments = zhihu_config.ENABLE_GET_COMMENTS
        self.enable_sub_comments = zhihu_config.ENABLE_GET_SUB_COMMENTS
    
    def start_requests(self):
        """生成初始请求"""
        # 检查Cookie配置
        if not zhihu_config.COOKIES:
            self.logger.error("Cookie未配置！请在config/zhihu_config.py中设置COOKIES")
            return
        
        # 先访问搜索页面获取必要的Cookie（参考原项目逻辑）
        yield scrapy.Request(
            url=f"{ZHIHU_URL}/search?q=python&search_source=Guess&utm_content=search_hot&type=content",
            callback=self._after_search_page,
            dont_filter=True
        )
    
    def _after_search_page(self, response):
        """访问搜索页面后，开始爬取创作者"""
        self.logger.info("已访问搜索页面，开始爬取创作者...")
        
        for user_link in zhihu_config.ZHIHU_CREATOR_URL_LIST:
            # 提取用户名（用于后续API请求）
            if "/people/" in user_link:
                parts = user_link.split("/people/")[-1].split("/")
                user_url_token = parts[0] if parts else user_link.split("/")[-1]
            else:
                user_url_token = user_link.split("/")[-1]
            
            # 如果URL已经是完整的知乎URL，直接使用；否则补全
            if user_link.startswith("http"):
                request_url = user_link
            elif user_link.startswith("/"):
                request_url = f"{ZHIHU_URL}{user_link}"
            else:
                request_url = f"{ZHIHU_URL}/people/{user_url_token}"
            
            # 请求创作者主页（使用原始URL，保持路径不变）
            yield scrapy.Request(
                url=request_url,
                callback=self.parse_creator,
                meta={'user_url_token': user_url_token, 'original_url': user_link},
                dont_filter=False
            )
    
    def parse_creator(self, response):
        """解析创作者信息"""
        # 检查响应状态
        if response.status == 403:
            self.logger.error(f"访问被拒绝(403)，请检查Cookie是否有效。URL: {response.url}")
            return
        
        if response.status != 200:
            self.logger.warning(f"响应状态码: {response.status}, URL: {response.url}")
            return
        
        user_url_token = response.meta['user_url_token']
        
        # 提取创作者信息
        creator_dict = self.extractor.extract_creator_from_html(user_url_token, response.text)
        if creator_dict:
            item = ZhihuCreatorItem(**creator_dict)
            yield item
            
            # 使用从HTML提取的url_token（可能更准确）
            actual_url_token = creator_dict.get('url_token') or user_url_token
            self.logger.info(f"使用url_token: {actual_url_token} (原始: {user_url_token})")
            
            # 爬取创作者的回答
            params = {
                "include": "data[*].is_normal,admin_closed_comment,reward_info,is_collapsed,annotation_action,annotation_detail,collapse_reason,collapsed_by,suggest_edit,comment_count,can_comment,content,editable_content,attachment,voteup_count,reshipment_settings,comment_permission,created_time,updated_time,review_info,excerpt,paid_info,reaction_instruction,is_labeled,label_info,relationship.is_authorized,voting,is_author,is_thanked,is_nothelp;data[*].vessay_info;data[*].author.badge[?(type=best_answerer)].topics;data[*].author.vip_info;data[*].question.has_publishing_draft,relationship",
                "offset": 0,
                "limit": 20,
                "order_by": "created"
            }
            url = f"{ZHIHU_URL}/api/v4/members/{actual_url_token}/answers?{urlencode(params)}"
            yield scrapy.Request(
                url=url,
                callback=self.parse_creator_answers,
                meta={'user_url_token': actual_url_token, 'offset': 0},
                dont_filter=True
            )
            
            # 爬取创作者的想法（pins）
            params_pins = {
                "offset": 0,
                "limit": 20,
                "includes": "data[*].upvoted_followees,admin_closed_comment"
            }
            url_pins = f"{ZHIHU_URL}/api/v4/v2/pins/{actual_url_token}/moments?{urlencode(params_pins)}"
            yield scrapy.Request(
                url=url_pins,
                callback=self.parse_creator_pins,
                meta={'user_url_token': actual_url_token, 'offset': 0},
                dont_filter=True
            )
        else:
            self.logger.warning(f"未能提取创作者信息: {user_url_token}")
    
    def parse_creator_answers(self, response):
        """解析创作者的回答列表"""
        # 检查响应状态
        if response.status == 403:
            self.logger.error(f"API请求被拒绝(403): {response.url}")
            self.logger.error(f"响应内容: {response.text[:500]}")
            return
        
        if response.status == 404:
            self.logger.warning(f"用户可能不存在或没有回答(404): {response.url}")
            # 尝试解析响应，看是否有错误信息
            try:
                data = json.loads(response.text)
                error_msg = data.get('error', {}).get('message', '')
                if error_msg:
                    self.logger.warning(f"错误信息: {error_msg}")
            except:
                pass
            return
        
        if response.status != 200:
            self.logger.warning(f"API响应状态码: {response.status}, URL: {response.url}")
            return
        
        try:
            data = json.loads(response.text)
            answers_data = data.get('data', [])
            user_url_token = response.meta['user_url_token']
            offset = response.meta['offset']
            
            self.logger.info(f"成功获取 {len(answers_data)} 条回答数据")
            
            # 提取回答内容
            for answer_data in answers_data:
                content_dict = self.extractor.extract_answer_content(answer_data)
                # 确保source_keyword字段存在（creator模式为空）
                if 'source_keyword' not in content_dict:
                    content_dict['source_keyword'] = ''
                item = ZhihuContentItem(**content_dict)
                yield item
                
                # 如果启用评论，爬取评论
                if self.enable_comments:
                    content_id = content_dict['content_id']
                    params = {
                        "order": "score",
                        "offset": "",
                        "limit": 10
                    }
                    url = f"{ZHIHU_URL}/api/v4/comment_v5/answers/{content_id}/root_comment?{urlencode(params)}"
                    yield scrapy.Request(
                        url=url,
                        callback=self.parse_comments,
                        meta={'content_id': content_id, 'content_type': 'answer'}
                    )
            
            # 检查是否有下一页
            paging = data.get('paging', {})
            if not paging.get('is_end', True):
                offset += 20
                params = {
                    "include": "data[*].is_normal,admin_closed_comment,reward_info,is_collapsed,annotation_action,annotation_detail,collapse_reason,collapsed_by,suggest_edit,comment_count,can_comment,content,editable_content,attachment,voteup_count,reshipment_settings,comment_permission,created_time,updated_time,review_info,excerpt,paid_info,reaction_instruction,is_labeled,label_info,relationship.is_authorized,voting,is_author,is_thanked,is_nothelp;data[*].vessay_info;data[*].author.badge[?(type=best_answerer)].topics;data[*].author.vip_info;data[*].question.has_publishing_draft,relationship",
                    "offset": offset,
                    "limit": 20,
                    "order_by": "created"
                }
                url = f"{ZHIHU_URL}/api/v4/members/{user_url_token}/answers?{urlencode(params)}"
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_creator_answers,
                    meta={'user_url_token': user_url_token, 'offset': offset},
                    dont_filter=True
                )
        except Exception as e:
            self.logger.error(f"解析创作者回答失败: {e}")
    
    def parse_comments(self, response):
        """解析评论"""
        # 检查响应状态
        if response.status == 403:
            self.logger.error(f"评论API请求被拒绝(403): {response.url}")
            return
        
        if response.status != 200:
            self.logger.warning(f"评论API响应状态码: {response.status}, URL: {response.url}")
            return
        
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
                        params = {
                            "order": "sort",
                            "offset": "",
                            "limit": 10
                        }
                        url = f"{ZHIHU_URL}/api/v4/comment_v5/comment/{comment_id}/child_comment?{urlencode(params)}"
                        yield scrapy.Request(
                            url=url,
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
    
    def parse_creator_pins(self, response):
        """解析创作者的想法列表"""
        # 检查响应状态
        if response.status == 403:
            self.logger.error(f"想法API请求被拒绝(403): {response.url}")
            self.logger.error(f"响应内容: {response.text[:500]}")
            return
        
        if response.status == 404:
            self.logger.warning(f"用户可能不存在或没有想法(404): {response.url}")
            # 尝试解析响应，看是否有错误信息
            try:
                data = json.loads(response.text)
                error_msg = data.get('error', {}).get('message', '')
                if error_msg:
                    self.logger.warning(f"错误信息: {error_msg}")
            except:
                pass
            return
        
        if response.status != 200:
            self.logger.warning(f"想法API响应状态码: {response.status}, URL: {response.url}")
            return
        
        try:
            data = json.loads(response.text)
            pins_data = data.get('data', [])
            user_url_token = response.meta['user_url_token']
            offset = response.meta['offset']
            
            self.logger.info(f"成功获取 {len(pins_data)} 条想法数据")
            
            # 提取想法内容
            for pin_data in pins_data:
                if pin_data.get("type") != "pin":
                    continue
                
                content_dict = self.extractor.extract_pin_content(pin_data)
                # 确保source_keyword字段存在（creator模式为空）
                if 'source_keyword' not in content_dict:
                    content_dict['source_keyword'] = ''
                item = ZhihuContentItem(**content_dict)
                yield item
                
                # 如果启用评论，爬取想法的评论
                if self.enable_comments:
                    content_id = content_dict['content_id']
                    params = {
                        "order_by": "score",
                        "offset": "",
                        "limit": 20
                    }
                    url = f"{ZHIHU_URL}/api/v4/comment_v5/pins/{content_id}/root_comment?{urlencode(params)}"
                    yield scrapy.Request(
                        url=url,
                        callback=self.parse_comments,
                        meta={'content_id': content_id, 'content_type': 'pin'}
                    )
            
            # 检查是否有下一页
            paging = data.get('paging', {})
            if not paging.get('is_end', True):
                offset += 20
                params_pins = {
                    "offset": offset,
                    "limit": 20,
                    "includes": "data[*].upvoted_followees,admin_closed_comment"
                }
                url_pins = f"{ZHIHU_URL}/api/v4/v2/pins/{user_url_token}/moments?{urlencode(params_pins)}"
                yield scrapy.Request(
                    url=url_pins,
                    callback=self.parse_creator_pins,
                    meta={'user_url_token': user_url_token, 'offset': offset},
                    dont_filter=True
                )
        except Exception as e:
            self.logger.error(f"解析创作者想法失败: {e}")

