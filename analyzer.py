import os
import json
import requests
import feedparser
from google import genai
from google.genai import types
import urllib.parse
from datetime import datetime, timedelta, timezone
import yfinance as yf

# JSTタイムゾーン（UTC+9）
JST = timezone(timedelta(hours=9))

def now_jst():
    """現在時刻をJSTで取得"""
    return datetime.now(JST)

# 設定
CONFIG_FILE = "config.json"
DATA_DIR = "data"
HISTORY_DIR = os.path.join(DATA_DIR, "history")
DB_FILE = os.path.join(DATA_DIR, "current.json")  # 最新データ
RSS_BASE_URL = "https://news.google.com/rss/search?q={}&hl=ja&gl=JP&ceid=JP:ja"

# ディレクトリを作成
os.makedirs(HISTORY_DIR, exist_ok=True)

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

def update_history_index(current_date):
    """履歴インデックスファイルを更新"""
    index_file = os.path.join(HISTORY_DIR, "index.json")
    
    # 既存のインデックスを読み込む
    existing_dates = set()
    if os.path.exists(index_file):
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                existing_dates = set(json.load(f))
        except:
            pass
    
    # 現在の日付を追加
    existing_dates.add(current_date)
    
    # 実際に存在するファイルのみをインデックスに含める
    if os.path.exists(HISTORY_DIR):
        actual_files = {f.replace('.json', '') for f in os.listdir(HISTORY_DIR) 
                       if f.endswith('.json') and f != 'index.json'}
        existing_dates = existing_dates.intersection(actual_files)
    
    # ソートして保存
    sorted_dates = sorted(existing_dates, reverse=True)
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(sorted_dates, f, indent=2)

def migrate_old_history():
    """既存のhistory.jsonを本日の日付で保存"""
    # ディレクトリを作成
    os.makedirs(HISTORY_DIR, exist_ok=True)
    
    old_history_file = "history.json"
    if not os.path.exists(old_history_file):
        return
    
    try:
        # 既存のhistory.jsonを読み込む
        with open(old_history_file, "r", encoding="utf-8") as f:
            old_history = json.load(f)
        
        if not isinstance(old_history, list) or len(old_history) == 0:
            print("No history data to migrate")
            return
        
        # 本日の日付で保存（JST）
        today = now_jst().strftime("%Y-%m-%d")
        today_file = os.path.join(HISTORY_DIR, f"{today}.json")
        
        # 既存のファイルがある場合はマージ
        if os.path.exists(today_file):
            with open(today_file, "r", encoding="utf-8") as f:
                existing_history = json.load(f)
            # 重複を避けてマージ
            existing_timestamps = {entry["timestamp"] for entry in existing_history}
            new_entries = [entry for entry in old_history if entry["timestamp"] not in existing_timestamps]
            merged_history = new_entries + existing_history
        else:
            merged_history = old_history
        
        # 時系列でソート（最新が先頭）
        merged_history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # 保存
        with open(today_file, "w", encoding="utf-8") as f:
            json.dump(merged_history, f, indent=2, ensure_ascii=False)
        
        print(f"Migrated {len(old_history)} history entries to {today_file}")
        print(f"Total entries in today's file: {len(merged_history)}")
        
        # インデックスを更新
        update_history_index(today)
        
    except Exception as e:
        print(f"Error migrating old history: {e}")
        import traceback
        traceback.print_exc()

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
    # ディレクトリを作成（確実に作成されるように）
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    
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
            article_date = now_jst().strftime("%Y-%m-%d %H:%M")  # デフォルトは収集時刻（JST）
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
                "collected_at": now_jst().strftime("%Y-%m-%d %H:%M")  # 収集時刻も保持（JST）
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
            "updated_at": now_jst().strftime("%Y-%m-%d %H:%M"),
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
            "updated_at": now_jst().strftime("%Y-%m-%d %H:%M"),
            "token_usage": token_usage
        },
        "companies": companies_data
    }

    # ディレクトリを作成（念のため）
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)

    # 保存
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
    
    # 履歴を日付ごとに分割して保存（JST）
    timestamp = now_jst()
    date_str = timestamp.strftime("%Y-%m-%d")
    time_str = timestamp.strftime("%H:%M")
    
    history_entry = {
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M"),
        "data": final_output
    }
    
    # 日付ごとの履歴ファイル
    history_file = os.path.join(HISTORY_DIR, f"{date_str}.json")
    
    # 既存の履歴を読み込む
    daily_history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                daily_history = json.load(f)
                if not isinstance(daily_history, list):
                    print("Warning: History file is not a list, resetting...")
                    daily_history = []
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse history file: {e}, resetting...")
            daily_history = []
        except Exception as e:
            print(f"Warning: Error reading history file: {e}, resetting...")
            daily_history = []
    
    # 新しい履歴を追加（最新が先頭）
    daily_history.insert(0, history_entry)
    
    # 日付ごとの履歴を保存
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(daily_history, f, indent=2, ensure_ascii=False)
        
        # 履歴インデックスを更新
        update_history_index(date_str)
        
        print(f"Analysis complete. Saved data for {len(companies_data)} companies.")
        print(f"History saved to: {os.path.abspath(history_file)}")
        print(f"Daily history entries: {len(daily_history)}")
    except Exception as e:
        print(f"Error saving history file: {e}")
        import traceback
        traceback.print_exc()
        print(f"Analysis complete. Saved data for {len(companies_data)} companies.")

if __name__ == "__main__":
    # 初回実行時に既存のhistory.jsonを移行
    migrate_old_history()
    main()