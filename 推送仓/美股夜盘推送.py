import yfinance as yf
from datetime import datetime
from typing import Dict, List, Optional, Tuple
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

MODULES: Dict[str, List[str]] = {
    "AI 应用（AI Applications）": ["PLTR", "AI", "PATH", "CRM", "ADBE"],
    "存储芯片（Memory Chips）": ["MU", "WDC", "STX", "KIOXY", "SNDK"],
    "机器人（Robotics）": ["TSLA", "IRBT", "ISRG", "SFTBY", "AVAV"],
    "半导体（Semiconductors）": ["NVDA", "AMD", "INTC", "TSM", "ASML"],
    "CPO（Co-packaged Optics）": ["AVGO", "MRVL", "COHR", "LITE", "NVDA"],
    "光伏（Solar PV）": ["FSLR", "ENPH", "SEDG", "RUN", "SPWR"],
}


def _safe_float(x) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def get_last_two_closes(symbol: str) -> Optional[Tuple[str, float, float]]:
    """
    返回 (date_yyyy_mm_dd, last_close, prev_close)
    拿不到或数据不足则返回 None
    """
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="10d", interval="1d")
    if hist is None or hist.empty or "Close" not in hist.columns:
        return None

    closes = hist["Close"].dropna()
    if len(closes) < 2:
        return None

    last_close = _safe_float(closes.iloc[-1])
    prev_close = _safe_float(closes.iloc[-2])
    if last_close is None or prev_close is None:
        return None

    date = closes.index[-1].strftime("%Y-%m-%d")
    return date, last_close, prev_close


def get_daily_stats_for_symbols(symbols: List[str]):
    """
    每个 symbol 返回:
    - date: 最近交易日日期
    - close: 最近收盘价
    - prev_close: 前一交易日收盘价
    - pct: 涨跌幅（%）
    """
    results = []
    for symbol in symbols:
        data = get_last_two_closes(symbol)
        if not data:
            print(f"警告：{symbol} 没有拿到足够的历史数据，跳过")
            continue
        date, last_close, prev_close = data
        pct = (last_close / prev_close - 1.0) * 100.0 if prev_close != 0 else None
        results.append({
            "symbol": symbol,
            "date": date,
            "close": last_close,
            "prev_close": prev_close,
            "pct": pct,
        })
    return results


def save_to_csv(rows, filename="us_stocks_close.csv"):
    if not rows:
        print("没有数据可以写入 CSV")
        return

    fieldnames = ["symbol", "date", "close", "prev_close", "pct"]
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        # 如果文件是第一次写，可以写表头（简单判断文件是否为空也可以，这里直接写一次，手动删也行）
        # writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _fmt3(x: Optional[float]) -> str:
    if x is None:
        return "--"
    return f"{x:.3f}"


def _fmt_pct3(x: Optional[float]) -> str:
    if x is None:
        return "--"
    sign = "+" if x >= 0 else ""
    return f"{sign}{x:.3f}%"


def build_markdown_message(rows, module_stats, date: str):
    """
    把收盘价 + 个股涨跌幅 + 板块汇总拼成一条 Markdown 消息
    """
    lines: List[str] = [f"**美股夜盘收盘 & 板块涨跌汇总（{date}）**", ""]

    if module_stats:
        max_up = max(module_stats, key=lambda x: x["module_pct"])
        max_down = min(module_stats, key=lambda x: x["module_pct"])
        lines.append(f"**涨幅最大板块**：{max_up['module']}（{_fmt_pct3(max_up['module_pct'])}）")
        lines.append(f"**跌幅最大板块**：{max_down['module']}（{_fmt_pct3(max_down['module_pct'])}）")
        lines.append("")

        lines.append("**板块汇总（板块涨跌幅=板块内 5 只个股涨跌幅平均）**")
        lines.append("")
        lines.append("| 板块 | 覆盖个股数 | 板块涨跌幅 |")
        lines.append("| --- | ---: | ---: |")
        for ms in module_stats:
            lines.append(f"| {ms['module']} | {ms['count']} | {_fmt_pct3(ms['module_pct'])} |")
        lines.append("")

    # 个股明细（按板块分组）
    by_symbol = {r["symbol"]: r for r in rows}
    lines.append("**个股明细**")
    lines.append("")
    for module, symbols in MODULES.items():
        available = [s for s in symbols if s in by_symbol]
        if not available:
            continue
        lines.append(f"**{module}**")
        lines.append("")
        lines.append("| 股票 | 收盘价 | 涨跌幅 |")
        lines.append("| --- | ---: | ---: |")
        for s in available:
            r = by_symbol[s]
            lines.append(f"| {s} | `{_fmt3(r['close'])}` | `{_fmt_pct3(r['pct'])}` |")
        lines.append("")

    if not rows:
        lines.append("今日未获取到任何美股收盘数据。")

    lines.append(f"_生成时间（UTC）：{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}_")
    return "\n".join(lines)


def calc_module_stats(rows):
    by_symbol = {r["symbol"]: r for r in rows}
    module_stats = []
    for module, symbols in MODULES.items():
        pcts = []
        for s in symbols:
            r = by_symbol.get(s)
            if r and r.get("pct") is not None:
                pcts.append(float(r["pct"]))
        if not pcts:
            continue
        module_stats.append({
            "module": module,
            "count": len(pcts),
            "module_pct": sum(pcts) / len(pcts),
        })
    module_stats.sort(key=lambda x: x["module_pct"], reverse=True)
    return module_stats


if __name__ == "__main__":
    # 股票池：所有板块个股去重后合并
    symbols = sorted({s for ss in MODULES.values() for s in ss})

    rows = get_daily_stats_for_symbols(symbols)
    print(rows)

    # 保存到 CSV
    save_to_csv(rows)

    # 推送到企业微信
    date = rows[0]["date"] if rows else datetime.utcnow().strftime("%Y-%m-%d")
    module_stats = calc_module_stats(rows)
    markdown_content = build_markdown_message(rows, module_stats, date)
    send_markdown(markdown_content)
