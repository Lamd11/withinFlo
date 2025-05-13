import asyncio
from playwright.async_api import async_playwright

async def main():
    print("Starting Playwright test...")
    async with async_playwright() as p:
        print("Playwright started successfully!")
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto('https://example.com')
        title = await page.title()
        print(f"Page title: {title}")
        await browser.close()
    print("Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(main()) 