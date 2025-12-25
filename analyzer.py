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
DATA_DIR = "docs/data"  # GitHub Pages用にdocs/dataに直接保存
HISTORY_DIR = os.path.join(DATA_DIR, "history")
DB_FILE = os.path.join(DATA_DIR, "current.json")  # 最新データ
RSS_BASE_URL = "https://news.google.com/rss/search?q={}&hl=ja&gl=JP&ceid=JP:ja"

# ディレクトリを作成
os.makedirs(DATA_DIR, exist_ok=True)
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
    "HOYA": "7741.T",
    "パナソニック": "6752.T",
    "三菱重工業": "7011.T",
    "日本製鉄": "5401.T",
    "JFEホールディングス": "5411.T",
    "住友化学": "4005.T",
    "三菱ケミカルホールディングス": "4188.T",
    "旭化成": "3407.T",
    "東レ": "3402.T",
    "帝人": "3401.T",
    "住友金属鉱山": "5713.T",
    "三井金属鉱業": "5706.T",
    "住友商事": "8053.T",
    "丸紅": "8002.T",
    "双日": "2768.T",
    "豊田自動織機": "6201.T",
    "コマツ": "6301.T",
    "日立建機": "6305.T",
    "オムロン": "6645.T",
    "三菱電機": "6503.T",
    "富士電機": "6504.T",
    "東芝": "6502.T",
    "シャープ": "6753.T",
    "日本電気": "6701.T",
    "京セラ": "6971.T",
    "TDK": "6762.T",
    "アルプスアルパイン": "6770.T",
    "ローム": "6963.T",
    "ルネサスエレクトロニクス": "6723.T",
    "日亜化学工業": "5393.T",
    "日本電産": "6594.T",
    "ニコン": "7731.T",
    "キヤノン": "7751.T",
    "リコー": "7752.T",
    "セイコーエプソン": "6724.T",
    "スズキ": "7269.T",
    "マツダ": "7261.T",
    "スバル": "7270.T",
    "いすゞ自動車": "7202.T",
    "日産自動車": "7201.T",
    "ブリヂストン": "5108.T",
    "住友ゴム工業": "5110.T",
    "アイシン": "7259.T",
    "トヨタ紡織": "3116.T",
    "日本郵政": "6178.T",
    "JR東日本": "9020.T",
    "JR西日本": "9021.T",
    "JR東海": "9022.T",
    "ANAホールディングス": "9202.T",
    "日本航空": "9201.T",
    "川崎重工業": "7012.T",
    "IHI": "7013.T",
    "住友重機械工業": "6302.T",
    "日立造船": "7004.T",
    "三井物産": "8031.T",
    "住友不動産": "8830.T",
    "三井不動産": "8801.T",
    "三菱地所": "8802.T",
    "野村ホールディングス": "8604.T",
    "大和証券グループ本社": "8601.T",
    "SMBC日興証券": "8609.T",
    "第一生命ホールディングス": "8750.T",
    "日本生命保険": "7181.T",
    "明治安田生命保険": "7182.T",
    "損害保険ジャパン": "8751.T",
    "東京海上ホールディングス": "8766.T",
    "MS&ADインシュアランスグループ": "8725.T",
    "SOMPOホールディングス": "8630.T",
    "日本製紙": "3863.T",
    "王子ホールディングス": "3861.T",
    "花王": "4452.T",
    "資生堂": "4911.T",
    "コーセー": "4922.T",
    "味の素": "2802.T",
    "キッコーマン": "2801.T",
    "日本ハム": "2282.T",
    "明治ホールディングス": "2269.T",
    "森永製菓": "2201.T",
    "カルビー": "2229.T",
    "アサヒグループホールディングス": "2502.T",
    "キリン": "2503.T",
    "サントリーホールディングス": "2587.T",
    "イオン": "8267.T",
    "永旺リテール": "8261.T",
    "ローソン": "2651.T",
    "ファミリーマート": "8028.T",
    "パルコ": "8251.T",
    "高島屋": "8233.T",
    "三越伊勢丹ホールディングス": "3099.T",
    "大塚ホールディングス": "4578.T",
    "アステラス製薬": "4503.T",
    "エーザイ": "4523.T",
    "第一三共": "4568.T",
    "中外製薬": "4519.T",
    "塩野義製薬": "4507.T",
    "オノフィ": "4528.T",
    "テルモ": "4543.T",
    "日本光電工業": "6849.T",
    "日本郵船": "9101.T",
    "商船三井": "9104.T",
    "川崎汽船": "9107.T",
    "ヤマトホールディングス": "9064.T",
    "佐川急便": "9123.T",
    "日本通運": "9062.T",
    "楽天グループ": "4755.T",
    "サイバーエージェント": "4751.T",
    "GMOインターネット": "9449.T",
    "Zホールディングス": "4689.T",
    "ヤフー": "4689.T",
    "メルカリ": "4385.T",
    "ワークスアプリケーションズ": "3751.T",
    "オプティム": "3694.T",
    "日本ガイシ": "5333.T",
    "AGC": "5201.T",
    "太平洋セメント": "5233.T",
    "住友大阪セメント": "5232.T",
    "TOTO": "5332.T",
    "LIXIL": "5938.T",
    "積水ハウス": "1928.T",
    "大和ハウス工業": "1925.T",
    "セキスイハイム": "1924.T",
    "大林組": "1802.T",
    "鹿島建設": "1812.T",
    "清水建設": "1803.T",
    "大成建設": "1801.T",
    "竹中工務店": "1810.T",
    "前田建設工業": "1820.T",
    "東急": "9005.T",
    "東武鉄道": "9001.T",
    "西武ホールディングス": "9024.T",
    "近鉄グループホールディングス": "9041.T",
    "京王電鉄": "9007.T",
    "小田急電鉄": "9009.T",
    "京成電鉄": "9009.T",
    "東京ガス": "9531.T",
    "大阪ガス": "9532.T",
    "東邦ガス": "9533.T",
    "東京電力ホールディングス": "9501.T",
    "関西電力": "9503.T",
    "中部電力": "9502.T",
    "九州電力": "9508.T",
    "中国電力": "9504.T",
    "四国電力": "9507.T",
    "北海道電力": "9509.T",
    "東北電力": "9506.T",
    "北陸電力": "9505.T",
    "沖縄電力": "9511.T"
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

def migrate_old_data():
    """既存のdata/フォルダの内容をdocs/data/に移行"""
    old_data_dir = "data"
    if not os.path.exists(old_data_dir):
        return
    
    try:
        # 既存のdata/current.jsonを移行
        old_current = os.path.join(old_data_dir, "current.json")
        if os.path.exists(old_current):
            import shutil
            shutil.copy2(old_current, DB_FILE)
            print(f"Migrated {old_current} to {DB_FILE}")
        
        # 既存のdata/history/を移行
        old_history_dir = os.path.join(old_data_dir, "history")
        if os.path.exists(old_history_dir):
            import shutil
            for file in os.listdir(old_history_dir):
                if file.endswith('.json'):
                    old_file = os.path.join(old_history_dir, file)
                    new_file = os.path.join(HISTORY_DIR, file)
                    if not os.path.exists(new_file):
                        shutil.copy2(old_file, new_file)
                        print(f"Migrated {old_file} to {new_file}")
    except Exception as e:
        print(f"Error migrating old data: {e}")

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

def fetch_news(query, max_items=5, days_ago=6):
    """
    指定されたクエリでニュースを取得し、指定された日数以内のもののみを返す
    """
    encoded_query = urllib.parse.quote(query)
    url = RSS_BASE_URL.format(encoded_query)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    cutoff_date = now_jst() - timedelta(days=days_ago)
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        
        filtered_entries = []
        for entry in feed.entries:
            # 公開日を解析
            published_dt = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_dt = datetime(*entry.published_parsed[:6]).replace(tzinfo=timezone.utc).astimezone(JST)
            elif hasattr(entry, 'published'):
                try:
                    # 一般的な形式のパース
                    published_dt = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=timezone.utc).astimezone(JST)
                except:
                    pass
            
            # 日付が取得できない、または期限内の場合のみ採用
            if published_dt is None or published_dt >= cutoff_date:
                filtered_entries.append(entry)
            
            if len(filtered_entries) >= max_items:
                break
                
        return filtered_entries
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

def extract_first_json_block(text):
    """
    文字列から最初に見つかった JSON ブロック（[...] または {...}）を抽出する。
    Extra data エラーを防ぐためのガード。
    """
    import re
    # 配列を優先して探す
    array_match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
    if array_match:
        return array_match.group(0)
    
    # オブジェクトを探す
    object_match = re.search(r'\{\s*".*"\s*:.*\}', text, re.DOTALL)
    if object_match:
        return object_match.group(0)
    
    return text

def analyze_batch(companies_news):
    """
    companies_news: [
        {"name": "トヨタ", "news": [{"title": "...", "snippet": "..."}, ...]},
        ...
    ]
    の形式
    """
    
    prompt_content = {
        "instruction": "あなたはプロの証券アナリストです。以下の各企業の最新ニュース（過去6日以内）を分析し、株価に与える影響を評価してください。",
        "requirements": [
            "各企業について、直近のニュースに基づいた「株価上昇期待値」を0〜100点で採点（average_score）。",
            "50点（中立）を基準とし、ポジティブならば高く、ネガティブならば低く設定してください。",
            "特に直近2-3日の速報性のある情報を重視すること。",
            "各ニュース記事について、投資判断における重要性を反映した「記事ごとのスコアリング」（0-100）と「具体的な理由（30文字以内）」を作成。",
            "出力はJSON形式のみとし、余計な説明は省くこと。",
            "JSON構造: [{ 'company': 企業名, 'average_score': 数値, 'news': [{ 'title': 記事タイトル, 'score': 数値, 'reason': 理由 }] }]"
        ],
        "data": companies_news
    }

    prompt_str = json.dumps(prompt_content, ensure_ascii=False, indent=2)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp", # 最新モデルを使用
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
        
        # 堅牢なパース処理
        clean_text = extract_first_json_block(response.text)
        return json.loads(clean_text), usage
    except Exception as e:
        print(f"Error in batch analysis: {e}")
        # パースエラーの場合、レスポンスの冒頭を出力してデバッグしやすくする
        if hasattr(response, 'text'):
            print(f"Raw response (first 100 chars): {response.text[:100]}...")
        return [], {}

def main():
    try:
        # ディレクトリを作成（確実に作成されるように）
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(HISTORY_DIR, exist_ok=True)
        
        if not init_client():
            print("Error: Failed to initialize Gemini client")
            return

        try:
            config = load_config()
        except Exception as e:
            print(f"Error loading config.json: {e}")
            import traceback
            traceback.print_exc()
            return

        if not config or len(config) == 0:
            print("Error: config.json is empty or invalid")
            return

        print(f"Loaded {len(config)} companies from config.json")

        # 1. ニュース収集
        print("Fetching news...")
        batch_input = []
        
        for company in config:
            print(f"Checking {company['name']}...")
            
            # 複数のクエリで検索（会社名、会社名＋株価、会社名＋最新）
            queries = [
                company['name'],
                f"{company['name']} 株価",
                f"{company['name']} 決算 ニュース",
                f"{company['name']} 経営戦略"
            ]
            
            all_entries = []
            seen_links = set()
            
            for query in queries:
                entries = fetch_news(query, max_items=3, days_ago=6)
                for entry in entries:
                    if entry.link not in seen_links:
                        all_entries.append(entry)
                        seen_links.add(entry.link)
                
                if len(all_entries) >= 5: # 1社最大5件
                    break
            
            news_items = []
            for entry in all_entries:
                # 記事の公開日を取得（RSSフィードから）
                article_date = now_jst().strftime("%Y-%m-%d %H:%M")  # デフォルト
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        dt = datetime(*entry.published_parsed[:6]).replace(tzinfo=timezone.utc).astimezone(JST)
                        article_date = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                
                news_items.append({
                    "title": entry.title,
                    "snippet": getattr(entry, 'summary', ''),
                    "link": entry.link,
                    "date": article_date,
                    "collected_at": now_jst().strftime("%Y-%m-%d %H:%M")
                })
            
            if news_items:
                batch_input.append({
                    "name": company["name"],
                    "news": news_items
                })

        if not batch_input:
            print("No news found.")
            return

        # 2. 一括分析（チャンク分けして実行）
        print(f"Analyzing {len(batch_input)} companies with Gemini in chunks...")
        analysis_results = []
        token_usage = {"prompt_tokens": 0, "candidates_tokens": 0, "total_tokens": 0}
        
        chunk_size = 20
        chunks = [batch_input[i:i + chunk_size] for i in range(0, len(batch_input), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} companies)...")
            chunk_input = [
                {"name": item["name"], "news": [{"title": n["title"], "snippet": n["snippet"]} for n in item["news"]]}
                for item in chunk
            ]
            
            chunk_results, chunk_usage = analyze_batch(chunk_input)
            
            if chunk_results:
                analysis_results.extend(chunk_results)
            
            if chunk_usage:
                token_usage["prompt_tokens"] += chunk_usage.get("prompt_tokens", 0)
                token_usage["candidates_tokens"] += chunk_usage.get("candidates_tokens", 0)
                token_usage["total_tokens"] += chunk_usage.get("total_tokens", 0)
        
        if not analysis_results or len(analysis_results) == 0:
            print("Error: No analysis results returned from Gemini API")
            print(f"Batch input had {len(batch_input)} companies")
            return

        print(f"Analysis completed for {len(analysis_results)} companies")

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
            
            # 業種情報を取得
            sector = None
            original_config = next((c for c in config if c["name"] == company_name), None)
            if original_config and "sector" in original_config:
                sector = original_config["sector"]
            
            company_record = {
                "company": company_name,
                "sector": sector,
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

        # データが空でないことを確認
        if len(companies_data) == 0:
            print("Error: No company data to save. Analysis may have failed.")
            return

        # 保存
        print(f"Saving data for {len(companies_data)} companies to {DB_FILE}")
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(final_output, f, indent=2, ensure_ascii=False)
            print(f"Successfully saved current.json to {os.path.abspath(DB_FILE)}")
        except Exception as e:
            print(f"Error saving current.json: {e}")
            import traceback
            traceback.print_exc()
            return
        
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
    
    except Exception as e:
        print(f"Error in main(): {e}")
        import traceback
        traceback.print_exc()
        # エラーが発生しても空のデータを保存しない
        return

if __name__ == "__main__":
    # 初回実行時に既存のdata/フォルダを移行
    migrate_old_data()
    # 既存のhistory.jsonを移行
    migrate_old_history()
    main()