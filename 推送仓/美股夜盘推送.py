import yfinance as yf
from datetime import datetime
from typing import List
import csv

from weworkbot import Bot as wBot

# 企业微信机器人 Webhook URL
url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=dd087cea-1c56-4902-b919-e1f0aacd4a1f'

def send_markdown(content: str):
    """
    发送 Markdown 消息到企业微信群机器人
    """
    wBot(url).set_text(content, type='markdown').send()


def send_text(content: str):
    """
    发送普通文本消息到企业微信群机器人
    """
    wBot(url).set_text(content).send()

def get_daily_close_for_symbols(symbols: List[str]):
    results = []
    for symbol in symbols:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d", interval="1d")
        if hist.empty:
            print(f"警告：{symbol} 没有拿到数据，跳过")
            continue

        last_row = hist.iloc[-1]
        results.append({
            "symbol": symbol,
            "date": last_row.name.strftime("%Y-%m-%d"),
            "close": float(last_row["Close"]),
        })
    return results


def save_to_csv(rows, filename="us_stocks_close.csv"):
    if not rows:
        print("没有数据可以写入 CSV")
        return

    fieldnames = ["symbol", "date", "close"]
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        # 如果文件是第一次写，可以写表头（简单判断文件是否为空也可以，这里直接写一次，手动删也行）
        # writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_markdown_message(rows):
    """
    把收盘价列表拼成一条 Markdown 消息
    """
    if not rows:
        return "今日未获取到任何美股收盘数据。"

    # 假设所有数据是同一天的
    date = rows[0]["date"]
    lines = [
        f"**美股夜盘收盘价 ({date})**",
        ""
    ]
    for row in rows:
        symbol = row["symbol"]
        close = row["close"]
        lines.append(f"- **{symbol}** 收盘价：`{close}`")

    return "\n".join(lines)


if __name__ == "__main__":
    symbols = ["AAPL", "MSFT", "TSLA"]  # 你关心的股票列表
    rows = get_daily_close_for_symbols(symbols)
    print(rows)

    # 保存到 CSV
    save_to_csv(rows)

    # 推送到企业微信
    markdown_content = build_markdown_message(rows)
    send_markdown(markdown_content)