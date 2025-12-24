# -*- coding: utf-8 -*-
"""
知乎数据提取器
"""
import json
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from parsel import Selector
from scrapy_zhihu.items import ZhihuContentItem, ZhihuCommentItem, ZhihuCreatorItem
from zhihu_core.constants import ZHIHU_URL, ZHIHU_ZHUANLAN_URL
from zhihu_core.utils import extract_text_from_html


class ZhihuExtractor:
    """知乎数据提取器"""
    
    def __init__(self):
        pass
    
    def extract_creator_from_html(self, user_url_token: str, html_content: str) -> Optional[Dict]:
        """从HTML中提取创作者信息"""
        if not html_content:
            return None
        
        selector = Selector(text=html_content)
        js_init_data = selector.xpath("//script[@id='js-initialData']/text()").get(default="").strip()
        if not js_init_data:
            return None
        
        try:
            js_init_data_dict = json.loads(js_init_data)
            users_info = js_init_data_dict.get("initialState", {}).get("entities", {}).get("users", {})
            if not users_info:
                return None
            
            # 首先尝试使用URL中的token直接查找
            creator_info = users_info.get(user_url_token)
            
            # 如果找不到，尝试遍历所有用户，通过urlToken匹配
            if not creator_info:
                for key, user_info in users_info.items():
                    # 检查urlToken是否匹配
                    if user_info.get("urlToken") == user_url_token:
                        creator_info = user_info
                        break
                    # 检查key是否匹配（可能是不同的格式）
                    if key == user_url_token or key.endswith(f"/{user_url_token}"):
                        creator_info = user_info
                        break
            
            # 如果还是找不到，且只有一个用户，使用该用户
            if not creator_info and len(users_info) == 1:
                creator_info = list(users_info.values())[0]
            
            if not creator_info:
                return None
            
            # 使用实际的urlToken（从HTML中提取的）或使用传入的token
            actual_url_token = creator_info.get("urlToken") or user_url_token
            
            return {
                "user_id": creator_info.get("id"),
                "user_link": f"{ZHIHU_URL}/people/{actual_url_token}",
                "user_nickname": creator_info.get("name"),
                "user_avatar": creator_info.get("avatarUrl"),
                "url_token": actual_url_token,
                "gender": self._format_gender_text(creator_info.get("gender")),
                "ip_location": creator_info.get("ipInfo"),
                "follows": creator_info.get("followingCount", 0),
                "fans": creator_info.get("followerCount", 0),
                "anwser_count": creator_info.get("answerCount", 0),
                "video_count": creator_info.get("zvideoCount", 0),
                "question_count": creator_info.get("questionCount", 0),
                "article_count": creator_info.get("articlesCount", 0),
                "column_count": creator_info.get("columnsCount", 0),
                "get_voteup_count": creator_info.get("voteupCount", 0),
            }
        except Exception as e:
            print(f"[ZhihuExtractor] 提取创作者信息失败: {e}")
            return None
    
    def extract_answer_content(self, answer: Dict) -> Dict:
        """提取回答内容"""
        question = answer.get("question", {})
        author = self._extract_author(answer.get("author"))
        
        return {
            "content_id": str(answer.get("id", "")),
            "content_type": "answer",
            "content_text": extract_text_from_html(answer.get("content", "")),
            "question_id": str(question.get("id", "")),
            "content_url": f"{ZHIHU_URL}/question/{question.get('id')}/answer/{answer.get('id')}",
            "title": extract_text_from_html(answer.get("title", "")),
            "desc": extract_text_from_html(answer.get("description", "") or answer.get("excerpt", "")),
            "created_time": answer.get("created_time", 0),
            "updated_time": answer.get("updated_time", 0),
            "voteup_count": answer.get("voteup_count", 0),
            "comment_count": answer.get("comment_count", 0),
            **author
        }
    
    def extract_article_content(self, article: Dict) -> Dict:
        """提取文章内容"""
        author = self._extract_author(article.get("author"))
        
        return {
            "content_id": str(article.get("id", "")),
            "content_type": "article",
            "content_text": extract_text_from_html(article.get("content", "")),
            "question_id": "",
            "content_url": f"{ZHIHU_ZHUANLAN_URL}/p/{article.get('id')}",
            "title": extract_text_from_html(article.get("title", "")),
            "desc": extract_text_from_html(article.get("excerpt", "")),
            "created_time": article.get("created_time", 0) or article.get("created", 0),
            "updated_time": article.get("updated_time", 0) or article.get("updated", 0),
            "voteup_count": article.get("voteup_count", 0),
            "comment_count": article.get("comment_count", 0),
            **author
        }
    
    def extract_video_content(self, zvideo: Dict) -> Dict:
        """提取视频内容"""
        author = self._extract_author(zvideo.get("author"))
        
        if "video" in zvideo and isinstance(zvideo.get("video"), dict):
            content_url = f"{ZHIHU_URL}/zvideo/{zvideo.get('id')}"
            created_time = zvideo.get("published_at", 0)
            updated_time = zvideo.get("updated_at", 0)
        else:
            content_url = zvideo.get("video_url", "")
            created_time = zvideo.get("created_at", 0)
            updated_time = 0
        
        return {
            "content_id": str(zvideo.get("id", "")),
            "content_type": "zvideo",
            "content_text": "",  # 视频类型没有文本内容
            "question_id": "",
            "content_url": content_url,
            "title": extract_text_from_html(zvideo.get("title", "")),
            "desc": extract_text_from_html(zvideo.get("description", "")),
            "created_time": created_time,
            "updated_time": updated_time,
            "voteup_count": zvideo.get("voteup_count", 0),
            "comment_count": zvideo.get("comment_count", 0),
            **author
        }
    
    def extract_comment(self, comment: Dict, content_id: str, content_type: str) -> Dict:
        """提取评论信息"""
        author = self._extract_author(comment.get("author"))
        ip_location = self._extract_comment_ip_location(comment.get("comment_tag", []))
        
        return {
            "comment_id": str(comment.get("id", "")),
            "parent_comment_id": str(comment.get("reply_comment_id", "")),
            "content": extract_text_from_html(comment.get("content", "")),
            "publish_time": comment.get("created_time", 0),
            "ip_location": ip_location,
            "sub_comment_count": comment.get("child_comment_count", 0),
            "like_count": comment.get("like_count", 0),
            "dislike_count": comment.get("dislike_count", 0),
            "content_id": content_id,
            "content_type": content_type,
            **author
        }
    
    def _extract_author(self, author: Dict) -> Dict:
        """提取作者信息"""
        try:
            if not author:
                return self._empty_author()
            if not author.get("id"):
                author = author.get("member") or {}
            
            return {
                "user_id": str(author.get("id", "")),
                "user_link": f"{ZHIHU_URL}/people/{author.get('url_token', '')}",
                "user_nickname": author.get("name", ""),
                "user_avatar": author.get("avatar_url", ""),
                "user_url_token": author.get("url_token", ""),
            }
        except Exception:
            return self._empty_author()
    
    def _empty_author(self) -> Dict:
        """返回空的作者信息"""
        return {
            "user_id": "",
            "user_link": "",
            "user_nickname": "",
            "user_avatar": "",
            "user_url_token": "",
        }
    
    def _extract_comment_ip_location(self, comment_tags: List[Dict]) -> str:
        """提取评论IP位置"""
        if not comment_tags:
            return ""
        for ct in comment_tags:
            if ct.get("type") == "ip_info":
                return ct.get("text", "")
        return ""
    
    @staticmethod
    def _format_gender_text(gender: int) -> str:
        """格式化性别文本"""
        if gender == 1:
            return "男"
        elif gender == 0:
            return "女"
        else:
            return "未知"
    
    def extract_pin_content(self, pin_data: Dict) -> Dict:
        """提取想法内容"""
        pin_id = str(pin_data.get("id", ""))
        author = self._extract_author(pin_data.get("author"))
        
        # 提取文本内容
        content_text = ""
        content_list = pin_data.get("content", [])
        for content_item in content_list:
            if content_item.get("type") == "text":
                text_content = content_item.get("content", "")
                if text_content:
                    content_text += extract_text_from_html(text_content) + "\n"
        
        # 提取图片URL（如果有）
        image_urls = []
        for content_item in content_list:
            if content_item.get("type") == "image":
                img_url = content_item.get("original_url") or content_item.get("url", "")
                if img_url:
                    image_urls.append(img_url)
        
        # 如果有图片，添加到文本中
        if image_urls:
            content_text += "\n[图片] " + ", ".join(image_urls)
        
        return {
            "content_id": pin_id,
            "content_type": "pin",
            "content_text": content_text.strip(),
            "question_id": "",  # 想法没有question_id
            "content_url": pin_data.get("url", f"{ZHIHU_URL}/pin/{pin_id}"),
            "title": "",  # 想法没有标题
            "desc": content_text[:200] if content_text else "",  # 描述取前200字符
            "created_time": pin_data.get("created", 0),
            "updated_time": pin_data.get("updated", 0),
            "voteup_count": pin_data.get("like_count", 0),
            "comment_count": pin_data.get("comment_count", 0),
            **author
        }
    
    @staticmethod
    def extract_offset(paging_info: Dict) -> str:
        """从分页信息中提取offset"""
        next_url = paging_info.get("next")
        if not next_url:
            return ""
        parsed_url = urlparse(next_url)
        query_params = parse_qs(parsed_url.query)
        offset = query_params.get('offset', [""])[0]
        return offset

