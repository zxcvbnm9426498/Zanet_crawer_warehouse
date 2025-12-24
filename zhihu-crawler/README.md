# 知乎爬虫 (Scrapy版本)

基于 Scrapy 框架重构的知乎爬虫，专门用于爬取：
- **详情模式 (detail)**: 爬取指定内容的详情和评论
- **创作者模式 (creator)**: 爬取创作者主页的所有内容

## 项目结构

```
zhihu-crawler/
├── scrapy_zhihu/          # Scrapy项目
│   ├── spiders/           # 爬虫
│   │   ├── detail_spider.py    # 详情模式爬虫
│   │   └── creator_spider.py   # 创作者模式爬虫
│   ├── items.py          # 数据模型
│   ├── middlewares.py    # 中间件（签名、Cookie）
│   ├── pipelines.py      # 数据存储
│   └── settings.py       # 配置
├── zhihu_core/           # 核心模块
│   ├── extractor.py      # 数据提取器
│   ├── sign.py           # API签名
│   ├── utils.py          # 工具函数
│   └── constants.py      # 常量
├── config/               # 配置文件
│   └── zhihu_config.py   # 知乎配置
├── libs/                 # 第三方库
│   └── zhihu.js          # 签名JS文件
└── data/                 # 数据输出目录
    └── zhihu/
        ├── csv/          # CSV格式
        └── json/         # JSON格式
```

## 安装

```bash
pip install -r requirements.txt
```

## 配置

编辑 `config/zhihu_config.py`:

```python
# Cookie配置（必须）
COOKIES = "your_cookie_string_here"

# 创作者模式：指定要爬取的创作者URL列表
ZHIHU_CREATOR_URL_LIST = [
    "https://www.zhihu.com/people/zhangkangkang",
]

# 详情模式：指定要爬取的内容URL列表
ZHIHU_SPECIFIED_ID_LIST = [
    "https://www.zhihu.com/question/826896610/answer/4885821440",  # 回答
    "https://zhuanlan.zhihu.com/p/673461588",  # 文章
    "https://www.zhihu.com/zvideo/1539542068422144000",  # 视频
]

# 是否爬取评论
ENABLE_GET_COMMENTS = True

# 是否爬取二级评论
ENABLE_GET_SUB_COMMENTS = False

# 数据保存方式: csv | json
SAVE_DATA_OPTION = "csv"
```

## 使用方法

### 创作者模式

```bash
scrapy crawl creator
```

### 详情模式

```bash
scrapy crawl detail
```

## 数据输出

数据会保存在 `data/zhihu/` 目录下：
- CSV格式：`data/zhihu/csv/`
- JSON格式：`data/zhihu/json/`

## 注意事项

1. **Cookie配置**: 必须配置有效的Cookie才能正常爬取
2. **请求频率**: 已设置合理的下载延迟，请勿频繁请求
3. **遵守规则**: 请遵守知乎的使用条款和robots.txt规则

