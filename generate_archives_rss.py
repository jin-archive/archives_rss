import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
import re
from urllib.parse import urljoin

# 1. 대상 URL 및 설정 정보 리스트 (두 개의 게시판을 한 번에 처리)
targets = [
    {
        'url': 'https://www.archives.go.kr/next/newnews/wordsList1.do',
        'title': '국가기록원 알립니다 RSS',
        'desc': '행정안전부 국가기록원 알립니다(공지사항) 게시판입니다.',
        'filename': 'archives_notice_rss.xml'
    },
    {
        'url': 'https://www.archives.go.kr/next/newnews/employment1.do',
        'title': '국가기록원 채용공고 RSS',
        'desc': '행정안전부 국가기록원 채용공고 게시판입니다.',
        'filename': 'archives_recruit_rss.xml'
    }
]

base_url = "https://www.archives.go.kr"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

# 2. 각 게시판별로 반복하며 RSS 생성
for target in targets:
    print(f"[{target['title']}] 작업을 시작합니다...")
    
    try:
        response = requests.get(target['url'], headers=headers, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8' # 한글 깨짐 방지
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # RSS 피드 초기화
        fg = FeedGenerator()
        fg.id(target['url'])
        fg.title(target['title'])
        fg.author({'name': '국가기록원'})
        fg.link(href=target['url'], rel='alternate')
        fg.description(target['desc'])
        fg.language('ko')
        
        # 게시글 목록 파싱 (표 형태)
        rows = soup.select('table tbody tr')
        if not rows:
            rows = soup.select('.board_list tbody tr, .list_wrap > div, ul.list > li')
            
        items_found = 0
        
        for row in rows:
            a_tag = row.find('a')
            if not a_tag:
                continue
                
            # 제목 정제 (이미지에 있는 'N' 아이콘 텍스트 등 제거)
            raw_title = a_tag.get_text(separator=' ', strip=True)
            title = re.sub(r'^(공지|새글|N)\s*', '', raw_title, flags=re.IGNORECASE).strip()
            
            if len(title) < 2:
                continue
                
            href = a_tag.get('href', '')
            onclick = a_tag.get('onclick', '')
            
            # 링크 조립 (자바스크립트 처리 포함)
            if href.startswith('/'):
                link = urljoin(base_url, href)
            elif 'javascript' in href or href == '#' or not href:
                nums = re.findall(r"\d{4,}", onclick)
                if nums:
                    link = f"{target['url']}?id={nums[0]}"
                else:
                    link = f"{target['url']}#{hash(title)}"
            else:
                link = urljoin(target['url'], href)
                
            # 날짜 추출 (형식: 2026-03-18)
            date_str = ""
            date_match = re.search(r'(20\d{2}[-./]\d{2}[-./]\d{2})', row.get_text(separator=' '))
            if date_match:
                date_str = date_match.group(1).replace('.', '-').replace('/', '-')
                
            # RSS 항목 추가 (읽어온 순서대로 차곡차곡)
            fe = fg.add_entry(order='append')
            fe.id(link)
            fe.title(title)
            fe.link(href=link)
            
            if date_str:
                try:
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                    kst = pytz.timezone('Asia/Seoul')
                    dt = kst.localize(dt)
                    fe.pubDate(dt)
                except ValueError:
                    pass
                    
            items_found += 1
            
        fg.rss_file(target['filename'])
        print(f"-> 총 {items_found}개의 게시글 발견, {target['filename']} 생성 완료!\n")
        
    except Exception as e:
        print(f"[{target['title']}] 오류 발생: {e}")
