import streamlit as st
import re
import random
import os

# --- 設定網頁與極簡 Spotify 質感 CSS ---
st.set_page_config(page_title="CAA B1.1 刷題神器", layout="centered")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    h1, h2, h3 { color: #1DB954 !important; font-weight: 700; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    .stProgress .st-bo { background-color: #1DB954; }
    div.stButton > button {
        border-radius: 20px; border: 1px solid #535353; color: #FFFFFF; background-color: transparent; transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover { border-color: #1DB954; color: #1DB954; }
    div.stButton > button[kind="primary"] { background-color: #1DB954; border: none; color: #121212; font-weight: bold; }
    div.stButton > button[kind="primary"]:hover { background-color: #1ed760; color: #121212; transform: scale(1.02); }
</style>
""", unsafe_allow_html=True)

# --- 題庫解析與資料載入 ---
MODULE_INFO = {
    "01": {"name": "數學", "limit": 32}, "02": {"name": "物理", "limit": 52},
    "03": {"name": "電機基礎", "limit": 52}, "04": {"name": "電子基礎", "limit": 20},
    "05": {"name": "數位技術與電子儀器", "limit": 40}, "06": {"name": "材料與硬體", "limit": 72},
    "07": {"name": "維修實務", "limit": 80}, "08": {"name": "基本空氣動力學", "limit": 20},
    "09": {"name": "人為因素", "limit": 20}, "10": {"name": "航空法規", "limit": 40},
    "11": {"name": "渦輪飛機空氣動力、結構與系統", "limit": 140}, "15": {"name": "燃氣渦輪發動機", "limit": 92},
    "17": {"name": "螺旋槳", "limit": 32}
}

@st.cache_data
def load_and_parse_questions(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return []
    questions = []
    blocks = content.split("Question Number.")
    for block in blocks[1:]:
        try:
            q_match = re.search(r'\s*\d+\.\s*(.*?)(?=Option A\.|Option \u0391\.)', block, re.DOTALL)
            opt_a = re.search(r'(?:Option A\.|Option \u0391\.)\s*(.*?)(?=Option B\.|Option \u0392\.)', block, re.DOTALL)
            opt_b = re.search(r'(?:Option B\.|Option \u0392\.)\s*(.*?)(?=Option C\.|Option \u0393\.)', block, re.DOTALL)
            opt_c = re.search(r'(?:Option C\.|Option \u0393\.)\s*(.*?)(?=Correct Answer is\.)', block, re.DOTALL)
            ans = re.search(r'Correct Answer is\.\s*(.*?)(?=Explanation\.)', block, re.DOTALL)
            exp = re.search(r'Explanation\.\s*(.*)', block, re.DOTALL)

            if q_match and opt_a and opt_b and opt_c and ans:
                questions.append({
                    "question": q_match.group(1).strip(),
                    "options": [opt_a.group(1).strip(), opt_b.group(1).strip(), opt_c.group(1).strip()],
                    "correct_text": ans.group(1).strip(),
                    "explanation": exp.group(1).strip() if exp else "無詳解"
                })
        except Exception:
            continue
    return questions

def get_available_modules():
    files = [f for f in os.listdir('.') if f.endswith('.txt')]
    modules = {}
    for file in files:
        num_match = re.search(r'\d+', file)
        if num_match:
            mod_num = num_match.group(0).zfill(2)
            mod_name = MODULE_INFO.get(mod_num, {"name": "自訂題庫"})["name"]
            modules[f"Module {mod_num} - {mod_name}"] = file
    return modules

# --- 初始化狀態 ---
if 'app_initialized' not in st.session_state:
    st.session_state.app_initialized = True
    st.session_state.current_pool = []
    st.session_state.current_index = 0
    st.session_state.user_answers = {} 
    st.session_state.show_explanation = False
    st.session_state.wrong_bank = {} # 記錄各科錯題: { "01": [題庫dict, ...], "02": [...] }
    st.session_state.exam_submitted = False

# --- 側邊欄設定 ---
available_modules = get_available_modules()

with st.sidebar:
    st.title("🎧 播放控制台")
    if not available_modules:
        st.warning("⚠️ 找不到題庫 txt 檔")
    else:
        selected_module_key = st.selectbox("選擇章節", list(available_modules.keys()))
        current_file = available_modules[selected_module_key]
        mod_num = re.search(r'\d+', current_file).group(0).zfill(2)
        standard_limit = MODULE_INFO.get(mod_num, {"limit": None}).get("limit")
        
        selected_mode = st.radio("選擇模式", ["自由練習 (50題)", "真實模擬考", "錯題練習"])
        
        if st.button("▶️ 載入 / 重新開始", type="primary"):
            all_q = load_and_parse_questions(current_file)
            st.session_state.user_answers = {}
            st.session_state.current_index = 0
            st.session_state.show_explanation = False
            st.session_state.exam_submitted = False
            
            if "自由練習" in selected_mode:
                limit = min(50, len(all_q))
                st.session_state.current_pool = random.sample(all_q, limit)
            elif "模擬考" in selected_mode:
                limit = standard_limit if standard_limit and standard_limit <= len(all_q) else len(all_q)
                st.session_state.current_pool = random.sample(all_q, limit)
            elif "錯題" in selected_mode:
                wrong_qs = st.session_state.wrong_bank.get(mod_num, [])
                if not wrong_qs:
                    st.toast("🎉 太神啦！這個章節目前沒有錯題喔！")
                    st.session_state.current_pool = []
                else:
                    st.session_state.current_pool = random.sample(wrong_qs, len(wrong_qs))
            st.rerun()

    st.divider()
    
    # 答題矩陣與交卷
    if st.session_state.current_pool and not st.session_state.exam_submitted:
        st.subheader("答題狀況總覽")
        status_text = ""
        for i in range(len(st.session_state.current_pool)):
            if i in st.session_state.user_answers:
                status_text += "🟢 " if st.session_state.user_answers[i]['is_correct'] else "🔴 "
            else:
                status_text += "⚪ "
            if (i + 1) % 5 == 0:
                status_text += "\n\n"
        st.markdown(status_text)
        st.caption("🟢答對 | 🔴答錯 | ⚪未答")
        
        st.divider()
        if st.button("📝 交卷並結算成績", use_container_width=True):
            st.session_state.exam_submitted = True
            st.rerun()

# --- 主畫面區 ---
st.title("專業科目刷題系統")

if not st.session_state.current_pool:
    st.info("請從左側選擇章節並點擊「載入 / 重新開始」發動引擎！")
    st.stop()

# --- 成績結算畫面 ---
if st.session_state.exam_submitted:
    total_qs = len(st.session_state.current_pool)
    correct_qs = sum(1 for ans in st.session_state.user_answers.values() if ans['is_correct'])
    score = round((correct_qs / total_qs) * 100, 1) if total_qs > 0 else 0
    
    st.header("📊 測驗結果報告")
    st.markdown(f"### 你的總得分： **{score}** / 100")
    
    if "模擬考" in selected_mode:
        if score >= 75:
            st.success("🎉 恭喜通過！達到民航局 75 分及格標準，這手感保持下去，證照絕對是你的！")
            st.balloons()
        else:
            st.error("💔 未達及格標準 75 分。別灰心，去左邊選單開啟「錯題練習」把弱點補起來，下次一定過！")
    else:
        st.info("💡 練習模式結算完畢！繼續保持手感喔！")
        
    if st.button("再測驗一次"):
        st.session_state.exam_submitted = False
        st.rerun()
    st.stop()

# --- 答題畫面 ---
pool_size = len(st.session_state.current_pool)
idx = st.session_state.current_index
current_q = st.session_state.current_pool[idx]

st.progress((idx + 1) / pool_size)
st.caption(f"Question {idx + 1} of {pool_size}")

st.markdown(f"### {current_q['question']}")

previous_choice = st.session_state.user_answers.get(idx, {}).get('choice', None)
options = current_q['options']
default_idx = options.index(previous_choice) if previous_choice in options else None

user_choice = st.radio("選擇答案：", options, index=default_idx, key=f"q_{idx}")

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("⬅️ 上一題", use_container_width=True):
        st.session_state.current_index = max(0, idx - 1)
        st.session_state.show_explanation = False
        st.rerun()
with col2:
    if st.button("確認送出 (存檔)", type="primary", use_container_width=True):
        if user_choice:
            is_correct = current_q['correct_text'].strip() in user_choice or user_choice in current_q['correct_text'].strip()
            st.session_state.user_answers[idx] = {'choice': user_choice, 'is_correct': is_correct}
            st.session_state.show_explanation = True
            
            # 答錯自動加入錯題本
            if not is_correct:
                if mod_num not in st.session_state.wrong_bank:
                    st.session_state.wrong_bank[mod_num] = []
                if current_q not in st.session_state.wrong_bank[mod_num]:
                    st.session_state.wrong_bank[mod_num].append(current_q)
            st.rerun()
        else:
            st.warning("請先選擇答案！")
with col3:
    if st.button("跳過 / 下一題 ➡️", use_container_width=True):
        st.session_state.current_index = min(pool_size - 1, idx + 1)
        st.session_state.show_explanation = False
        st.rerun()

if st.session_state.show_explanation or idx in st.session_state.user_answers:
    st.divider()
    ans_data = st.session_state.user_answers.get(idx)
    if ans_data:
        if ans_data['is_correct']:
            st.success("✅ 答對了！")
        else:
            st.error(f"❌ 答錯了。正確答案是： {current_q['correct_text']}")
        st.info(f"💡 **詳解：** {current_q['explanation']}")