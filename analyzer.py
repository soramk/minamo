import os
import json
import requests
import feedparser
from google import genai
from google.genai import types
import urllib.parse
from datetime import datetime

# 設定
TARGET_QUERY = "トヨタ自動車 株価" 
encoded_query = urllib.parse.quote(TARGET_QUERY)
RSS_URL = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"
DB_FILE = "data.json"

# 新しいGeminiクライアントの初期化
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def get_gemini_analysis(title, snippet):
    prompt = f"""
    以下のニュースタイトルと概要から、投資家目線で「株価上昇の期待値」を1〜10点で採点し、その理由を30文字以内で簡潔に述べよ。
    出力はJSON形式のみ: {{"score": 数値, "reason": "理由"}}

    ニュース: {title}
    概要: {snippet}
    """
    try:
        # 新しいSDKでの呼び出し方
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error analyzing: {e}")
        return {"score": 0, "reason": "分析失敗"}

def main():
    print(f"Fetching news for: {TARGET_QUERY}")
    
    # ★追加: ブラウザのふりをする設定 (User-Agent)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        # requestsを使ってデータを取得し、それをfeedparserに渡す
        resp = requests.get(RSS_URL, headers=headers, timeout=10)
        resp.raise_for_status() # エラーならここで止める
        feed = feedparser.parse(resp.content)
    except Exception as e:
        print(f"Network Error: {e}")
        return

    new_entries = []
    
    # 既存データの読み込み
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            existing_urls = {item["link"] for item in existing_data}
    except FileNotFoundError:
        existing_data = []
        existing_urls = set()

    # 記事が取れているか確認
    print(f"Found {len(feed.entries)} entries in RSS.")

    for entry in feed.entries[:5]: # 最新5件
        if entry.link in existing_urls:
            continue

        print(f"Analyzing: {entry.title}")
        analysis = get_gemini_analysis(entry.title, entry.summary)
        
        record = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "title": entry.title,
            "link": entry.link,
            "score": analysis["score"],
            "reason": analysis["reason"]
        }
        new_entries.append(record)

    # 保存処理
    if new_entries:
        updated_data = new_entries + existing_data
        updated_data = updated_data[:100] 
        
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(new_entries)} new entries.")
    else:
        print("No new news found (or all kept).")

if __name__ == "__main__":
    main()