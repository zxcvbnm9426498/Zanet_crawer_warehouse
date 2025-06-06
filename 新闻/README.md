<!--
 * @Author: 择安网络
 * @Code function: 
 * @Date: 2025-04-29 11:14:52
 * @FilePath: /爬虫仓/README.md
 * @LastEditTime: 2025-06-04 09:53:05
-->
# 新闻爬虫工具集

这个项目包含两个新闻网站的爬虫工具，用于抓取CCTV和人民网的新闻搜索结果。

## 功能特点

### CCTV爬虫 (CCTV.py)
- 异步多线程爬取CCTV网站搜索结果
- 自动检测并处理分页
- 支持自定义搜索关键词和爬取页数
- 结果保存为CSV格式
- 适配CCTV网站搜索页面结构

### 人民网爬虫 (人民网.py)
- 支持同步和异步两种爬取模式
- 完整提取文章内容
- 支持按时间范围筛选新闻
- 可通过命令行参数灵活配置
- 多线程并发处理，提高效率

## 环境要求

- Python 3.7+
- 依赖库：requests, aiohttp, asyncio, BeautifulSoup4, pandas, tqdm

## 依赖安装

```bash
pip install requests aiohttp asyncio beautifulsoup4 pandas tqdm
```

## 使用方法

### CCTV爬虫

```bash
python 新闻/CCTV.py
```

CCTV爬虫默认搜索关键词为"智慧城市"，可以在代码中修改`main`函数的`search_query`参数更改搜索关键词。

### 人民网爬虫

```bash
# 基本用法
python 新闻/人民网.py -k 搜索关键词

# 使用异步模式并限制页数
python 新闻/人民网.py -k 搜索关键词 -a -m 10

# 指定日期范围
python 新闻/人民网.py -k 搜索关键词 -s 2023-01-01 -e 2023-12-31

# 爬取特定年份的数据
python 新闻/人民网.py -k 搜索关键词 -y 2023
```

#### 参数说明

- `-k`, `--keyword`：搜索关键词，默认为"食物中毒"
- `-m`, `--max_pages`：最大抓取页数，默认不限制
- `-l`, `--limit`：每页结果数，默认为10
- `-d`, `--delay`：请求间隔(秒)，默认为1秒
- `-s`, `--start_date`：开始日期 (YYYY-MM-DD格式)
- `-e`, `--end_date`：结束日期 (YYYY-MM-DD格式)
- `-y`, `--year`：指定年份，会自动设置该年度的开始和结束日期
- `-a`, `--async_mode`：使用异步模式抓取
- `-c`, `--concurrency`：异步模式下的并发数，默认为5

## 输出结果

爬取的数据将保存为CSV文件，包含以下字段：
- 标题
- 内容摘要
- URL
- 发布时间
- 作者
- 编辑
- 来源
- 所属栏目
- 文章全文（仅人民网爬虫）
