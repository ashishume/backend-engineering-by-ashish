import requests
from bs4 import BeautifulSoup
import re
import os
from urllib.parse import urljoin, urlparse

class ByteByteGoScraper:
    def __init__(self, base_url="https://bytebytego.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
        })
    
    def fetch_page(self, url):
        """Fetch a single page and return BeautifulSoup object"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_article_content(self, soup, url):
        """Extract title, content, and metadata from an article page"""
        if not soup:
            return None
        
        # Extract title
        title_tag = soup.find('h1') or soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else "Untitled"
        
        # Extract main content (adjust selectors based on actual site structure)
        # Common patterns for article content
        content_selectors = [
            'article',
            'main',
            '.content',
            '.post-content',
            '.entry-content',
            '[class*="article"]',
            '[class*="post"]'
        ]
        
        content = None
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                break
        
        if not content:
            # Fallback to body content
            content = soup.find('body')
        
        # Clean up the content
        # Remove script and style elements
        for script in content.find_all(['script', 'style', 'nav', 'header', 'footer']):
            script.decompose()
        
        return {
            'title': title,
            'url': url,
            'content': str(content),
            'text': content.get_text(separator='\n', strip=True)
        }
    
    def html_to_markdown(self, html_content):
        """Convert HTML content to Markdown"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        markdown_lines = []
        
        for element in soup.descendants:
            if element.name == 'h1':
                markdown_lines.append(f"# {element.get_text(strip=True)}")
            elif element.name == 'h2':
                markdown_lines.append(f"## {element.get_text(strip=True)}")
            elif element.name == 'h3':
                markdown_lines.append(f"### {element.get_text(strip=True)}")
            elif element.name == 'p':
                text = element.get_text(strip=True)
                if text:
                    markdown_lines.append(text)
            elif element.name == 'ul':
                for li in element.find_all('li', recursive=False):
                    markdown_lines.append(f"- {li.get_text(strip=True)}")
            elif element.name == 'ol':
                for i, li in enumerate(element.find_all('li', recursive=False), 1):
                    markdown_lines.append(f"{i}. {li.get_text(strip=True)}")
            elif element.name == 'code':
                code_text = element.get_text(strip=True)
                if '\n' in code_text:
                    markdown_lines.append(f"```\n{code_text}\n```")
                else:
                    markdown_lines.append(f"`{code_text}`")
            elif element.name == 'pre':
                code_text = element.get_text(strip=True)
                markdown_lines.append(f"```\n{code_text}\n```")
            elif element.name == 'a':
                href = element.get('href', '')
                text = element.get_text(strip=True)
                if href and text:
                    markdown_lines.append(f"[{text}]({href})")
            elif element.name == 'img':
                src = element.get('src', '')
                alt = element.get('alt', 'image')
                if src:
                    markdown_lines.append(f"![{alt}]({src})")
        
        return '\n\n'.join(markdown_lines)
    


    def fetch_with_selenium(url):
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    html = driver.page_source
    driver.quit()
    return BeautifulSoup(html, 'html.parser')
    
    def scrape_article(self, url):
        """Scrape a single article and convert to markdown"""
        print(f"Scraping: {url}")
        soup = self.fetch_page(url)
        
        if not soup:
            return None
        
        article_data = self.extract_article_content(soup, url)
        if not article_data:
            return None
        
        # Convert to markdown
        markdown_content = self.html_to_markdown(article_data['content'])
        
        # Create full markdown document
        full_md = f"""# {article_data['title']}



        
**Source:** [{article_data['url']}]({article_data['url']})
**Scraped:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{markdown_content}
"""
        return full_md
    
    def save_to_file(self, content, filename, output_dir="./bytebytego_content"):
        """Save markdown content to local file"""
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Clean filename
        safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
        if not safe_filename.endswith('.md'):
            safe_filename += '.md'
        
        filepath = os.path.join(output_dir, safe_filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Saved to: {filepath}")
        return filepath
    
    def scrape_from_sitemap(self, sitemap_url=None):
        """Scrape all articles from sitemap"""
        if not sitemap_url:
            sitemap_url = f"{self.base_url}/sitemap.xml"
        
        soup = self.fetch_page(sitemap_url)
        if not soup:
            print("Could not fetch sitemap")
            return []
        
        # Extract URLs from sitemap
        urls = [loc.text for loc in soup.find_all('loc')]
        print(f"Found {len(urls)} URLs in sitemap")
        
        scraped_files = []
        for url in urls:
            # Filter for article URLs only
            if '/blog/' in url or '/newsletter/' in url or '/article/' in url:
                md_content = self.scrape_article(url)
                if md_content:
                    # Generate filename from URL
                    parsed = urlparse(url)
                    filename = os.path.basename(parsed.path) or 'index'
                    filepath = self.save_to_file(md_content, filename)
                    scraped_files.append(filepath)
        
        return scraped_files


# Example usage
if __name__ == "__main__":
    scraper = ByteByteGoScraper()
    
    # Option 1: Scrape a single article
    article_url = "https://bytebytego.com/courses/genai-system-design-interview/retrieval-augmented-generation"
    markdown = scraper.scrape_article(article_url)
    # if markdown:
    scraper.save_to_file(markdown, "single_article")
    
    # Option 2: Scrape from sitemap (all articles)
    # scraped_files = scraper.scrape_from_sitemap()
    
    # Option 3: Scrape multiple specific URLs
    urls_to_scrape = [
        # "https://bytebytego.com/p/api-design",
        # "https://bytebytego.com/p/system-design",
        # Add more URLs here
    ]
    
    for url in urls_to_scrape:
        try:
            md_content = scraper.scrape_article(url)
            if md_content:
                filename = url.split('/')[-1] if '/' in url else 'article'
                scraper.save_to_file(md_content, filename)
        except Exception as e:
            print(f"Error processing {url}: {e}")