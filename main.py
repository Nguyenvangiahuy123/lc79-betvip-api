#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Flask dự đoán Tài Xỉu SIÊU VIP - Version 9.2 ULTIMATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✧ 25 LOẠI CẦU CHUẨN XÁC NHẤT
✧ 30 THUẬT TOÁN DỰ ĐOÁN CAO CẤP
✧ 12 TÍN HIỆU BẺ CẦU THÔNG MINH
✧ HỖ TRỢ 8 GAME: LC79 (TX/MD5), BETVIP (TX/MD5), XENGLIVE (TX/MD5), XOCDIA88 (TX/MD5)
✧ AUTO PING MỖI 1 PHÚT ĐỂ GIỮ KẾT NỐI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import sys
import math
import threading
import time
import requests
from flask import Flask, request, jsonify
from collections import defaultdict, deque
from datetime import datetime

app = Flask(__name__)

# ================= CONFIG SIÊU VIP =================
AUTH_KEY = "apihdx"
USER_ID = "@Meowz_Pro"
ALGO_NAME = "HuyDaiXu SIÊU VIP - Ultimate Prediction Engine v9.2"

# Cấu hình API các game
GAME_CONFIG = {
    "lc79_tx": {
        "game_key": "LC79_TX",
        "api_url": "https://wtx.tele68.com/v1/tx/sessions",
        "name": "LC79 Tài Xỉu",
        "type": "legacy"
    },
    "lc79_md5": {
        "game_key": "LC79_MD5",
        "api_url": "https://wtxmd52.tele68.com/v1/txmd5/sessions",
        "name": "LC79 MD5",
        "type": "legacy"
    },
    "betvip_tx": {
        "game_key": "BETVIP_TX",
        "api_url": "https://wtx.macminim6.online/v1/tx/sessions",
        "name": "BETVIP Tài Xỉu",
        "type": "legacy"
    },
    "betvip_md5": {
        "game_key": "BETVIP_MD5",
        "api_url": "https://wtxmd52.macminim6.online/v1/txmd5/sessions",
        "name": "BETVIP MD5",
        "type": "legacy"
    },
    "xenglive_tx": {
        "game_key": "XENGLIVE_TX",
        "api_url": "https://taixiu.backend-98423498294223x1.online/api/luckydice/GetSoiCau",
        "name": "XengLive Tài Xỉu",
        "type": "new"
    },
    "xenglive_md5": {
        "game_key": "XENGLIVE_MD5",
        "api_url": "https://taixiumd5.backend-98423498294223x1.online/api/md5luckydice/GetSoiCau",
        "name": "XengLive MD5",
        "type": "new"
    },
    "xocdia88_tx": {
        "game_key": "XOCDIA88_TX",
        "api_url": "https://taixiu.system32-cloudfare-356783752985678522.monster/api/luckydice/GetSoiCau",
        "name": "XocDia88 Tài Xỉu",
        "type": "new"
    },
    "xocdia88_md5": {
        "game_key": "XOCDIA88_MD5",
        "api_url": "https://taixiumd5.system32-cloudfare-356783752985678522.monster/api/md5luckydice/GetSoiCau",
        "name": "XocDia88 MD5",
        "type": "new"
    }
}

# Lưu trữ độ chính xác của từng thuật toán
algo_accuracy = defaultdict(lambda: {'correct': 0, 'total': 0, 'weight': 70, 'recent_performance': deque(maxlen=20)})
actual_history = defaultdict(lambda: deque(maxlen=100))
game_cache = {}
cache_lock = threading.Lock()

# ================= FUNCTIONS CƠ BẢN =================
def fetch_data(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Lỗi fetch {url}: {e}", file=sys.stderr)
        return None

def fetch_and_cache(game_id):
    config = GAME_CONFIG.get(game_id)
    if not config:
        return None
    data = fetch_data(config['api_url'])
    if data is not None:
        with cache_lock:
            game_cache[game_id] = {'data': data, 'timestamp': datetime.now().isoformat()}
    return data

def get_cached_data(game_id):
    with cache_lock:
        cached = game_cache.get(game_id)
        if cached:
            return cached['data']
    return fetch_and_cache(game_id)

def parse_session(item, game_type):
    if game_type == "legacy":
        result_raw = item.get("resultTruyenThong", "").upper()
        if "TAI" in result_raw:
            result = "T"
        elif "XIU" in result_raw:
            result = "X"
        else:
            result = None
        point = item.get("point", 0)
        dices = item.get("dices", [0,0,0])
        return result, point, dices, item.get("id")
    else:
        bet_side = item.get("BetSide")
        if bet_side == 0:
            result = "T"
        elif bet_side == 1:
            result = "X"
        else:
            result = None
        point = item.get("DiceSum", 0)
        dices = [item.get("FirstDice", 0), item.get("SecondDice", 0), item.get("ThirdDice", 0)]
        session_id = item.get("SessionId")
        return result, point, dices, session_id

def build_history(data_list, game_type, max_len=100):
    if not data_list:
        return "", []
    if isinstance(data_list, dict) and 'list' in data_list:
        items = data_list['list']
    else:
        items = data_list
    recent = items[:max_len]
    recent.reverse()
    history = ""
    totals = []
    for item in recent:
        result, point, _, _ = parse_session(item, game_type)
        if result:
            history += result
            totals.append(point)
    return history, totals

def moving_average(data, window):
    if len(data) < window:
        return sum(data) / len(data) if data else 0
    return sum(data[-window:]) / window

def standard_deviation(data, mean=None):
    if not data:
        return 0
    if mean is None:
        mean = sum(data) / len(data)
    variance = sum((x - mean) ** 2 for x in data) / len(data)
    return math.sqrt(variance)

# ================= 25 LOẠI CẦU =================
class UltimatePatternDetector:
    @staticmethod
    def detect_bet(history):
        if len(history) < 2:
            return None
        last = history[-1]
        run = 1
        for i in range(len(history)-2, -1, -1):
            if history[i] == last:
                run += 1
            else:
                break
        if run >= 10:
            return {'name': f"🔥 Bệt {run} (BẺ GẤP)", 'confidence': 90, 'next': 'X' if last == 'T' else 'T', 'weight': 95}
        elif run >= 8:
            return {'name': f"⚠️ Bệt {run} (BẺ CẦU)", 'confidence': 85, 'next': 'X' if last == 'T' else 'T', 'weight': 85}
        elif run >= 6:
            return {'name': f"📈 Bệt {run} (CẢNH BÁO)", 'confidence': 75, 'next': last, 'weight': 75}
        elif run >= 4:
            return {'name': f"📊 Bệt {run}", 'confidence': 65, 'next': last, 'weight': 70}
        elif run >= 2:
            return {'name': f"📉 Bệt {run}", 'confidence': 55, 'next': last, 'weight': 60}
        return None

    @staticmethod
    def detect_1_1(history):
        if len(history) >= 4 and history[-4:] in ("TXTX", "XTXT"):
            return {'name': "⚡ Cầu 1-1 (Zigzag)", 'confidence': 88, 'next': 'X' if history[-1] == 'T' else 'T', 'weight': 85}
        return None

    @staticmethod
    def detect_2_2(history):
        if len(history) >= 4 and history[-4:] in ("TTXX", "XXTT"):
            next_pred = 'T' if history[-2:] in ("TT", "XT") else 'X'
            return {'name': "🎯 Cầu 2-2 (Kép đôi)", 'confidence': 82, 'next': next_pred, 'weight': 80}
        return None

    @staticmethod
    def detect_3_3(history):
        if len(history) >= 6 and history[-6:] in ("TTTXXX", "XXXTTT"):
            next_pred = 'X' if history[-3:] == "TTT" else 'T'
            return {'name': "🎲 Cầu 3-3 (Kép ba)", 'confidence': 78, 'next': next_pred, 'weight': 75}
        return None

    @staticmethod
    def detect_1_2(history):
        patterns = {"TXX": "T", "XTT": "X"}
        for pat, nxt in patterns.items():
            if len(history) >= len(pat) and history[-len(pat):] == pat:
                return {'name': f"🌀 Cầu 1-2 ({pat})", 'confidence': 72, 'next': nxt, 'weight': 70}
        return None

    @staticmethod
    def detect_2_1(history):
        patterns = {"TTX": "X", "XXT": "T"}
        for pat, nxt in patterns.items():
            if len(history) >= len(pat) and history[-len(pat):] == pat:
                return {'name': f"🌀 Cầu 2-1 ({pat})", 'confidence': 72, 'next': nxt, 'weight': 70}
        return None

    @staticmethod
    def detect_1_2_3(history):
        if len(history) >= 6:
            last6 = history[-6:]
            if last6 == "TXXTTT":
                return {'name': "🏆 Cầu 1-2-3 (T)", 'confidence': 77, 'next': 'X', 'weight': 75}
            if last6 == "XTTXXX":
                return {'name': "🏆 Cầu 1-2-3 (X)", 'confidence': 77, 'next': 'T', 'weight': 75}
        return None

    @staticmethod
    def detect_3_2_1(history):
        if len(history) >= 6:
            last6 = history[-6:]
            if last6 == "TTTXXT":
                return {'name': "🏆 Cầu 3-2-1 (T)", 'confidence': 77, 'next': 'X', 'weight': 75}
            if last6 == "XXXTTX":
                return {'name': "🏆 Cầu 3-2-1 (X)", 'confidence': 77, 'next': 'T', 'weight': 75}
        return None

    @staticmethod
    def detect_triangle(history):
        if len(history) >= 5:
            last5 = history[-5:]
            if last5 == "TXTXT":
                return {'name': "🔺 Cầu tam giác T (1-2-1)", 'confidence': 80, 'next': 'X', 'weight': 78}
            if last5 == "XTXTX":
                return {'name': "🔺 Cầu tam giác X (2-1-2)", 'confidence': 80, 'next': 'T', 'weight': 78}
        if len(history) >= 7:
            last7 = history[-7:]
            if last7 == "TXTXTXT":
                return {'name': "🔺🔺 Cầu tam giác mở rộng T", 'confidence': 85, 'next': 'X', 'weight': 82}
            if last7 == "XTXTXTX":
                return {'name': "🔺🔺 Cầu tam giác mở rộng X", 'confidence': 85, 'next': 'T', 'weight': 82}
        return None

    @staticmethod
    def detect_phase_shift(history):
        if len(history) >= 5:
            last5 = history[-5:]
            if last5 == "TTXXX":
                return {'name': "📐 Cầu lệch pha 2-3", 'confidence': 75, 'next': 'T', 'weight': 72}
            if last5 == "XXTTT":
                return {'name': "📐 Cầu lệch pha 3-2", 'confidence': 75, 'next': 'X', 'weight': 72}
        if len(history) >= 8:
            last8 = history[-8:]
            if last8 == "TTXXXTTX":
                return {'name': "📐📐 Cầu lệch pha 2-3-2", 'confidence': 80, 'next': 'X', 'weight': 78}
            if last8 == "XXTTTXXT":
                return {'name': "📐📐 Cầu lệch pha 3-2-3", 'confidence': 80, 'next': 'T', 'weight': 78}
        return None

    @staticmethod
    def detect_arithmetic(history):
        if len(history) < 8:
            return None
        nums = [1 if c == 'T' else 0 for c in history[-8:]]
        total = sum(nums)
        if total in [2,3,5,6]:
            return {'name': "🧮 Cầu số học", 'confidence': 68, 'next': 'T' if total > 4 else 'X', 'weight': 65}
        return None

    @staticmethod
    def detect_fibonacci(history):
        if len(history) < 9:
            return None
        fibs = [1,1,2,3,5,8]
        t_count = sum(1 for f in fibs if len(history) > f and history[-f] == 'T')
        if t_count >= 4:
            return {'name': "🌀 Cầu Fibonacci T", 'confidence': 75, 'next': 'X', 'weight': 73}
        if t_count <= 2:
            return {'name': "🌀 Cầu Fibonacci X", 'confidence': 75, 'next': 'T', 'weight': 73}
        return None

    @staticmethod
    def detect_regression_break(history):
        if len(history) < 10:
            return None
        nums = [1 if c == 'T' else 0 for c in history[-10:]]
        ma5 = sum(nums[-5:])/5
        ma10 = sum(nums)/10
        if abs(ma5 - ma10) > 0.3:
            return {'name': "📈📉 Cầu phá vỡ xu hướng", 'confidence': 72, 'next': 'T' if nums[-1]==0 else 'X', 'weight': 70}
        return None

    @staticmethod
    def detect_cycle(history, min_c=2, max_c=6):
        for c in range(min_c, max_c+1):
            if len(history) < c*2:
                continue
            pattern = history[-c:]
            if history[-2*c:-c] == pattern:
                pos = len(history) % c
                return {'name': f"🔄 Cầu chu kỳ {c}", 'confidence': 78, 'next': pattern[pos], 'weight': 75}
        return None

    @staticmethod
    def detect_trend(history):
        if len(history) < 20:
            return None
        short = history[-7:].count('T')/7
        medium = history[-14:].count('T')/14
        long = history[-21:].count('T')/21
        if short > medium > long and short - long > 0.2:
            return {'name': "🚀 Xu hướng TÀI tăng mạnh", 'confidence': 80, 'next': 'T', 'weight': 78}
        if long > medium > short and long - short > 0.2:
            return {'name': "📉 Xu hướng XỈU tăng mạnh", 'confidence': 80, 'next': 'X', 'weight': 78}
        if short > medium + 0.15:
            return {'name': "📈 Xu hướng TÀI ngắn hạn", 'confidence': 70, 'next': 'T', 'weight': 68}
        if medium > long + 0.15:
            return {'name': "📊 Xu hướng XỈU dài hạn", 'confidence': 70, 'next': 'X', 'weight': 68}
        return None

    @staticmethod
    def detect_balance_break(history):
        if len(history) < 12:
            return None
        recent = history[-12:]
        t_count = recent.count('T')
        if abs(t_count - (12-t_count)) <= 2:
            return {'name': "⚖️ Bẻ cầu do cân bằng", 'confidence': 75, 'next': 'X' if history[-1]=='T' else 'T', 'weight': 72}
        return None

    @staticmethod
    def detect_bet_reverse(history):
        if len(history) < 6:
            return None
        run = 1
        last = history[-1]
        for i in range(len(history)-2, -1, -1):
            if history[i] == last:
                run += 1
            else:
                break
        if run >= 5 and history[-2] == last and history[-1] != last:
            return {'name': "🔄 Cầu bệt đảo", 'confidence': 70, 'next': last, 'weight': 68}
        return None

    @staticmethod
    def detect_1_1_reverse(history):
        if len(history) >= 6:
            last6 = history[-6:]
            if last6 in ("TXTXXT", "XTXTXX"):
                return {'name': "🔄 Cầu 1-1 đảo", 'confidence': 73, 'next': history[-1], 'weight': 70}
        return None

    @staticmethod
    def detect_2_2_reverse(history):
        if len(history) >= 8:
            last8 = history[-8:]
            if last8 in ("TTXXTTXX", "XXTTXXTT"):
                return {'name': "🔄 Cầu 2-2 đảo", 'confidence': 75, 'next': 'X' if history[-1]=='T' else 'T', 'weight': 72}
        return None

    @staticmethod
    def detect_3_3_reverse(history):
        if len(history) >= 12:
            last12 = history[-12:]
            if last12 in ("TTTXXXTTTXXX", "XXXTTTXXXTTT"):
                return {'name': "🔄 Cầu 3-3 đảo", 'confidence': 78, 'next': 'X' if history[-1]=='T' else 'T', 'weight': 75}
        return None

    @staticmethod
    def detect_dragon(history):
        if len(history) < 5:
            return None
        t_run = 0
        for i in range(len(history)-1, -1, -1):
            if history[i] == 'T':
                t_run += 1
            else:
                break
        if t_run >= 6:
            return {'name': f"🐉 Cầu Rồng {t_run} (BẺ)", 'confidence': 82, 'next': 'X', 'weight': 80}
        if t_run >= 4:
            return {'name': f"🐉 Cầu Rồng {t_run}", 'confidence': 72, 'next': 'T', 'weight': 70}
        return None

    @staticmethod
    def detect_tiger(history):
        if len(history) < 5:
            return None
        x_run = 0
        for i in range(len(history)-1, -1, -1):
            if history[i] == 'X':
                x_run += 1
            else:
                break
        if x_run >= 6:
            return {'name': f"🐯 Cầu Hổ {x_run} (BẺ)", 'confidence': 82, 'next': 'T', 'weight': 80}
        if x_run >= 4:
            return {'name': f"🐯 Cầu Hổ {x_run}", 'confidence': 72, 'next': 'X', 'weight': 70}
        return None

    @staticmethod
    def detect_even_odd(history, totals):
        if len(totals) < 5:
            return None
        recent_totals = totals[-5:]
        even_count = sum(1 for t in recent_totals if t%2==0)
        if even_count >= 4:
            return {'name': "🎲 Cầu tổng CHẴN", 'confidence': 70, 'next': 'T' if even_count>2 else 'X', 'weight': 68}
        if even_count <= 1:
            return {'name': "🎲 Cầu tổng LẺ", 'confidence': 70, 'next': 'X' if even_count>2 else 'T', 'weight': 68}
        return None

    @staticmethod
    def detect_total_bet(history, totals):
        if len(totals) < 6:
            return None
        recent = totals[-6:]
        increasing = all(recent[i] <= recent[i+1] for i in range(5))
        decreasing = all(recent[i] >= recent[i+1] for i in range(5))
        if increasing:
            return {'name': "📈 Cầu tổng tăng dần", 'confidence': 68, 'next': 'T', 'weight': 65}
        if decreasing:
            return {'name': "📉 Cầu tổng giảm dần", 'confidence': 68, 'next': 'X', 'weight': 65}
        return None

    @staticmethod
    def detect_chain(history):
        if len(history) < 7:
            return None
        last7 = history[-7:]
        if all(last7[i] != last7[i+1] for i in range(6)):
            return {'name': "⛓️ Cầu chuỗi đảo liên tục", 'confidence': 85, 'next': 'X' if last7[-1]=='T' else 'T', 'weight': 82}
        if len(set(last7)) == 1:
            return {'name': "⛓️ Cầu chuỗi bệt dài", 'confidence': 75, 'next': last7[-1], 'weight': 72}
        return None

# ================= 30 THUẬT TOÁN DỰ ĐOÁN =================
class UltimateAdvancedAlgo:
    @staticmethod
    def markov1(history):
        if len(history) < 2:
            return None
        last = history[-1]
        trans = {'T':{'T':0,'X':0}, 'X':{'T':0,'X':0}}
        for i in range(len(history)-1):
            trans[history[i]][history[i+1]] += 1
        if trans[last]['T'] > trans[last]['X']:
            return 'T'
        if trans[last]['X'] > trans[last]['T']:
            return 'X'
        return None

    @staticmethod
    def markov2(history):
        if len(history) < 3:
            return None
        last2 = history[-2:]
        trans = defaultdict(lambda: defaultdict(int))
        for i in range(len(history)-2):
            trans[history[i:i+2]][history[i+2]] += 1
        if trans[last2]['T'] > trans[last2]['X']:
            return 'T'
        if trans[last2]['X'] > trans[last2]['T']:
            return 'X'
        return None

    @staticmethod
    def markov3(history):
        if len(history) < 4:
            return None
        last3 = history[-3:]
        trans = defaultdict(lambda: defaultdict(int))
        for i in range(len(history)-3):
            trans[history[i:i+3]][history[i+3]] += 1
        if trans[last3]['T'] > trans[last3]['X']:
            return 'T'
        if trans[last3]['X'] > trans[last3]['T']:
            return 'X'
        return None

    @staticmethod
    def markov4(history):
        if len(history) < 5:
            return None
        last4 = history[-4:]
        trans = defaultdict(lambda: defaultdict(int))
        for i in range(len(history)-4):
            trans[history[i:i+4]][history[i+4]] += 1
        if trans[last4]['T'] > trans[last4]['X']:
            return 'T'
        if trans[last4]['X'] > trans[last4]['T']:
            return 'X'
        return None

    @staticmethod
    def markov5(history):
        if len(history) < 6:
            return None
        last5 = history[-5:]
        trans = defaultdict(lambda: defaultdict(int))
        for i in range(len(history)-5):
            trans[history[i:i+5]][history[i+5]] += 1
        if trans[last5]['T'] > trans[last5]['X']:
            return 'T'
        if trans[last5]['X'] > trans[last5]['T']:
            return 'X'
        return None

    @staticmethod
    def weighted_frequency(history, window=20):
        if not history:
            return None
        recent = history[-window:]
        wt = sum((i+1)*(1 if ch=='T' else 0) for i,ch in enumerate(reversed(recent)))
        wx = sum((i+1)*(1 if ch=='X' else 0) for i,ch in enumerate(reversed(recent)))
        if wt > wx:
            return 'T'
        if wx > wt:
            return 'X'
        return None

    @staticmethod
    def simple_majority(history, window=15):
        if len(history) < window:
            return None
        recent = history[-window:]
        t = recent.count('T')
        x = window - t
        if t > x:
            return 'T'
        if x > t:
            return 'X'
        return None

    @staticmethod
    def moving_average_cross(history, short=5, long=13):
        if len(history) < long:
            return None
        short_t = history[-short:].count('T')/short
        long_t = history[-long:].count('T')/long
        if short_t > long_t + 0.12:
            return 'T'
        if long_t > short_t + 0.12:
            return 'X'
        return None

    @staticmethod
    def entropy_prediction(history, window=12):
        if len(history) < window:
            return None
        recent = history[-window:]
        p_t = recent.count('T')/window
        if p_t == 0 or p_t == 1:
            return recent[-1]
        entropy = -p_t*math.log2(p_t) - (1-p_t)*math.log2(1-p_t)
        if entropy > 0.95:
            return 'X' if recent[-1]=='T' else 'T'
        return recent[-1]

    @staticmethod
    def fibonacci_fractal(history):
        fibs = [1,1,2,3,5,8,13]
        count_match = sum(1 for f in fibs if len(history)>f and history[-f]==history[-1])
        if count_match >= len(fibs)//2:
            return history[-1]
        else:
            return 'X' if history[-1]=='T' else 'T'

    @staticmethod
    def cumulative_imbalance(history, window=25):
        if len(history) < window:
            return None
        recent = history[-window:]
        imbalance = recent.count('T') - recent.count('X')
        if imbalance > 7:
            return 'X'
        if imbalance < -7:
            return 'T'
        return None

    @staticmethod
    def zigzag_predict(history):
        if len(history) < 5:
            return None
        changes = sum(1 for i in range(1, min(5,len(history))) if history[-i]!=history[-i-1])
        if changes >= 4:
            return 'X' if history[-1]=='T' else 'T'
        if changes >= 3:
            return history[-1]
        return None

    @staticmethod
    def rsi_predict(history, period=7):
        if len(history) < period:
            return None
        nums = [1 if c=='T' else 0 for c in history[-period:]]
        gains = [max(nums[i]-nums[i-1],0) for i in range(1,len(nums))]
        losses = [max(nums[i-1]-nums[i],0) for i in range(1,len(nums))]
        avg_gain = sum(gains)/period if gains else 0
        avg_loss = sum(losses)/period if losses else 0
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain/avg_loss
            rsi = 100 - (100/(1+rs))
        if rsi > 75:
            return 'X' if history[-1]=='T' else 'T'
        if rsi < 25:
            return 'X' if history[-1]=='T' else 'T'
        if rsi > 65:
            return 'X'
        if rsi < 35:
            return 'T'
        return None

    @staticmethod
    def bollinger_predict(history, period=12):
        if len(history) < period:
            return None
        nums = [1 if c=='T' else 0 for c in history[-period:]]
        mean = sum(nums)/period
        std = standard_deviation(nums, mean)
        upper = mean + 2*std
        lower = mean - 2*std
        last = nums[-1]
        if last > upper:
            return 'X'
        if last < lower:
            return 'T'
        return None

    @staticmethod
    def macd_predict(history, short=6, long=13, signal=4):
        if len(history) < long+signal:
            return None
        nums = [1 if c=='T' else 0 for c in history]
        ema_short = moving_average(nums, short)
        ema_long = moving_average(nums, long)
        macd = ema_short - ema_long
        macd_history = []
        for i in range(len(nums)-signal, len(nums)):
            e_short = moving_average(nums[:i+1], short) if i+1>=short else moving_average(nums[:i+1], i+1)
            e_long = moving_average(nums[:i+1], long) if i+1>=long else moving_average(nums[:i+1], i+1)
            macd_history.append(e_short - e_long)
        signal_line = moving_average(macd_history, signal) if len(macd_history)>=signal else sum(macd_history)/len(macd_history)
        if macd > signal_line + 0.05:
            return 'T'
        if macd < signal_line - 0.05:
            return 'X'
        return None

    @staticmethod
    def stochastic_predict(history, period=7):
        if len(history) < period:
            return None
        nums = [1 if c=='T' else 0 for c in history[-period:]]
        highest = max(nums)
        lowest = min(nums)
        if highest == lowest:
            return None
        k = (nums[-1] - lowest)/(highest - lowest)*100
        if k > 80:
            return 'X'
        if k < 20:
            return 'T'
        return None

    @staticmethod
    def williams_r(history, period=7):
        if len(history) < period:
            return None
        nums = [1 if c=='T' else 0 for c in history[-period:]]
        highest = max(nums)
        lowest = min(nums)
        if highest == lowest:
            return None
        wr = (highest - nums[-1])/(highest - lowest)*(-100)
        if wr < -80:
            return 'T'
        if wr > -20:
            return 'X'
        return None

    @staticmethod
    def cci_predict(history, period=10):
        if len(history) < period:
            return None
        nums = [1 if c=='T' else 0 for c in history[-period:]]
        mean = sum(nums)/period
        mad = sum(abs(x-mean) for x in nums)/period
        if mad == 0:
            return None
        cci = (nums[-1] - mean)/(0.015*mad)
        if cci > 100:
            return 'X'
        if cci < -100:
            return 'T'
        return None

    @staticmethod
    def adx_predict(history, period=10):
        if len(history) < period+1:
            return None
        nums = [1 if c=='T' else 0 for c in history]
        plus_dm, minus_dm = [], []
        for i in range(1, len(nums)):
            if nums[i] > nums[i-1]:
                plus_dm.append(nums[i]-nums[i-1]); minus_dm.append(0)
            elif nums[i] < nums[i-1]:
                plus_dm.append(0); minus_dm.append(nums[i-1]-nums[i])
            else:
                plus_dm.append(0); minus_dm.append(0)
        if len(plus_dm) < period:
            return None
        atr = moving_average([abs(nums[i]-nums[i-1]) for i in range(1, len(nums))], period)
        if atr == 0:
            return None
        plus_di = moving_average(plus_dm[-period:], period)/atr*100
        minus_di = moving_average(minus_dm[-period:], period)/atr*100
        dx = abs(plus_di-minus_di)/(plus_di+minus_di)*100 if (plus_di+minus_di)>0 else 0
        if dx > 40:
            return 'T' if plus_di > minus_di else 'X'
        return None

    @staticmethod
    def mean_reversion(history, window=12):
        if len(history) < window:
            return None
        recent = history[-window:]
        mean = recent.count('T')/window
        if mean > 0.75:
            return 'X'
        if mean < 0.25:
            return 'T'
        return None

    @staticmethod
    def pattern_matching(history, lookback=25):
        if len(history) < lookback:
            return None
        query = history[-lookback:]
        best_match, best_score = None, -1
        for i in range(len(history)-lookback):
            segment = history[i:i+lookback]
            score = sum(1 for a,b in zip(segment, query) if a==b)
            if score > best_score:
                best_score, best_match = score, i
        if best_match is not None and best_match+lookback < len(history):
            next1 = history[best_match+lookback]
            if best_match+lookback+1 < len(history):
                next2 = history[best_match+lookback+1]
                if next1 == next2:
                    return next1
            return next1
        return None

    @staticmethod
    def linear_regression(history, window=12):
        if len(history) < window:
            return None
        y = [1 if c=='T' else 0 for c in history[-window:]]
        x = list(range(window))
        n = window
        sum_x = sum(x); sum_y = sum(y); sum_xy = sum(x[i]*y[i] for i in range(n)); sum_x2 = sum(xi*xi for xi in x)
        denom = n*sum_x2 - sum_x*sum_x
        if denom == 0:
            return None
        slope = (n*sum_xy - sum_x*sum_y)/denom
        intercept = (sum_y - slope*sum_x)/n
        pred = slope*window + intercept
        return 'T' if pred > 0.5 else 'X'

    @staticmethod
    def knn_predict(history, k=5, lookback=10):
        if len(history) < lookback+k:
            return None
        query = history[-lookback:]
        distances = []
        for i in range(len(history)-lookback-1):
            segment = history[i:i+lookback]
            distance = sum(1 for a,b in zip(segment, query) if a!=b)
            distances.append((distance, history[i+lookback]))
        distances.sort(key=lambda x:x[0])
        neighbors = [pred for _,pred in distances[:k]]
        t_count = neighbors.count('T')
        return 'T' if t_count > k-t_count else 'X'

    @staticmethod
    def naive_bayes(history, window=15):
        if len(history) < window:
            return None
        p_t = history.count('T')/len(history)
        p_x = 1 - p_t
        last5 = history[-5:]
        cond_t = sum(1 for i in range(len(history)-5) if history[i:i+5]==last5 and history[i+5]=='T') / max(1, history.count('T'))
        cond_x = sum(1 for i in range(len(history)-5) if history[i:i+5]==last5 and history[i+5]=='X') / max(1, history.count('X'))
        post_t = p_t * cond_t
        post_x = p_x * cond_x
        return 'T' if post_t > post_x else 'X'

    @staticmethod
    def decision_tree(history):
        if len(history) < 10:
            return None
        last1, last2, last3 = history[-1], history[-2] if len(history)>1 else None, history[-3] if len(history)>2 else None
        t5 = history[-5:].count('T') if len(history)>=5 else history.count('T')
        if last1=='T' and last2=='T' and last3=='T':
            return 'X'
        if last1=='X' and last2=='X' and last3=='X':
            return 'T'
        if last1=='T' and last2=='X' and last3=='T':
            return 'X'
        if last1=='X' and last2=='T' and last3=='X':
            return 'T'
        if t5 >= 4:
            return 'X'
        if t5 <= 1:
            return 'T'
        return last1

    @staticmethod
    def ensemble_voting(history):
        algos = [UltimateAdvancedAlgo.markov3, UltimateAdvancedAlgo.weighted_frequency,
                 UltimateAdvancedAlgo.rsi_predict, UltimateAdvancedAlgo.mean_reversion,
                 UltimateAdvancedAlgo.pattern_matching]
        votes = [algo(history) for algo in algos if algo(history) is not None]
        if not votes:
            return None
        return 'T' if votes.count('T') > votes.count('X') else 'X'

    @staticmethod
    def reinforcement_learning(history, game_id):
        if not actual_history[game_id]:
            return None
        recent_results = list(actual_history[game_id])[-20:]
        if len(recent_results) < 10:
            return None
        pattern_win_rate = defaultdict(lambda:{'win':0,'total':0})
        for i in range(len(recent_results)-1):
            pat = recent_results[i]
            nxt = recent_results[i+1]
            pattern_win_rate[pat]['total'] += 1
            if nxt == 'T':
                pattern_win_rate[pat]['win'] += 1
        current_pattern = history[-5:] if len(history)>=5 else history
        if current_pattern not in pattern_win_rate or pattern_win_rate[current_pattern]['total'] < 3:
            return None
        win_rate = pattern_win_rate[current_pattern]['win'] / pattern_win_rate[current_pattern]['total']
        return 'T' if win_rate > 0.5 else 'X'

# ================= TÍN HIỆU BẺ CẦU =================
class BreakSignalDetector:
    @staticmethod
    def rsi_break(history):
        pred = UltimateAdvancedAlgo.rsi_predict(history, 7)
        return pred is not None and pred != history[-1]

    @staticmethod
    def bollinger_break(history):
        pred = UltimateAdvancedAlgo.bollinger_predict(history, 10)
        return pred is not None and pred != history[-1]

    @staticmethod
    def macd_break(history):
        pred = UltimateAdvancedAlgo.macd_predict(history, 5, 12, 3)
        return pred is not None and pred != history[-1]

    @staticmethod
    def stochastic_break(history):
        pred = UltimateAdvancedAlgo.stochastic_predict(history, 7)
        return pred is not None and pred != history[-1]

    @staticmethod
    def williams_break(history):
        pred = UltimateAdvancedAlgo.williams_r(history, 7)
        return pred is not None and pred != history[-1]

    @staticmethod
    def cci_break(history):
        pred = UltimateAdvancedAlgo.cci_predict(history, 10)
        return pred is not None and pred != history[-1]

    @staticmethod
    def adx_break(history):
        pred = UltimateAdvancedAlgo.adx_predict(history, 10)
        return pred is not None and pred != history[-1]

    @staticmethod
    def divergence_break(history):
        if len(history) < 10:
            return False
        nums = [1 if c=='T' else 0 for c in history[-10:]]
        price_trend = nums[-1] - nums[0]
        rsi_values = []
        for i in range(7, len(nums)):
            sub = nums[i-6:i+1]
            gains = [max(sub[j]-sub[j-1],0) for j in range(1,len(sub))]
            losses = [max(sub[j-1]-sub[j],0) for j in range(1,len(sub))]
            avg_gain = sum(gains)/7 if gains else 0
            avg_loss = sum(losses)/7 if losses else 0
            rsi = 100 if avg_loss==0 else 100 - (100/(1+avg_gain/avg_loss))
            rsi_values.append(rsi)
        if len(rsi_values) >= 2:
            rsi_trend = rsi_values[-1] - rsi_values[0]
            if (price_trend > 0 and rsi_trend < 0) or (price_trend < 0 and rsi_trend > 0):
                return True
        return False

    @staticmethod
    def harmonic_break(history):
        if len(history) < 8:
            return False
        nums = [1 if c=='T' else 0 for c in history[-8:]]
        pattern = ''.join('T' if x==1 else 'X' for x in nums)
        return pattern in ['TXTXTXTX','XTXTXTXT','TTXXTTXX','XXTTXXTT']

    @staticmethod
    def fibonacci_retracement(history):
        if len(history) < 10:
            return False
        nums = [1 if c=='T' else 0 for c in history[-10:]]
        high, low = max(nums), min(nums)
        if high == low:
            return False
        retrace = (nums[-1] - low)/(high - low)
        return any(abs(retrace - level) < 0.1 for level in [0.382,0.5,0.618])

    @staticmethod
    def atr_break(history, period=10):
        if len(history) < period+1:
            return False
        nums = [1 if c=='T' else 0 for c in history]
        true_ranges = [abs(nums[i]-nums[i-1]) for i in range(1,len(nums))]
        if len(true_ranges) < period:
            return False
        atr = moving_average(true_ranges[-period:], period)
        last_tr = true_ranges[-1] if true_ranges else 0
        return last_tr > atr*1.5

    @staticmethod
    def ichimoku_break(history):
        if len(history) < 26:
            return False
        nums = [1 if c=='T' else 0 for c in history]
        tenkan = (max(nums[-9:]) + min(nums[-9:]))/2
        kijun = (max(nums[-26:]) + min(nums[-26:]))/2
        chikou = nums[-26] if len(nums)>26 else 0
        current = nums[-1]
        return (current > tenkan and current > kijun and chikou > kijun) or \
               (current < tenkan and current < kijun and chikou < kijun)

# ================= QUYẾT ĐỊNH SIÊU VIP =================
class SuperVipDecision:
    def __init__(self, history, totals, game_id):
        self.history = history
        self.totals = totals
        self.game_id = game_id
        self.break_signals = 0
        self.detectors = [
            UltimatePatternDetector.detect_bet,
            UltimatePatternDetector.detect_1_1,
            UltimatePatternDetector.detect_2_2,
            UltimatePatternDetector.detect_3_3,
            UltimatePatternDetector.detect_1_2,
            UltimatePatternDetector.detect_2_1,
            UltimatePatternDetector.detect_1_2_3,
            UltimatePatternDetector.detect_3_2_1,
            UltimatePatternDetector.detect_triangle,
            UltimatePatternDetector.detect_phase_shift,
            UltimatePatternDetector.detect_arithmetic,
            UltimatePatternDetector.detect_fibonacci,
            UltimatePatternDetector.detect_regression_break,
            UltimatePatternDetector.detect_cycle,
            UltimatePatternDetector.detect_trend,
            UltimatePatternDetector.detect_balance_break,
            UltimatePatternDetector.detect_bet_reverse,
            UltimatePatternDetector.detect_1_1_reverse,
            UltimatePatternDetector.detect_2_2_reverse,
            UltimatePatternDetector.detect_3_3_reverse,
            UltimatePatternDetector.detect_dragon,
            UltimatePatternDetector.detect_tiger,
            lambda h: UltimatePatternDetector.detect_even_odd(h, totals),
            lambda h: UltimatePatternDetector.detect_total_bet(h, totals),
            UltimatePatternDetector.detect_chain,
        ]
        self.algos = [
            ('Markov1', UltimateAdvancedAlgo.markov1),
            ('Markov2', UltimateAdvancedAlgo.markov2),
            ('Markov3', UltimateAdvancedAlgo.markov3),
            ('Markov4', UltimateAdvancedAlgo.markov4),
            ('Markov5', UltimateAdvancedAlgo.markov5),
            ('WeightedFreq', UltimateAdvancedAlgo.weighted_frequency),
            ('SimpleMajority', UltimateAdvancedAlgo.simple_majority),
            ('MovingAvg', UltimateAdvancedAlgo.moving_average_cross),
            ('Entropy', UltimateAdvancedAlgo.entropy_prediction),
            ('Fibonacci', UltimateAdvancedAlgo.fibonacci_fractal),
            ('Cumulative', UltimateAdvancedAlgo.cumulative_imbalance),
            ('Zigzag', UltimateAdvancedAlgo.zigzag_predict),
            ('RSI', UltimateAdvancedAlgo.rsi_predict),
            ('Bollinger', UltimateAdvancedAlgo.bollinger_predict),
            ('MACD', UltimateAdvancedAlgo.macd_predict),
            ('Stochastic', UltimateAdvancedAlgo.stochastic_predict),
            ('Williams%R', UltimateAdvancedAlgo.williams_r),
            ('CCI', UltimateAdvancedAlgo.cci_predict),
            ('ADX', UltimateAdvancedAlgo.adx_predict),
            ('MeanReversion', UltimateAdvancedAlgo.mean_reversion),
            ('PatternMatch', UltimateAdvancedAlgo.pattern_matching),
            ('LinearReg', UltimateAdvancedAlgo.linear_regression),
            ('KNN', UltimateAdvancedAlgo.knn_predict),
            ('NaiveBayes', UltimateAdvancedAlgo.naive_bayes),
            ('DecisionTree', UltimateAdvancedAlgo.decision_tree),
            ('Ensemble', UltimateAdvancedAlgo.ensemble_voting),
            ('RL', lambda h: UltimateAdvancedAlgo.reinforcement_learning(h, game_id)),
        ]
        self.break_detectors = [
            BreakSignalDetector.rsi_break,
            BreakSignalDetector.bollinger_break,
            BreakSignalDetector.macd_break,
            BreakSignalDetector.stochastic_break,
            BreakSignalDetector.williams_break,
            BreakSignalDetector.cci_break,
            BreakSignalDetector.adx_break,
            BreakSignalDetector.divergence_break,
            BreakSignalDetector.harmonic_break,
            BreakSignalDetector.fibonacci_retracement,
            BreakSignalDetector.atr_break,
            BreakSignalDetector.ichimoku_break,
        ]

    def check_break_signals(self):
        self.break_signals = 0
        for det in self.break_detectors:
            if det(self.history):
                self.break_signals += 1
        return self.break_signals

    def analyze(self):
        break_count = self.check_break_signals()
        should_break = break_count >= 3
        votes = []
        for det in self.detectors:
            try:
                res = det(self.history)
                if res:
                    votes.append((res['name'], res['next'], res.get('weight', res['confidence']), False))
            except:
                pass
        for name, func in self.algos:
            try:
                pred = func(self.history)
                if pred:
                    base_weight = algo_accuracy[self.game_id+'_'+name]['weight']
                    if should_break and pred != self.history[-1]:
                        base_weight += 10
                    votes.append((name, pred, base_weight, True))
            except:
                pass
        if not votes:
            last5 = self.history[-5:] if len(self.history)>=5 else self.history
            fb = 'T' if last5.count('T') >= last5.count('X') else 'X'
            return fb, 50, "Fallback", {}
        wT = sum(w for _,p,w,_ in votes if p=='T')
        wX = sum(w for _,p,w,_ in votes if p=='X')
        if should_break:
            if wT > wX:
                final = 'X'
                conf_boost = min(25, break_count*5)
            else:
                final = 'T'
                conf_boost = min(25, break_count*5)
        else:
            final = 'T' if wT > wX else 'X'
            conf_boost = 0
        total = wT + wX
        conf = round(max(wT,wX)/total*100) if total>0 else 50
        conf = min(99, conf+conf_boost)
        best_pat = max([v for v in votes if not v[3]], key=lambda x:x[2], default=None)
        pattern = best_pat[0] if best_pat else "Không xác định"
        if should_break:
            pattern = f"🔥 BẺ CẦU ({break_count} tín hiệu) - {pattern}"
        details = {src: pred for src,pred,_,_ in votes}
        details['break_signals'] = break_count
        details['should_break'] = should_break
        return final, conf, pattern, details

# ================= AUTO PING BACKGROUND =================
def ping_all_apis():
    while True:
        for game_id in GAME_CONFIG:
            try:
                fetch_and_cache(game_id)
                print(f"[{datetime.now()}] Ping {game_id} thành công")
            except Exception as e:
                print(f"[{datetime.now()}] Lỗi ping {game_id}: {e}")
        time.sleep(60)

ping_thread = threading.Thread(target=ping_all_apis, daemon=True)
ping_thread.start()

# ================= FLASK API =================
def create_endpoint(game_id):
    def endpoint_func():
        return predict_game(game_id)
    endpoint_func.__name__ = f"predict_{game_id}"
    return endpoint_func

for game_id in GAME_CONFIG:
    app.add_url_rule(f'/api/{game_id}', view_func=create_endpoint(game_id), methods=['GET'])

def predict_game(game_id):
    key = request.args.get('key')
    if key != AUTH_KEY:
        return jsonify({"error": "❌ Truy cập bị từ chối. Vui lòng cung cấp đúng Key xác thực."}), 403
    show_details = request.args.get('details', 'false').lower() == 'true'
    config = GAME_CONFIG.get(game_id)
    if not config:
        return jsonify({"error": "Game không hợp lệ."}), 400
    data = get_cached_data(game_id)
    if data is None:
        data = fetch_data(config['api_url'])
        if data is None:
            return jsonify({"error": f"Không thể lấy dữ liệu từ API Game {config['game_key']}."}), 500
    history, totals = build_history(data, config['type'])
    if not history:
        return jsonify({"error": "Không có dữ liệu lịch sử."}), 500
    if isinstance(data, dict) and 'list' in data:
        current_item = data['list'][0]
    else:
        current_item = data[0] if data else {}
    result, point, dices, session_id = parse_session(current_item, config['type'])
    if result:
        actual_history[game_id].append(result)
    dec = SuperVipDecision(history, totals, game_id)
    pred, conf, pattern, details = dec.analyze()
    tai_percent = conf if pred == 'T' else 100 - conf
    xiu_percent = 100 - tai_percent
    response = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "game": config['name'],
        "game_key": config['game_key'],
        "user_id": USER_ID,
        "current_session": {
            "phien": session_id,
            "ket_qua": "Tài" if result=='T' else "Xỉu" if result=='X' else "Chưa xác định",
            "tong": point,
            "xuc_xac": dices
        },
        "prediction": {
            "next_session": session_id+1 if session_id else "?",
            "du_doan": "Tài" if pred=='T' else "Xỉu",
            "do_tin_cay": f"{tai_percent}% - {xiu_percent}%",
            "cau_dang_chay": pattern,
            "break_signals": details.get('break_signals',0)
        },
        "statistics": {
            "history_length": len(history),
            "recent_trend": f"T{history[-10:].count('T')}:X{history[-10:].count('X')}" if len(history)>=10 else "N/A",
            "total_balance": f"T{history.count('T')}:X{history.count('X')}"
        }
    }
    if show_details:
        response["details"] = {
            "pattern_detectors": {k:v for k,v in details.items() if not k in ['break_signals','should_break'] and not any(algo in k for algo in ['Markov','RSI','MACD','Bollinger'])},
            "algorithms": {k:v for k,v in details.items() if any(algo in k for algo in ['Markov','RSI','MACD','Bollinger','Stochastic','Williams','CCI','ADX','MeanReversion','PatternMatch','LinearReg','KNN','NaiveBayes','DecisionTree','Ensemble','RL'])},
            "history_string": history[-30:] if len(history)>30 else history,
            "totals_history": totals[-20:] if len(totals)>20 else totals
        }
    return jsonify(response)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "version": "9.2",
        "algorithm": ALGO_NAME,
        "active_games": len(GAME_CONFIG),
        "total_patterns": 25,
        "total_algorithms": 30,
        "break_signals": 12,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    key = request.args.get('key')
    if key != AUTH_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    stats = {}
    for name, data in algo_accuracy.items():
        if data['total'] > 0:
            accuracy = data['correct']/data['total']*100
            stats[name] = {'accuracy': round(accuracy,2), 'total_predictions': data['total'], 'current_weight': data['weight']}
    return jsonify({"algorithm_stats": stats, "actual_history_length": {game: len(hist) for game, hist in actual_history.items()}})

@app.route('/api/update_accuracy', methods=['POST'])
def update_accuracy():
    key = request.args.get('key')
    if key != AUTH_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    game_id = data.get('game_id')
    algo_name = data.get('algo_name')
    was_correct = data.get('was_correct', False)
    if not game_id or not algo_name:
        return jsonify({"error": "Missing parameters"}), 400
    key_name = game_id + '_' + algo_name
    if was_correct:
        algo_accuracy[key_name]['correct'] += 1
    algo_accuracy[key_name]['total'] += 1
    total = algo_accuracy[key_name]['total']
    correct = algo_accuracy[key_name]['correct']
    if total > 0:
        accuracy = correct/total
        algo_accuracy[key_name]['weight'] = min(100, max(40, int(accuracy*100)))
    return jsonify({"status": "updated", "new_weight": algo_accuracy[key_name]['weight']})

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": ALGO_NAME,
        "version": "9.2 ULTIMATE",
        "features": {"patterns": 25, "algorithms": 30, "break_signals": 12},
        "endpoints": [f"/api/{game_id}?key={AUTH_KEY}&details=true/false" for game_id in GAME_CONFIG],
        "games": list(GAME_CONFIG.keys()),
        "author": USER_ID,
        "documentation": "Thêm parameter details=true để xem chi tiết các thuật toán và cầu"
    })

if __name__ == '__main__':
    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║   🚀 HuyDaiXu SIÊU VIP - Ultimate Prediction Engine v9.2    ║
    ║   📊 25 loại cầu | 30 thuật toán | 12 tín hiệu bẻ cầu       ║
    ║   🎯 Độ chính xác tối ưu | Bẻ cầu siêu chuẩn                ║
    ║   🌐 Server đang chạy tại: http://0.0.0.0:5000              ║
    ║   🔄 Auto ping mỗi 60s để giữ kết nối                       ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)