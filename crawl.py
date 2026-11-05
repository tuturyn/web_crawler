import asyncio
from asyncio.tasks import all_tasks
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup, Tag
from typing import TypedDict
import requests
import aiohttp


class PageData(TypedDict):
    url: str
    heading: str
    first_paragraph: str
    outgoing_links: list[str]
    image_urls: list[str]


class AsyncCrawler:
    def __init__(self, base_url: str, max_concurrency: int = 5, max_pages = 100) -> None:
        self.base_url = base_url
        self.base_domain = urlsplit(base_url).netloc

        self.page_data = {}
        self.visited = set()
        self.lock = asyncio.Lock()

        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)

        self.session = None

        self.max_pages = max_pages
        self.should_stop = False
        self.all_tasks = set()

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session is not None:
            await self.session.close()


    async def add_page_visit(self, normalized_url):
        if self.should_stop:
            return False
        async with self.lock:
            if normalized_url in self.visited:
                return False
            elif len(self.visited) >= self.max_pages:
                self.should_stop = True
                print("Reached maximum number of pages to crawl.")
                return False
            else:
                self.visited.add(normalized_url)
                return True

    
    async def get_html(self, url: str):
        try:
            async with self.session.get(url) as response:
            
                if response.status >= 400:
                    raise Exception("error level code (400+)")
            
                content_type = response.headers.get("content-type", "")
            
                if content_type.split(";")[0].strip() != "text/html":
                    raise Exception("response is not text/html") 
            
                return await response.text()
        except Exception as e:
            print(f"{e}")

    async def crawl_page(self, current_url=None):
    
        current_task = asyncio.current_task()
        try:
            if self.should_stop == True:
                return
                
        
            base_parts = urlsplit(self.base_url)
            current_parts = urlsplit(current_url)
            
            if current_parts.netloc != base_parts.netloc:
                return
        
            normalized_url = normalize_url(current_url)
    
            is_new = await self.add_page_visit(normalized_url)
            if not is_new:
                return
        
            print(f"crawling {current_url}")
        
            try:
                async with self.semaphore:
                    html = await self.get_html(current_url)
            except Exception as e:
                print(f"{e}")
                return
        
            page_info  = extract_page_data(html, current_url)
            async with self.lock:
                self.page_data[normalized_url] = page_info 
    
            tasks = []
            for link in page_info["outgoing_links"]:
                new_task = asyncio.create_task(self.crawl_page(link))
                tasks.append(new_task)
                self.all_tasks.add(new_task)
            await asyncio.gather(*tasks)
        finally:
            self.all_tasks.discard(current_task)
        return

    async def crawl(self):
        await self.crawl_page(self.base_url)
        return self.page_data
            
async def crawl_site_async(base_url: str, max_concurrency: int, max_pages: int) -> dict:
    async with AsyncCrawler(base_url, max_concurrency, max_pages) as crawler:
        page_data = await crawler.crawl()
        return page_data

def get_heading_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    h2 = soup.find("h2")

    if h1:
       heading = h1.get_text() 
    elif h2:
        heading = h2.get_text()
    else:
        heading = ""

    return heading

def get_first_paragraph_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    
    main = soup.find("main")
    first_p = (main or soup).find("p")

    paragraph = first_p.get_text() if first_p else ""

    return paragraph

def get_urls_from_html(html:str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    links = soup.find_all("a")

    tabLinks = []
    
    
    for link in links:
        if  link.get("href"):
            tabLinks.append(link.get("href"))

    tab_absolute_urls = []

    for link in tabLinks:
        tab_absolute_urls.append(urljoin(base_url, link))

    return tab_absolute_urls

def get_images_from_html(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    imgs = soup.find_all("img")

    tab_imgs = []
    
    
    for img in imgs:
        if  img.get("src"):
            tab_imgs.append(img.get("src"))

    tab_absolute_img = []

    for img in tab_imgs:
        tab_absolute_img.append(urljoin(base_url, img))

    return tab_absolute_img

def extract_page_data(html: str, page_url: str) -> dict:

    dictionary: PageData = {
        "url" : "",
        "heading" : "",
        "first_paragraph" : "",
        "outgoing_links": [],
        "image_urls" : [],
    }

    dictionary["url"] = page_url

    dictionary["heading"] = get_heading_from_html(html)

    dictionary["first_paragraph"] = get_first_paragraph_from_html(html)

    dictionary["outgoing_links"] = get_urls_from_html(html, page_url)
    
    dictionary["image_urls"] = get_images_from_html(html, page_url)

    return dictionary

def normalize_url(url: str) -> str:
    split = urlsplit(url)
    final_url = split.hostname
    final_url +=  split.path

    if split.path.endswith("/"):
        final_url = final_url[:-1]
    
    return final_url
