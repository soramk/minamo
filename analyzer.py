import os
import json
import feedparser
import google.generativeai as genai
import urllib.parse # ★追加: URL変換用ライブラリ
from datetime import datetime

# 設定
TARGET_QUERY = "トヨタ自動車 株価" 

# ★変更: 日本語やスペースをURLで使える文字に変換する
encoded_query = urllib.parse.quote(TARGET_QUERY)
RSS_URL = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"

DB_FILE = "data.json"

# Geminiの設定
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# ... (以下、変更なし。get_gemini_analysis 関数などそのまま) ...

def get_gemini_analysis(title, snippet):
    # モデル指定を少し変更（念のため最新のモデル名に近づける）
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""
    以下のニュースタイトルと概要から、投資家目線で「株価上昇の期待値」を1〜10点で採点し、その理由を30文字以内で簡潔に述べよ。
    出力はJSON形式のみ: {{"score": 数値, "reason": "理由"}}

    ニュース: {title}
    概要: {snippet}
    """
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        print(f"Error: {e}")
        # エラー時は安全なデフォルト値を返す
        return {"score": 0, "reason": "分析失敗"}

def main():
    # 1. ニュース取得
    print(f"Fetching news for: {TARGET_QUERY} (Encoded: {encoded_query})") # ログ用に変更
    feed = feedparser.parse(RSS_URL)
    
    # ... (以下、変更なし) ...
    
    new_entries = []
    
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            existing_urls = {item["link"] for item in existing_data}
    except FileNotFoundError:
        existing_data = []
        existing_urls = set()

    # 2. 新着記事を解析
    # ニュースが取れなかった場合のガードを追加
    if not feed.entries:
        print("No entries found in RSS.")
        return

    for entry in feed.entries[:5]:
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

    # 3. 保存
    if new_entries:
        updated_data = new_entries + existing_data
        updated_data = updated_data[:100] 
        
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(new_entries)} new entries.")
    else:
        print("No new news found.")

if __name__ == "__main__":
    main()