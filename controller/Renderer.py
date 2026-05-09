from playwright.sync_api import sync_playwright


class Renderer:

    def __init__(self, config):
        self.config = config

    def html_to_png(self, html: str, output_path: str):

        with sync_playwright() as p:
            browser = p.chromium.launch()

            page = browser.new_page(
                viewport={
                    "width": self.config.render.width,
                    "height": self.config.render.height
                }
            )

            page.set_content(html)
            page.wait_for_timeout(300)

            page.screenshot(
                path=output_path,
                full_page=True
            )

            browser.close()
