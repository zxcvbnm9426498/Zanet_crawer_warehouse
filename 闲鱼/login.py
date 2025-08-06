import asyncio
from playwright.async_api import async_playwright

STATE_FILE = "cookies.json"
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://www.goofish.com/")
        print("\n" + "="*50)
        print("请在打开的浏览器窗口中手动登录您的闲鱼账号。")
        print("推荐使用APP扫码登录。")
        print("登录成功后，回到这里，按 Enter 键继续...")
        print("="*50 + "\n")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, input)
        await context.storage_state(path=STATE_FILE)
        print(f"登录状态已成功保存到文件: {STATE_FILE}")
        await browser.close()
if __name__ == "__main__":
    print("正在启动浏览器以进行登录...")
    asyncio.run(main())