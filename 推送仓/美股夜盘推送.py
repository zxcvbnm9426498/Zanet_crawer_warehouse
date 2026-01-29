import yfinance as yf
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from weworkbot import Bot as wBot
import os
url = os.getenv("WX_WEBHOOK_URL")

def send_markdown(content: str):
    wBot(url).set_text(content, type='markdown').send()


def send_text(content: str):
    wBot(url).set_text(content).send()

MODULES: Dict[str, List[str]] = {
    "AI 应用": ["PLTR", "AI", "PATH", "CRM", "ADBE"],
    "存储芯片": ["MU", "WDC", "STX", "KIOXY", "SNDK"],
    "机器人": ["TSLA", "IRBT", "ISRG", "SFTBY", "AVAV"],
    "半导体": ["NVDA", "AMD", "INTC", "TSM", "ASML"],
    "CPO": ["AVGO", "MRVL", "COHR", "LITE", "NVDA"],
    "光伏": ["FSLR", "ENPH", "SEDG", "RUN", "SPWR"],
}


def _safe_float(x) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def get_last_two_closes(symbol: str) -> Optional[Tuple[str, float, float]]:

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

    lines: List[str] = [f"**美股夜盘收盘 & 板块涨跌汇总（{date}）**", ""]

    if module_stats:
        max_up = max(module_stats, key=lambda x: x["module_pct"])
        max_down = min(module_stats, key=lambda x: x["module_pct"])
        lines.append(f"**涨幅最大板块**：{max_up['module']}（{_fmt_pct3(max_up['module_pct'])}）")
        lines.append(f"**跌幅最大板块**：{max_down['module']}（{_fmt_pct3(max_down['module_pct'])}）")
        lines.append("")

        lines.append("**板块汇总**")
        lines.append("")
        table_lines = []
        table_lines.append("板块".ljust(35) + "个股数".rjust(8) + "涨跌幅".rjust(15))
        table_lines.append("-" * 38)
        for ms in module_stats:
            module_name = ms['module']
            count = ms['count']
            pct_str = _fmt_pct3(ms['module_pct'])
            table_lines.append(module_name.ljust(35) + str(count).rjust(8) + pct_str.rjust(15))
        lines.append("```")
        lines.extend(table_lines)
        lines.append("```")
        lines.append("")

    by_symbol = {r["symbol"]: r for r in rows}
    lines.append("**个股明细**")
    lines.append("")
    for module, symbols in MODULES.items():
        available = [s for s in symbols if s in by_symbol]
        if not available:
            continue
        lines.append(f"**{module}**")
        lines.append("")
        table_lines = []
        table_lines.append("股票".ljust(8) + "收盘价".rjust(15) + "涨跌幅".rjust(15))
        table_lines.append("-" * 38)
        for s in available:
            r = by_symbol[s]
            close_str = _fmt3(r['close'])
            pct_str = _fmt_pct3(r['pct'])
            table_lines.append(s.ljust(8) + close_str.rjust(15) + pct_str.rjust(15))
        lines.append("```")
        lines.extend(table_lines)
        lines.append("```")
        lines.append("")

    if not rows:
        lines.append("今日未获取到任何美股收盘数据。")

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

    symbols = sorted({s for ss in MODULES.values() for s in ss})

    rows = get_daily_stats_for_symbols(symbols)

    date = rows[0]["date"] if rows else datetime.utcnow().strftime("%Y-%m-%d")
    module_stats = calc_module_stats(rows)
    markdown_content = build_markdown_message(rows, module_stats, date)
    send_markdown(markdown_content)
