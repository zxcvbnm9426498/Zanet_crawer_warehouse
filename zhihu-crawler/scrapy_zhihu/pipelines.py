# -*- coding: utf-8 -*-
"""
数据存储Pipeline
"""
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

from itemadapter import ItemAdapter
from scrapy_zhihu.items import ZhihuContentItem, ZhihuCommentItem, ZhihuCreatorItem
from config import zhihu_config


class ZhihuPipeline:
    """知乎数据存储Pipeline"""
    
    def __init__(self):
        self.save_option = zhihu_config.SAVE_DATA_OPTION
        self.data_dir = Path("data/zhihu")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # CSV文件句柄
        self.csv_files = {}
        self.csv_writers = {}
        
        # JSON数据缓存
        self.json_data = {
            'contents': [],
            'comments': [],
            'creators': []
        }
    
    def open_spider(self, spider):
        """Spider启动时调用"""
        if self.save_option == 'csv':
            self._init_csv_files()
        elif self.save_option == 'json':
            self._init_json_files()
    
    def close_spider(self, spider):
        """Spider关闭时调用"""
        if self.save_option == 'csv':
            self._close_csv_files()
        elif self.save_option == 'json':
            self._save_json_files()
    
    def process_item(self, item, spider):
        """处理item"""
        import time
        adapter = ItemAdapter(item)
        item_dict = dict(adapter)
        
        # 添加时间戳（13位毫秒时间戳）
        item_dict['last_modify_ts'] = int(time.time() * 1000)
        
        # 确保source_keyword字段存在（creator/detail模式为空）
        if isinstance(item, ZhihuContentItem) and 'source_keyword' not in item_dict:
            item_dict['source_keyword'] = ''
        
        if isinstance(item, ZhihuContentItem):
            self._save_content(item_dict)
        elif isinstance(item, ZhihuCommentItem):
            self._save_comment(item_dict)
        elif isinstance(item, ZhihuCreatorItem):
            self._save_creator(item_dict)
        
        return item
    
    def _save_content(self, item_dict: Dict):
        """保存内容"""
        if self.save_option == 'csv':
            self._write_csv('contents', item_dict)
        elif self.save_option == 'json':
            self.json_data['contents'].append(item_dict)
    
    def _save_comment(self, item_dict: Dict):
        """保存评论"""
        if self.save_option == 'csv':
            self._write_csv('comments', item_dict)
        elif self.save_option == 'json':
            self.json_data['comments'].append(item_dict)
    
    def _save_creator(self, item_dict: Dict):
        """保存创作者"""
        if self.save_option == 'csv':
            self._write_csv('creators', item_dict)
        elif self.save_option == 'json':
            self.json_data['creators'].append(item_dict)
    
    def _init_csv_files(self):
        """初始化CSV文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_dir = self.data_dir / "csv"
        csv_dir.mkdir(parents=True, exist_ok=True)
        
        for item_type in ['contents', 'comments', 'creators']:
            file_path = csv_dir / f"{item_type}_{timestamp}.csv"
            self.csv_files[item_type] = open(file_path, 'w', newline='', encoding='utf-8-sig')
            self.csv_writers[item_type] = None  # 延迟初始化，需要知道字段名
    
    def _write_csv(self, item_type: str, item_dict: Dict):
        """写入CSV"""
        if item_type not in self.csv_files:
            return
        
        writer = self.csv_writers.get(item_type)
        if writer is None:
            # 第一次写入，创建writer并写入表头
            writer = csv.DictWriter(self.csv_files[item_type], fieldnames=item_dict.keys())
            writer.writeheader()
            self.csv_writers[item_type] = writer
        
        writer.writerow(item_dict)
    
    def _close_csv_files(self):
        """关闭CSV文件"""
        for f in self.csv_files.values():
            if f:
                f.close()
    
    def _init_json_files(self):
        """初始化JSON文件"""
        pass
    
    def _save_json_files(self):
        """保存JSON文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_dir = self.data_dir / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        
        for item_type, data in self.json_data.items():
            if data:
                file_path = json_dir / f"{item_type}_{timestamp}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

