from selenium import webdriver
from bs4 import BeautifulSoup
import markdownify
from concurrent.futures import ThreadPoolExecutor
from utils.content_processing import html_to_markdown, needs_visual_analysis
import logging
from typing import Optional, Dict

class WebCrawler:
    def __init__(self, config):
        self.config = config
        self.timeout = config.crawl_timeout
        self.max_threads = config.max_threads
        self._setup_logging()
        
    def gather_sources(self, plan):
        urls = self._get_urls_from_plan(plan)
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            results = list(executor.map(self.process_url, urls))
        return [r for r in results if r is not None]
        
    def process_url(self, url: str) -> Optional[Dict]:
        """Process a single URL and return its content"""
        driver = None
        try:
            driver = self._create_driver()
            driver.get(url)
            
            # Wait for dynamic content
            driver.implicitly_wait(self.timeout)
            
            # Get page content
            soup = BeautifulSoup(driver.page_source, "html.parser")
            content = self._clean_content(soup)
            
            # Check if visual analysis needed
            requires_visual = self._needs_visual_analysis(soup)
            if requires_visual:
                screenshot = driver.get_screenshot_as_base64()
                return {
                    'content': content,
                    'screenshot': screenshot,
                    'needs_visual': True
                }
            
            return {
                'content': content,
                'needs_visual': False
            }
            
        except Exception as e:
            self.logger.error(f"Error processing {url}: {str(e)}")
            return None
            
        finally:
            if driver:
                driver.quit()

    def _create_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return webdriver.Chrome(options=options)

    def _take_screenshot(self, driver):
        return driver.get_screenshot_as_base64()

    def _setup_logging(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def get_page_content(self, url):
        try:
            self.driver.set_page_load_timeout(self.timeout)
            self.driver.get(url)
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            return self._clean_content(soup)
        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")
            return None
            
    def _clean_content(self, soup: BeautifulSoup) -> str:
        """Clean and extract main content"""
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
            
        # Convert to markdown
        return html_to_markdown(str(soup))

    def _needs_visual_analysis(self, soup: BeautifulSoup) -> bool:
        """Check if page needs visual analysis"""
        # Check for tables
        if soup.find_all('table'):
            return True
            
        # Check for charts/graphs
        img_tags = soup.find_all('img')
        for img in img_tags:
            alt = img.get('alt', '').lower()
            if any(term in alt for term in ['chart', 'graph', 'diagram', 'figure']):
                return True
                
        return False 