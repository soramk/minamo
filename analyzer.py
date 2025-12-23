import os
import json
import requests
import feedparser
from google import genai
from google.genai import types
import urllib.parse
from datetime import datetime

# 設定
CONFIG_FILE = "config.json"
DB_FILE = "data.json"
RSS_BASE_URL = "https://news.google.com/rss/search?q={}&hl=ja&gl=JP&ceid=JP:ja"

# Geminiクライアントは後で初期化
client = None

def init_client():
    global client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        return False
    try:
        client = genai.Client(api_key=api_key)
        return True
    except Exception as e:
        print(f"Error initializing Gemini client: {e}")
        return False

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_news(query):
    encoded_query = urllib.parse.quote(query)
    url = RSS_BASE_URL.format(encoded_query)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        return feed.entries[:3] # 各社最新3件に絞る（トークン節約のため）
    except Exception as e:
        print(f"Error fetching news for {query}: {e}")
        return []

def analyze_batch(companies_news):
    """
    companies_news: [
        {"name": "トヨタ", "news": [{"title": "...", "snippet": "..."}, ...]},
        ...
    ]
    の形式
    """
    
    prompt_content = {
        "instruction": "あなたはプロの証券アナリストです。以下の各企業のニュースを分析し、投資家目線で評価してください。",
        "requirements": [
            "各企業について、ニュース全体を通しての「株価上昇期待値」を1〜10点で採点（average_score）。",
            "各ニュース記事について、投資への影響度を考慮した「記事ごとのスコア」（1-10）と「理由（30文字以内）」を作成。",
            "出力はJSON形式のみ。",
            "JSON構造: [{ 'company': 企業名, 'average_score': 数値, 'news': [{ 'title': 記事タイトル, 'score': 数値, 'reason': 理由 }] }]"
        ],
        "data": companies_news
    }

    prompt_str = json.dumps(prompt_content, ensure_ascii=False, indent=2)

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt_str,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        usage = {}
        if response.usage_metadata:
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "candidates_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count
            }
            
        return json.loads(response.text), usage
    except Exception as e:
        print(f"Error in batch analysis: {e}")
        return [], {}

def main():
    if not init_client():
        return

    try:
        config = load_config()
    except Exception as e:
        print(f"Error loading config.json: {e}")
        return

    # 1. ニュース収集
    print("Fetching news...")
    batch_input = []
    
    for company in config:
        print(f"Checking {company['name']}...")
        entries = fetch_news(company['query'])
        
        news_items = []
        for entry in entries:
            news_items.append({
                "title": entry.title,
                "snippet": entry.summary,
                "link": entry.link,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M") # 収集時刻
            })
        
        if news_items:
            batch_input.append({
                "name": company["name"],
                "news": news_items
            })

    if not batch_input:
        print("No news found.")
        return

    # 2. 一括分析
    print("Analyzing all companies with Gemini...")
    analysis_results, token_usage = analyze_batch([
        {"name": item["name"], "news": [{"title": n["title"], "snippet": n["snippet"]} for n in item["news"]]}
        for item in batch_input
    ])
    
    if token_usage:
        print(f"Token Usage: {token_usage}")

    # 3. 結果のマージと保存
    companies_data = []
    
    # APIのレスポンスと元のリンク情報などを紐付け
    for result in analysis_results:
        # 元のデータ（リンク情報など）を探す
        original_company = next((x for x in batch_input if x["name"] == result.get("company")), None)
        if not original_company:
            continue
            
        company_record = {
            "company": result.get("company"),
            "average_score": result.get("average_score", 0),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "news": []
        }

        # ニュースごとの紐付け (タイトルで簡易マッチング)
        for analyzed_news in result.get("news", []):
            original_news = next((x for x in original_company["news"] if x["title"] == analyzed_news.get("title")), None)
            if original_news:
                company_record["news"].append({
                    "title": original_news["title"],
                    "link": original_news["link"],
                    "score": analyzed_news.get("score", 0),
                    "reason": analyzed_news.get("reason", "N/A"),
                    "date": original_news["date"]
                })
        
        companies_data.append(company_record)

    # 保存データの構築 (メタデータを含める)
    final_output = {
        "metadata": {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "token_usage": token_usage
        },
        "companies": companies_data
    }

    # 保存
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
    
    print(f"Analysis complete. Saved data for {len(companies_data)} companies.")

if __name__ == "__main__":
    main()