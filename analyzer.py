import os
import json
import requests
import feedparser
from google import genai
from google.genai import types
import urllib.parse
from datetime import datetime, timedelta
import yfinance as yf

# 設定
CONFIG_FILE = "config.json"
DB_FILE = "data.json"
HISTORY_FILE = "history.json"
RSS_BASE_URL = "https://news.google.com/rss/search?q={}&hl=ja&gl=JP&ceid=JP:ja"

# 企業名からティッカーシンボルのマッピング（日本の主要企業）
COMPANY_TICKER_MAP = {
    "トヨタ自動車": "7203.T",
    "ソニーグループ": "6758.T",
    "キーエンス": "6861.T",
    "三菱UFJフィナンシャルG": "8306.T",
    "東京エレクトロン": "8035.T",
    "ソフトバンクグループ": "9984.T",
    "日立製作所": "6501.T",
    "ファーストリテイリング": "9983.T",
    "任天堂": "7974.T",
    "新光電気工業": "6967.T",
    "伊藤忠商事": "8001.T",
    "三井住友フィナンシャルG": "8316.T",
    "信越化学工業": "4063.T",
    "KDDI": "9433.T",
    "日本電信電話": "9432.T",
    "リクルートホールディングス": "6098.T",
    "ダイキン工業": "6367.T",
    "本田技研工業": "7267.T",
    "武田薬品工業": "4502.T",
    "みずほフィナンシャルG": "8411.T",
    "オリエンタルランド": "4661.T",
    "村田製作所": "6981.T",
    "日本たばこ産業": "2914.T",
    "セブン＆アイ・ホールディングス": "3382.T",
    "デンソー": "6902.T",
    "SMC": "6273.T",
    "富士通": "6702.T",
    "アドバンテスト": "6857.T",
    "三菱商事": "8058.T",
    "HOYA": "7741.T"
}

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

def fetch_stock_price(company_name):
    """企業名から前日と当日の株価を取得"""
    ticker = COMPANY_TICKER_MAP.get(company_name)
    if not ticker:
        print(f"Warning: Ticker not found for {company_name}")
        return None
    
    try:
        stock = yf.Ticker(ticker)
        # 過去2営業日のデータを取得
        hist = stock.history(period="5d")
        if len(hist) < 2:
            print(f"Warning: Not enough data for {company_name} ({ticker})")
            return None
        
        # 最新の2日分のデータを取得
        latest = hist.iloc[-1]
        previous = hist.iloc[-2]
        
        current_price = float(latest['Close'])
        previous_price = float(previous['Close'])
        price_change = current_price - previous_price
        price_change_percent = (price_change / previous_price) * 100
        
        return {
            "ticker": ticker,
            "current_price": current_price,
            "previous_price": previous_price,
            "price_change": price_change,
            "price_change_percent": price_change_percent,
            "date": latest.name.strftime("%Y-%m-%d") if hasattr(latest.name, 'strftime') else str(latest.name)
        }
    except Exception as e:
        # エラーメッセージを確認して、上場廃止の可能性がある場合は警告のみ
        error_msg = str(e)
        if "delisted" in error_msg.lower() or "not found" in error_msg.lower() or "no data found" in error_msg.lower():
            print(f"Warning: Stock data not available for {company_name} ({ticker}) - possibly delisted or symbol not found")
        else:
            print(f"Error fetching stock price for {company_name} ({ticker}): {e}")
        return None

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
            "各企業について、ニュース全体を通しての「株価上昇期待値」を0〜100点で採点（average_score）。",
            "各ニュース記事について、投資への影響度を考慮した「記事ごとのスコア」（0-100）と「理由（30文字以内）」を作成。",
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
            # 記事の公開日を取得（RSSフィードから）
            article_date = datetime.now().strftime("%Y-%m-%d %H:%M")  # デフォルトは収集時刻
            if hasattr(entry, 'published'):
                try:
                    # feedparserが日付を解析している場合
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        article_date = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d %H:%M")
                    else:
                        # 文字列から日付を抽出
                        article_date = entry.published
                except:
                    pass
            
            news_items.append({
                "title": entry.title,
                "snippet": entry.summary,
                "link": entry.link,
                "date": article_date,  # 記事の公開日
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M")  # 収集時刻も保持
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

    # 3. 株価情報を取得
    print("Fetching stock prices...")
    stock_prices = {}
    for company in config:
        company_name = company["name"]
        stock_info = fetch_stock_price(company_name)
        if stock_info:
            stock_prices[company_name] = stock_info

    # 4. 結果のマージと保存
    companies_data = []
    
    # APIのレスポンスと元のリンク情報などを紐付け
    for result in analysis_results:
        # 元のデータ（リンク情報など）を探す
        original_company = next((x for x in batch_input if x["name"] == result.get("company")), None)
        if not original_company:
            continue
        
        company_name = result.get("company")
        predicted_score = result.get("average_score", 0)
        
        # 株価情報とスコアを比較
        stock_info = stock_prices.get(company_name)
        score_evaluation = None
        if stock_info:
            price_change_percent = stock_info["price_change_percent"]
            # スコアと実際の株価変動を比較して評価
            # スコアが高い（50以上）→ 上昇期待、スコアが低い（50未満）→ 下落期待
            # スコアの強度も考慮（50-60:弱い、60-70:中程度、70-80:強い、80-100:非常に強い）
            score_strength = "弱い" if predicted_score < 60 else ("中程度" if predicted_score < 70 else ("強い" if predicted_score < 80 else "非常に強い"))
            
            if predicted_score >= 50:
                # 上昇期待の場合
                if price_change_percent > 0:
                    # 正しく予測（上昇期待で実際に上昇）
                    # スコアの強度と実際の変動率を考慮して精度を計算
                    base_accuracy = 50
                    direction_bonus = 20  # 方向が正しい
                    magnitude_bonus = min(30, abs(price_change_percent) * 3)  # 変動率に応じたボーナス
                    accuracy = min(100, base_accuracy + direction_bonus + magnitude_bonus)
                    
                    # 変動率が1%未満の場合は部分的的中
                    status = "的中" if price_change_percent >= 1.0 else "部分的的中"
                    score_evaluation = {
                        "accuracy": round(accuracy, 1),
                        "prediction": f"上昇予測 ({score_strength})",
                        "actual": f"{price_change_percent:+.2f}%",
                        "status": status
                    }
                else:
                    # 外れ（上昇期待だが実際は下落）
                    # 外れ度合いに応じて精度を下げる
                    penalty = min(50, abs(price_change_percent) * 5)
                    accuracy = max(0, 50 - penalty)
                    score_evaluation = {
                        "accuracy": round(accuracy, 1),
                        "prediction": f"上昇予測 ({score_strength})",
                        "actual": f"{price_change_percent:+.2f}%",
                        "status": "外れ"
                    }
            else:
                # 下落期待の場合
                if price_change_percent < 0:
                    # 正しく予測（下落期待で実際に下落）
                    base_accuracy = 50
                    direction_bonus = 20
                    magnitude_bonus = min(30, abs(price_change_percent) * 3)
                    accuracy = min(100, base_accuracy + direction_bonus + magnitude_bonus)
                    
                    status = "的中" if price_change_percent <= -1.0 else "部分的的中"
                    score_evaluation = {
                        "accuracy": round(accuracy, 1),
                        "prediction": f"下落予測 ({score_strength})",
                        "actual": f"{price_change_percent:+.2f}%",
                        "status": status
                    }
                else:
                    # 外れ（下落期待だが実際は上昇）
                    penalty = min(50, abs(price_change_percent) * 5)
                    accuracy = max(0, 50 - penalty)
                    score_evaluation = {
                        "accuracy": round(accuracy, 1),
                        "prediction": f"下落予測 ({score_strength})",
                        "actual": f"{price_change_percent:+.2f}%",
                        "status": "外れ"
                    }
            
        company_record = {
            "company": company_name,
            "average_score": predicted_score,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "stock_info": stock_info,
            "score_evaluation": score_evaluation,
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
                    "date": original_news["date"],  # 記事の公開日
                    "collected_at": original_news.get("collected_at", original_news["date"])  # 収集時刻
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
    
    # 履歴に追加
    history_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "data": final_output
    }
    
    # 既存の履歴を読み込む
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []
    
    # 新しい履歴を追加（最新が先頭）
    history.insert(0, history_entry)
    
    # 履歴を保存（期限なく全て保持）
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    
    print(f"Analysis complete. Saved data for {len(companies_data)} companies.")
    print(f"History updated. Total entries: {len(history)}")

if __name__ == "__main__":
    main()