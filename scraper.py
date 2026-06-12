#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
baha-home-sync — Bahamut 小屋 creation scraper.

Fetches all PUBLIC creations from a Bahamut creator's 小屋 (home.gamer.com.tw),
converts each article to Markdown, and writes them to an output directory for
syncing to GitHub.

Data sources:
  - List API : https://api.gamer.com.tw/home/v2/creation_list.php?owner=<id>&page=<n>
  - Article  : https://home.gamer.com.tw/artwork.php?sn=<csn>

Only publicly visible articles are fetched; login-/coin-locked or deleted ones
are skipped and recorded in scrape_state.json.

Usage:
  python scraper.py --owner <owner_id> --out <output_dir>
"""
import argparse
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

API_LIST = "https://api.gamer.com.tw/home/v2/creation_list.php"
ARTWORK = "https://home.gamer.com.tw/artwork.php?sn={sn}"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TPE = timezone(timedelta(hours=8))


def make_session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA,
                      "Accept-Language": "zh-TW,zh;q=0.9"})
    return s


def fetch_list(session, owner):
    items = []
    page = 1
    total_page = 1
    while page <= total_page:
        r = session.get(API_LIST,
                        params={"owner": owner, "page": page},
                        timeout=30)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"Error: {data['error']}")
        d = data["data"]
        total_page = int(d.get("totalPage", 1))
        for it in d.get("list", []):
            items.append({
                "csn": str(it["csn"]),
                "title": it.get("title", "").strip(),
                "category": it.get("categoryName", "").strip(),
                "gp": it.get("gp", 0),
                "visit": it.get("visit", 0),
                "userid": it.get("userid", owner),
            })
        print(f"Page: {page}/{total_page}, total: {len(items)}")
        page += 1
        time.sleep(0.8)
    return items


def fetch_article(session, csn):
    r = session.get(ARTWORK.format(sn=csn), timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    content = soup.select_one("#article_content")
    if content is None:
        return None

    h1 = soup.select_one("h1.article-title")
    title = h1.get_text(strip=True) if h1 else ""

    date_str = ""
    intro = soup.select_one(".article-intro")
    if intro:
        m = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
                      intro.get_text(" ", strip=True))
        if m:
            date_str = m.group(0)

    author = ""
    a = soup.select_one(".article-intro a.caption-text")
    if a:
        author = a.get_text(strip=True)

    for tag in content.select("script, style, ins, .ad-feedback"):
        tag.decompose()

    for h in content.select("h1, h2, h3, h4, h5, h6"):
        if h.find("img"):
            h.unwrap()
        elif not h.get_text(strip=True):
            h.decompose()

    return {
        "title": title,
        "date": date_str,
        "author": author,
        "content_html": str(content),
    }


def html_to_markdown(html):
    body = md(html, heading_style="ATX", bullets="-",
              strip=["span"])
    body = re.sub(r"(?:^[ \t]*[-*_]{3,}[ \t]*\n+){2,}", "---\n\n", body,
                  flags=re.MULTILINE)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body


def slugify(title, csn):
    s = re.sub(r"[^\w一-鿿]+", "-", title, flags=re.UNICODE)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    s = s[:60] if s else "untitled"
    return f"{csn}-{s}"


def yaml_escape(v):
    v = str(v).replace('"', '\\"')
    return f'"{v}"'


def write_markdown(item, art, out_posts):
    fname = slugify(item["title"] or art.get("title", ""), item["csn"]) + ".md"
    path = os.path.join(out_posts, fname)
    url = f"https://home.gamer.com.tw/artwork.php?sn={item['csn']}"
    title = item["title"] or art.get("title", "")
    fm = [
        "---",
        f"title: {yaml_escape(title)}",
        f"author: {yaml_escape(art.get('author') or item.get('userid',''))}",
        f"date: {yaml_escape(art.get('date',''))}",
        f"category: {yaml_escape(item.get('category',''))}",
        f"baha_sn: {yaml_escape(item['csn'])}",
        f"source_url: {yaml_escape(url)}",
        f"gp: {item.get('gp',0)}",
        f"visit: {item.get('visit',0)}",
        "---",
        "",
        f"# {title}",
        "",
        f"> 原文：[{url}]({url}) ｜ 分類：{item.get('category','')} ｜ "
        f"發表：{art.get('date','')}",
        "",
        html_to_markdown(art["content_html"]),
        "",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(fm))
    return fname


def write_index(owner, written, out_dir):
    written = sorted(written, key=lambda x: x["date"], reverse=True)
    now = datetime.now(TPE).strftime("%Y-%m-%d %H:%M:%S %Z")
    lines = [
        f"# 巴哈姆特小屋創作備份 — {owner}",
        "",
        f"由 [scraper.py](scraper.py) 自動從 "
        f"[{owner} 的小屋](https://home.gamer.com.tw/{owner}) 抓取公開創作，"
        "轉為 Markdown 後同步至本倉庫。",
        "",
        f"- 文章數：**{len(written)}** 篇",
        f"- 最後更新：{now}",
        "",
        "| 日期 | 標題 | 分類 | GP | 人氣 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for w in written:
        lines.append(
            f"| {w['date'][:10]} | [{w['title']}](posts/{w['file']}) "
            f"| {w['category']} | {w['gp']} | {w['visit']} |")
    lines.append("")
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description="巴哈姆特小屋創作 → Markdown")
    ap.add_argument("--owner", required=True, help="小屋帳號 ID (owner)")
    ap.add_argument("--out", default=".", help="輸出目錄（git repo 根目錄）")
    ap.add_argument("--delay", type=float, default=1.0,
                    help="每篇文章之間的延遲秒數（禮貌爬蟲）")
    args = ap.parse_args()

    out_dir = os.path.abspath(args.out)
    out_posts = os.path.join(out_dir, "posts")
    os.makedirs(out_posts, exist_ok=True)

    session = make_session()
    print(f"[1/3] 抓取 {args.owner} 的創作列表 …")
    items = fetch_list(session, args.owner)
    print(f"  共 {len(items)} 篇創作")

    print(f"[2/3] 逐篇抓取全文並轉 Markdown …")
    written, skipped = [], []
    for i, it in enumerate(items, 1):
        try:
            art = fetch_article(session, it["csn"])
        except Exception as e:
            print(f"  [{i}/{len(items)}] sn={it['csn']} 失敗：{e}")
            skipped.append({**it, "reason": str(e)})
            continue
        if art is None:
            print(f"  [{i}/{len(items)}] sn={it['csn']} 略過（非公開／鎖文）")
            skipped.append({**it, "reason": "non-public"})
            continue
        fname = write_markdown(it, art, out_posts)
        written.append({**it, "file": fname,
                        "date": art.get("date", ""),
                        "title": it["title"] or art.get("title", "")})
        print(f"  [{i}/{len(items)}] sn={it['csn']} → posts/{fname}")
        time.sleep(args.delay)

    print(f"[3/3] 產生索引 README.md …")
    write_index(args.owner, written, out_dir)

    summary = {
        "owner": args.owner,
        "scraped_at": datetime.now(TPE).isoformat(),
        "total": len(items),
        "written": len(written),
        "skipped": len(skipped),
        "skipped_items": skipped,
    }
    with open(os.path.join(out_dir, "scrape_state.json"), "w",
              encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()