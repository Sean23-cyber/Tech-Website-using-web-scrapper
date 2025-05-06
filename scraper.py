import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import random
import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class NewsArticle:
    def __init__(self, title: str, summary: str, url: str, source: str, 
                 category: str, image: str = "", authors: List[str] = None):
        self.title = title
        self.summary = summary
        self.url = url
        self.source = source
        self.category = category
        self.image = image
        self.authors = authors or []
        self.date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.scrape_timestamp = int(time.time())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "source": self.source,
            "category": self.category,
            "image": self.image,
            "authors": self.authors,
            "date": self.date,
            "scrape_timestamp": self.scrape_timestamp
        }

class NewsScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'DNT': '1'
        }
        self.articles = []
        self.request_delay = (1.0, 3.0)
        self.timeout = 15
        
    def _make_request(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        for attempt in range(max_retries):
            try:
                time.sleep(random.uniform(*self.request_delay))
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', random.randint(10, 30)))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds before retry...")
                    time.sleep(retry_after)
                    continue
                else:
                    logger.error(f"HTTP {response.status_code} for {url}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed for {url}: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Max retries exceeded for {url}")
                    return None
                time.sleep(random.uniform(2.0, 5.0))
        
        return None
    
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        try:
            response = self._make_request(url)
            if response:
                return BeautifulSoup(response.text, 'html.parser')
            return None
        except Exception as e:
            logger.error(f"Error parsing page {url}: {e}")
            return None
    
    def _normalize_url(self, url: str, base_domain: str) -> str:
        if not url.startswith('http'):
            return urljoin(base_domain, url)
        return url
    
    def _extract_authors(self, article_element) -> List[str]:
        author_selectors = [
            '.author-name', '.byline__author', '.c-byline__author', 
            '[rel="author"]', '.author', '.byline-author'
        ]
        
        authors = []
        for selector in author_selectors:
            author_elements = article_element.select(selector)
            if author_elements:
                for elem in author_elements:
                    author = elem.get_text(strip=True)
                    if author and author not in authors:
                        authors.append(author)
        return authors
    
    def scrape_techcrunch_ai(self) -> None:
        logger.info("Scraping TechCrunch AI...")
        url = "https://techcrunch.com/category/artificial-intelligence/"
        soup = self.get_page(url)
        
        if not soup:
            return
        
        article_containers = (
            soup.select('article.post-block') or
            soup.select('.post-block') or
            soup.select('div[data-type="article"]') or
            soup.select('div.content') or
            soup.select('article') or
            soup.find_all(['article', 'div'], class_=lambda c: c and ('post' in c.lower() or 'article' in c.lower()))
        )
        
        logger.info(f"Found {len(article_containers)} potential articles on TechCrunch")
        
        for article in article_containers:
            try:
                title_elem = None
                for selector in ['h2 a', 'h3 a', '.post-block__title a', '.article__title a', '.title a']:
                    title_elem = article.select_one(selector)
                    if title_elem:
                        break
                        
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = self._normalize_url(title_elem['href'], "https://techcrunch.com")
                
                summary_elem = None
                for selector in ['div.post-block__content', '.excerpt', 'p.post-block__excerpt', '.article__excerpt']:
                    summary_elem = article.select_one(selector)
                    if summary_elem:
                        break
                    
                summary = summary_elem.get_text(strip=True) if summary_elem else ""
                
                img_elem = None
                for selector in ['img.post-block__image', '.article__featured-image img', 'figure img']:
                    img_elem = article.select_one(selector)
                    if img_elem:
                        break
                    
                img_url = ""
                if img_elem:
                    img_url = img_elem.get('data-src') or img_elem.get('src', "")
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                
                authors = self._extract_authors(article)
                
                self.articles.append(NewsArticle(
                    title=title,
                    summary=summary,
                    url=url,
                    source="TechCrunch",
                    category="AI",
                    image=img_url,
                    authors=authors
                ))
                
            except Exception as e:
                logger.error(f"Error processing TechCrunch article: {e}")

    def scrape_wired_tech(self) -> None:
        logger.info("Scraping Wired Tech...")
        url = "https://www.wired.com/category/business/"
        soup = self.get_page(url)
        
        if not soup:
            return
            
        # Updated selectors for Wired's current layout
        article_containers = (
            soup.select('div.SummaryItemContent-gYA-Dbp') or
            soup.select('li.summary-item') or
            soup.select('div.card-component') or
            soup.select('article.archive-item-component') or
            soup.find_all(['article', 'div', 'li'], 
                class_=lambda c: c and ('summary' in c.lower() or 'card' in c.lower() or 'item' in c.lower()))
        )
        
        logger.info(f"Found {len(article_containers)} potential articles on Wired")
        
        for article in article_containers:
            try:
                # Updated title selectors
                title_elem = article.select_one('a[data-testid="SummaryItemHedLink"]')
                if not title_elem:
                    title_elem = article.select_one('h2 a') or article.select_one('h3 a')
                
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                url = self._normalize_url(title_elem.get('href', ''), "https://www.wired.com")
                
                # Updated summary selectors
                summary_elem = article.select_one('p[data-testid="SummaryItemDek"]')
                if not summary_elem:
                    summary_elem = article.select_one('.summary-item__dek') or article.select_one('p.dek')
                
                summary = summary_elem.get_text(strip=True) if summary_elem else ""
                
                # Updated image selectors
                img_elem = article.select_one('img[data-testid="SummaryItemImage"]')
                if not img_elem:
                    img_elem = article.select_one('.summary-item__image img') or article.select_one('img.SummaryItemImage-gEhMcn')
                
                img_url = ""
                if img_elem:
                    img_url = img_elem.get('src') or img_elem.get('data-src', "")
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = 'https://www.wired.com' + img_url
                
                authors = self._extract_authors(article)
                
                self.articles.append(NewsArticle(
                    title=title,
                    summary=summary,
                    url=url,
                    source="Wired",
                    category="Tech",
                    image=img_url,
                    authors=authors
                ))
                
            except Exception as e:
                logger.error(f"Error processing Wired article: {e}")
    
    def save_articles(self, filename: str = 'news_data.json') -> None:
        articles_data = [article.to_dict() for article in self.articles]
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(articles_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully saved {len(articles_data)} articles to {filename}")
        except Exception as e:
            logger.error(f"Error saving articles to {filename}: {e}")
    
    def load_articles(self, filename: str = 'news_data.json') -> List[Dict[str, Any]]:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except UnicodeDecodeError:
            try:
                with open(filename, 'r', encoding='utf-8-sig') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading articles: {e}")
                return []
        except FileNotFoundError:
            logger.warning("No existing data file found")
            return []
        except json.JSONDecodeError:
            logger.warning("Data file corrupted")
            return []
    
    def scrape_all(self, source_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            logger.info(f"Starting scraping process (filter: {source_filter})...")
            self.articles = []
            
            if not source_filter or source_filter.lower() == "techcrunch":
                self.scrape_techcrunch_ai()
            
            if not source_filter or source_filter.lower() == "wired":
                self.scrape_wired_tech()
            
            if len(self.articles) < 5:
                logger.warning("Few articles found, attempting fallback scraping...")
                self._fallback_scrape(source_filter)
            
            self.save_articles()
            
            logger.info(f"Scraping completed. Found {len(self.articles)} articles.")
            return [article.to_dict() for article in self.articles]
            
        except Exception as e:
            logger.error(f"Error in scrape_all: {e}")
            return []
    
    def _fallback_scrape(self, source_filter: Optional[str] = None) -> None:
        """Generic fallback scraping method"""
        urls_to_scrape = []
        
        if not source_filter or source_filter.lower() == "techcrunch":
            urls_to_scrape.append(("https://techcrunch.com/category/artificial-intelligence/", "TechCrunch", "AI"))
        
        if not source_filter or source_filter.lower() == "wired":
            urls_to_scrape.append(("https://www.wired.com/category/business/", "Wired", "Tech"))
        
        for url, source, category in urls_to_scrape:
            logger.info(f"Attempting fallback scrape for {source}")
            soup = self.get_page(url)
            
            if not soup:
                continue
                
            # Generic article detection
            article_links = []
            article_pattern = re.compile(r'/\d{4}/|/article/|/story/|/news/|/entry/|/posts?/')
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                if ('nav' in str(link.parent).lower() or 
                    'footer' in str(link.parent).lower() or
                    'menu' in str(link.parent).lower()):
                    continue
                    
                if article_pattern.search(href):
                    link_text = link.get_text(strip=True)
                    
                    if len(link_text) < 15 or link_text.lower() in ['home', 'about', 'contact']:
                        continue
                        
                    if not any(href == a['url'] for a in self.articles):
                        article_links.append(link)
            
            for link in article_links[:20]:  # Limit to 20 articles per source
                try:
                    title = link.get_text(strip=True)
                    url = self._normalize_url(link['href'], url)
                    
                    self.articles.append(NewsArticle(
                        title=title,
                        summary="",
                        url=url,
                        source=source,
                        category=category,
                        image=""
                    ))
                    
                except Exception as e:
                    logger.error(f"Error processing fallback article: {e}")

def main():
    try:
        logger.info("Starting news scraper...")
        
        scraper = NewsScraper()
        
        # Example of how to use with source filter
        # articles = scraper.scrape_all(source_filter="wired")  # Only scrape Wired
        articles = scraper.scrape_all()  # Scrape all sources
        
        logger.info("Scraping process completed.")
        
        if articles:
            sources = set(article['source'] for article in articles)
            logger.info(f"Scraped {len(articles)} articles from {len(sources)} sources")
        else:
            logger.warning("No articles were scraped")
            
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
    finally:
        logger.info("Program finished")

if __name__ == "__main__":
    main()