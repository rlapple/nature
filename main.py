import argparse
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from llm import summarize_with_llm, translate_with_llm,classify_paper_with_llm
from export import export_markdown_by_category
import time
import random
BASE_URL = "https://www.nature.com"


def _parse_nature_pub_date(text: str):
    """
    Try to parse Nature's date text into an aware datetime (UTC).
    Returns None if unparseable.
    Examples: '27 December 2025', '27 Dec 2025', '2025-12-27', ISO8601 in datetime attr.
    """
    if not text:
        return None
    s = re.sub(r"\s+", " ", text.strip())

    # Prefer ISO8601 (e.g. '2025-12-27', '2025-12-27T10:00:00Z')
    try:
        iso = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass

    fmts = (
        "%d %B %Y",   # 27 December 2025
        "%d %b %Y",   # 27 Dec 2025
        "%Y-%m-%d",   # 2025-12-27
    )
    for fmt in fmts:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def _month_range_utc(month_arg: str | None):
    """
    month_arg: 'YYYY-MM' or None (=> current month in UTC)
    returns (month_start_utc, next_month_start_utc, label)
    """
    now = datetime.now(timezone.utc)
    if not month_arg:
        y, m = now.year, now.month
    else:
        mobj = re.fullmatch(r"(\d{4})-(\d{2})", month_arg.strip())
        if not mobj:
            raise ValueError("month must be in YYYY-MM format, e.g. 2025-12")
        y, m = int(mobj.group(1)), int(mobj.group(2))
        if not (1 <= m <= 12):
            raise ValueError("month must be between 01 and 12")

    month_start = datetime(y, m, 1, 0, 0, 0, tzinfo=timezone.utc)
    if m == 12:
        next_month_start = datetime(y + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    else:
        next_month_start = datetime(y, m + 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    return month_start, next_month_start, f"{y:04d}-{m:02d}"


def fetch_nature_research_articles(page=1):
    url = f"{BASE_URL}/nature/research-articles?page={page}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    results = []

    # 每个论文条目通常在 article 标签
    for item in soup.find_all("article"):
        # 标题
        h3 = item.find("h3")
        if not h3:
            continue
        title = h3.get_text(strip=True)

        # 链接
        #
        a = h3.find("a")
        if not a:
            continue
        rel_link = a.get("href")
        link = BASE_URL + rel_link

        # 发表日期：优先取 datetime 属性（更稳定），否则取文本
        date_tag = item.find("time")
        pub_date = ""
        if date_tag:
            pub_date = date_tag.get("datetime") or date_tag.get_text(strip=True) or ""
        results.append({
            "title": title,
            "url": link,
            "date": pub_date,
            "page": page
        })
    return results


def fetch_nature_research_articles_for_month(month: str | None = None, max_pages: int = 300):
    if max_pages < 1:
        raise ValueError("max_pages must be >= 1")

    month_start, next_month_start, label = _month_range_utc(month)

    aggregated = []
    for page in range(1, max_pages + 1):
        try:
            items = fetch_nature_research_articles(page=page)
        except requests.HTTPError as exc:
            print(f"Skipping page {page} due to HTTPError: {exc}")
            continue
        except requests.RequestException as exc:
            print(f"Skipping page {page} due to network error: {exc}")
            continue

        if not items:
            break

        any_parsed = False
        all_older_than_month_start = True

        for it in items:
            dt = _parse_nature_pub_date(it.get("date", ""))
            if dt is None:
                continue

            any_parsed = True
            if month_start <= dt < next_month_start:
                aggregated.append(it)

            if dt >= month_start:
                all_older_than_month_start = False

        # 可解析日期都早于该月月初 => 后续更旧，停止
        if any_parsed and all_older_than_month_start:
            break

    return aggregated, label





def fetch_nature_abstract(url: str, timeout: int = 15) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    # 优先：标准 Abstract 区块
    abs_div = soup.find("div", id="Abs1-content")
    if abs_div:
        paras = [p.get_text(" ", strip=True) for p in abs_div.find_all("p")]
        return "\n".join(paras)

    # 兜底：新版结构
    for section in soup.find_all("section"):
        h2 = section.find("h2")
        if h2 and "abstract" in h2.get_text(strip=True).lower():
            content = section.find("div", class_="c-article-section__content")
            if content:
                paras = [p.get_text(" ", strip=True) for p in content.find_all("p")]
                return "\n".join(paras)

    return ""


def fetch_nature_main_content(url: str, timeout: int = 15) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    # 不要picture，只要正文
    main_div = soup.find("div", class_="c-article-section__content", id="Sec1-content")
    if main_div:
        paras = [p.get_text(" ", strip=True) for p in main_div.find_all("p")]
        
        return "\n".join(paras)

    return ""



from collections import defaultdict

def group_papers_by_category(papers):
    groups = defaultdict(list)
    for p in papers:
        groups[p.get("category", "Other")].append(p)
    return groups


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch Nature research articles for a specified month (default: current month).")
    parser.add_argument("--month", type=str, default=None, help="Target month in YYYY-MM (default: current month)")
    parser.add_argument("--max-pages", type=int, default=30, help="Max pages to scan (safety cap)")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        papers, label = fetch_nature_research_articles_for_month(month=args.month, max_pages=args.max_pages)
    except ValueError as exc:
        print(f"Invalid input: {exc}")
        return

    if not papers:
        print(f"No papers found for month {label}.")
        return

    # 可选：按日期倒序（解析失败的放最后，保持原样）
    def _sort_key(p):
        dt = _parse_nature_pub_date(p.get("date", ""))
        return dt or datetime.min.replace(tzinfo=timezone.utc)

    papers.sort(key=_sort_key, reverse=True)

    # papers = papers[:1]
    for p in papers:
        abstract = fetch_nature_abstract(p['url'])
        time.sleep(random.uniform(1, 2))  # 避免请求过快
        main_content = fetch_nature_main_content(p['url'])

        content = abstract + "\n" + main_content

        # 1. 分类（只做一次）
        category = classify_paper_with_llm(p['title'], abstract)
        p["category"] = category

        # 2. 总结
        summary = summarize_with_llm(p['title'], content)
        p["summary"] = summary

        # 3. 标题翻译
        translated_title = translate_with_llm(p['title'], target_language="Chinese")
        p["translated_title"] = translated_title
        

    groups = group_papers_by_category(papers)

    md_text = export_markdown_by_category(groups, label)

    output_path = f"nature_{label}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_text)

    print(f"Markdown exported to {output_path}")


if __name__ == "__main__":
    main()
