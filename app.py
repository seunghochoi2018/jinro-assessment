# ────────────────────────────────────────────────────────────────────────
# 진로 탐색 시스템 - Streamlit 메인 앱
# Multi-Theory Ensemble Career Assessment (MTECA)
#
# 실행: streamlit run app.py
# ────────────────────────────────────────────────────────────────────────

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd
import json
import base64

from data.questions import (
    get_assessment_plan, get_age_group,
    HOLLAND_LABELS, HOLLAND_DESC,
    MI_LABELS, MI_DESC,
    BIG5_LABELS, VALUES_LABELS, ANCHOR_LABELS,
)
from data.i18n import t, tq, tc, tcat, LANG_CONFIG
from engine.scorer import score_all_modules, get_ctci_interpretation, get_rcs_interpretation
from engine.matcher import rank_careers, get_career_fit_summary


def get_lang() -> str:
    return st.session_state.get("lang", "ko")

# ────────────────────────────────────────────────
# 페이지 설정
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="진로 탐색 시스템",
    page_icon=":compass:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ────────────────────────────────────────────────
# CSS 스타일
# ────────────────────────────────────────────────
st.markdown("""
<style>
    /* 모바일 뷰포트 */
    @media (max-width: 768px) {
        .main-title { font-size: 1.5rem !important; }
        .sub-title { font-size: 0.9rem !important; }
        .career-card { padding: 0.7rem 0.8rem !important; }
        .reason-item { font-size: 0.82rem !important; }
        .metric-val { font-size: 1.3rem !important; }
        /* 모바일에서 2열 레이아웃을 1열로 */
        [data-testid="column"] { min-width: 100% !important; }
        .stExpander { margin-bottom: 0.5rem !important; }
    }
    /* 터치 친화적 버튼 */
    .stButton > button {
        min-height: 44px;
        font-size: 1rem;
    }
    .stRadio > div > label {
        padding: 6px 4px;
        cursor: pointer;
    }
    /* 스크롤바 스타일 */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-thumb { background: #667eea60; border-radius: 3px; }
    /* 아랍어 RTL 지원 */
    [lang="ar"] .stRadio, [lang="ar"] .stMarkdown { direction: rtl; text-align: right; }

    .main-title {
        font-size: 2.2rem; font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 0.2rem;
    }
    .sub-title {
        text-align: center; color: #666; font-size: 1.05rem; margin-bottom: 2rem;
    }
    .progress-bar-container {
        background: #f0f0f0; border-radius: 10px; height: 10px; margin-bottom: 1rem;
    }
    .section-header {
        background: linear-gradient(90deg, #667eea20, transparent);
        border-left: 4px solid #667eea;
        padding: 0.6rem 1rem; border-radius: 0 8px 8px 0;
        font-weight: 700; font-size: 1.15rem; margin-bottom: 0.5rem;
        color: #333;
    }
    .theory-badge {
        display: inline-block; background: #667eea18; color: #667eea;
        border: 1px solid #667eea40; border-radius: 20px;
        padding: 2px 12px; font-size: 0.8rem; font-weight: 600; margin-right: 6px;
    }
    .career-card {
        border: 1px solid #e0e0e0; border-radius: 12px;
        padding: 1rem 1.2rem; margin-bottom: 0.8rem;
        background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: box-shadow 0.2s;
    }
    .career-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.12); }
    .fit-badge-high { background: #22c55e22; color: #16a34a; border: 1px solid #22c55e60;
        border-radius: 20px; padding: 2px 12px; font-weight: 700; font-size: 0.85rem; }
    .fit-badge-mid { background: #f59e0b22; color: #d97706; border: 1px solid #f59e0b60;
        border-radius: 20px; padding: 2px 12px; font-weight: 700; font-size: 0.85rem; }
    .fit-badge-low { background: #ef444422; color: #dc2626; border: 1px solid #ef444460;
        border-radius: 20px; padding: 2px 12px; font-weight: 700; font-size: 0.85rem; }
    .reason-item { background: #f8f9ff; border-radius: 8px; padding: 0.4rem 0.8rem;
        margin-bottom: 0.3rem; font-size: 0.88rem; border-left: 3px solid #667eea; }
    .metric-box { background: #f8f9ff; border-radius: 10px; padding: 0.8rem 1rem;
        text-align: center; border: 1px solid #e8eaf6; }
    .metric-val { font-size: 1.8rem; font-weight: 800; color: #667eea; }
    .metric-label { font-size: 0.8rem; color: #666; margin-top: 0.2rem; }
    .diff-low { background:#dcfce722; color:#16a34a; border:1px solid #22c55e60;
        border-radius:6px; padding:1px 8px; font-size:0.8rem; font-weight:600; }
    .diff-mid { background:#fef9c322; color:#ca8a04; border:1px solid #eab30860;
        border-radius:6px; padding:1px 8px; font-size:0.8rem; font-weight:600; }
    .diff-high { background:#fff7ed22; color:#ea580c; border:1px solid #f9731660;
        border-radius:6px; padding:1px 8px; font-size:0.8rem; font-weight:600; }
    .diff-very-high { background:#fef2f222; color:#dc2626; border:1px solid #f8717160;
        border-radius:6px; padding:1px 8px; font-size:0.8rem; font-weight:600; }
    .alt-careers-box { background:#f0f4ff; border-radius:8px; padding:0.5rem 0.8rem;
        margin-top:0.5rem; font-size:0.85rem; border-left:3px solid #667eea; }
    .profile-insight { background:linear-gradient(135deg,#f8f9ff,#fff8f8);
        border-radius:10px; padding:0.8rem 1rem; margin-bottom:0.6rem;
        border:1px solid #e8eaf6; }
</style>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────────
# 세션 상태 초기화
# ────────────────────────────────────────────────
def init_state():
    defaults = {
        "step": "welcome",        # welcome | info | survey | result
        "age": None,
        "name": "",
        "age_group": None,
        "plan": None,
        "current_section": 0,
        "answers": {},            # {section_key: {qid: score}}
        "results": None,
        "ranked_careers": None,
        "selected_career": None,
        "career_situation": None, # 성인 전용: 현재 진로 상황
        "lang": "ko",             # 언어 설정
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


def _render_lang_selector():
    """사이드바 / 상단 언어 선택기"""
    lang_options = list(LANG_CONFIG.keys())
    lang_labels = [f"{LANG_CONFIG[l]['flag']} {LANG_CONFIG[l]['name']}" for l in lang_options]
    current_idx = lang_options.index(st.session_state.get("lang", "ko"))
    chosen = st.selectbox(
        "🌐 Language",
        options=lang_options,
        format_func=lambda l: f"{LANG_CONFIG[l]['flag']} {LANG_CONFIG[l]['name']}",
        index=current_idx,
        key="lang_selector",
        label_visibility="collapsed",
    )
    if chosen != st.session_state.get("lang"):
        st.session_state.lang = chosen
        st.rerun()


# ────────────────────────────────────────────────
# 헬퍼 함수
# ────────────────────────────────────────────────

def go_to(step: str):
    st.session_state.step = step
    st.rerun()


def reset():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def render_progress(current: int, total: int, label: str = ""):
    pct = int(current / max(total, 1) * 100)
    st.markdown(f"""
    <div style='margin-bottom:0.5rem;'>
        <div style='display:flex;justify-content:space-between;font-size:0.82rem;color:#666;'>
            <span>{label}</span><span>{pct}%</span>
        </div>
        <div class='progress-bar-container'>
            <div style='background:linear-gradient(90deg,#667eea,#764ba2);
                border-radius:10px;height:10px;width:{pct}%;transition:width 0.3s;'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ────────────────────────────────────────────────
# 화면 1: 환영 화면
# ────────────────────────────────────────────────

def render_welcome():
    lang = get_lang()
    # 공유 링크로 접속 시 결과 미리보기 표시
    params = st.query_params
    if "r" in params:
        share_data = _decode_share_param(params["r"])
        if share_data:
            st.markdown(f'<div class="main-title">{t("shared_result", lang)}</div>', unsafe_allow_html=True)
            st.success(f"**{share_data.get('n', '')}**")
            st.markdown(f"**{t('interest_code', lang)}:** `{share_data.get('h', '')}`")
            st.markdown("**Top 5:**")
            for rank, (cname, cscore) in enumerate(share_data.get("t", []), 1):
                st.markdown(f"{rank}. **{cname}** — {cscore}")
            st.markdown("---")
            st.markdown(t("try_yourself", lang))
            if st.button(t("start_btn", lang), use_container_width=True, key="shared_start"):
                st.query_params.clear()
                st.rerun()
            return

    st.markdown(f'<div class="main-title">{t("app_title", lang)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">{t("app_subtitle", lang)}</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        st.markdown(f"**{t('time_hint', lang)}**")
        st.markdown("---")
        if st.button(t("start_btn", lang), type="primary", use_container_width=True):
            go_to("info")


# ────────────────────────────────────────────────
# 화면 2: 기본 정보 입력
# ────────────────────────────────────────────────

def render_info():
    lang = get_lang()
    info_titles = {"ko":"기본 정보 입력","en":"Basic Information","zh":"基本信息","es":"Información Básica","hi":"बुनियादी जानकारी","ar":"المعلومات الأساسية","pt":"Informações Básicas"}
    st.markdown(f'<div class="main-title">{info_titles.get(lang,"기본 정보 입력")}</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        name = st.text_input(t("name_label", lang), placeholder="Name", value=st.session_state.name)
        age = st.number_input(
            t("age_label", lang), min_value=6, max_value=80, value=st.session_state.age or 17,
        )

        age_group = get_age_group(age)
        plan = get_assessment_plan(age_group)

        age_group_labels = {
            "child":       t("age_child", lang),
            "teen":        t("age_teen", lang),
            "young_adult": t("age_young", lang),
            "adult":       t("age_adult", lang),
        }

        st.info(f"**{age_group_labels[age_group]}** — {len(plan['sections'])} modules")

        # 성인 전용: 현재 진로 상황 질문
        career_situation = None
        if age_group in ("adult", "young_adult"):
            st.markdown("---")
            situation_opts = [
                t("situation_opt1", lang),
                t("situation_opt2", lang),
                t("situation_opt3", lang),
                t("situation_opt4", lang),
            ]
            career_situation = st.radio(
                t("situation_label", lang),
                options=situation_opts,
                key="career_situation_radio",
                index=0,
            )

        # 검사 구성 미리보기
        preview_labels = {"ko":"검사 구성 확인하기","en":"Preview test structure","zh":"预览测试结构","es":"Ver estructura del test","hi":"परीक्षण संरचना देखें","ar":"معاينة هيكل الاختبار","pt":"Ver estrutura do teste"}
        with st.expander(preview_labels.get(lang, "검사 구성 확인하기")):
            for i, sec in enumerate(plan["sections"]):
                n_q = len(sec["questions"])
                st.markdown(f"**{i+1}. {sec['title']}** ({n_q})")

        st.markdown("")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(t("prev_btn", lang), use_container_width=True):
                go_to("welcome")
        with col_b:
            if st.button(t("start_btn", lang), type="primary", use_container_width=True):
                if not name.strip():
                    st.warning("Please enter your name." if lang == "en" else "이름을 입력해주세요.")
                else:
                    st.session_state.name = name
                    st.session_state.age = age
                    st.session_state.age_group = age_group
                    st.session_state.plan = plan
                    st.session_state.current_section = 0
                    st.session_state.answers = {}
                    st.session_state.career_situation = career_situation
                    go_to("survey")


# ────────────────────────────────────────────────
# 화면 3: 설문 화면
# ────────────────────────────────────────────────

LIKERT_OPTIONS_KO = ["전혀 아니다", "아니다", "보통이다", "그렇다", "매우 그렇다"]


def get_likert_options(lang: str) -> list:
    return [t(k, lang) for k in ["scale_1", "scale_2", "scale_3", "scale_4", "scale_5"]]

def render_survey():
    plan = st.session_state.plan
    current_sec_idx = st.session_state.current_section
    sections = plan["sections"]

    if current_sec_idx >= len(sections):
        # 모든 섹션 완료 → 결과 계산
        _compute_and_go_to_result()
        return

    section = sections[current_sec_idx]
    total_sections = len(sections)
    questions = section["questions"]

    # 헤더
    st.markdown(f'<div class="main-title">{section["title"]}</div>', unsafe_allow_html=True)
    render_progress(current_sec_idx + 1, total_sections,
                    f"검사 {current_sec_idx+1}/{total_sections}: {section['title']}")

    st.markdown(f'<div class="sub-title">{section["desc"]}</div>', unsafe_allow_html=True)

    # 이전 답변 로드
    sec_key = section["key"]
    if sec_key not in st.session_state.answers:
        st.session_state.answers[sec_key] = {}
    current_answers = st.session_state.answers[sec_key]

    # 강제선택 섹션 여부 판별
    is_forced_choice = sec_key in ("values", "anchors")

    if is_forced_choice:
        _render_forced_choice_section(sec_key, questions, current_answers, current_sec_idx, total_sections)
    else:
        _render_likert_section(sec_key, questions, current_answers, current_sec_idx, total_sections)


def _get_dim_label(dim: str, sec_key: str) -> str:
    """차원 레이블 - 사용자에게 노출 안 함"""
    return ""


def _render_likert_section(sec_key, questions, current_answers, current_sec_idx, total_sections):
    """리커트 5점 척도 섹션 렌더링 (Holland, MI, Big5, Maturity)"""
    lang = get_lang()
    likert_opts = get_likert_options(lang)
    # 모든 문항 키를 세션 상태에 강제 초기화 (보통이다 기본값)
    for q in questions:
        widget_key = f"q_{q['id']}"
        saved_score = current_answers.get(q["id"], None)
        if saved_score is not None:
            st.session_state[widget_key] = likert_opts[saved_score - 1]
        else:
            st.session_state[widget_key] = likert_opts[2]

    with st.form(key=f"survey_form_{current_sec_idx}"):
        for q in questions:
            qid = q["id"]
            q_text = tq(qid, lang)
            resp = st.radio(
                label=f"**{q_text}**",
                options=likert_opts,
                horizontal=True,
                key=f"q_{qid}",
            )
            current_answers[qid] = likert_opts.index(resp) + 1

        st.session_state.answers[sec_key] = current_answers
        prev_btn, next_btn = _render_nav_buttons(current_sec_idx, total_sections)

    if prev_btn:
        if current_sec_idx > 0:
            st.session_state.current_section -= 1
        else:
            go_to("info")
        st.rerun()
    if next_btn:
        st.session_state.current_section += 1
        st.rerun()


def _render_forced_choice_section(sec_key, questions, current_answers, current_sec_idx, total_sections):
    """
    강제 선택 섹션 (가치관/커리어 방향) - form 없이 실시간 카운트 반응
    """
    from data.questions import VALUES_LABELS, ANCHOR_LABELS

    labels_map = VALUES_LABELS if sec_key == "values" else ANCHOR_LABELS
    pick_n = 3 if sec_key == "values" else 2

    items = {q["dim"]: q["text"] for q in questions}
    dim_list = list(items.keys())

    st.markdown(f"""
    <div style='background:#f8f9ff;border-radius:10px;padding:0.8rem 1rem;margin-bottom:1rem;
         border-left:4px solid #667eea;'>
        아래 항목 중 <b>가장 중요한 것 {pick_n}가지</b>를 선택하세요.<br>
        <small style='color:#888;'>모든 항목이 중요해 보여도, 자신에게 진짜 우선순위인 것을 골라야 합니다.</small>
    </div>
    """, unsafe_allow_html=True)

    # 체크박스 (form 밖 → 실시간 반응)
    selected_dims = []
    for i, (dim, text) in enumerate(items.items()):
        was_checked = current_answers.get(questions[i]["id"], 1) == 5
        checked = st.checkbox(f"**{text}**", value=was_checked, key=f"fc_{sec_key}_{i}")
        if checked:
            selected_dims.append(dim)

    # 실시간 카운트 표시
    count = len(selected_dims)
    remaining = pick_n - count
    if remaining > 0:
        st.info(f"{remaining}개 더 선택해 주세요.")
    elif remaining < 0:
        st.error(f"{-remaining}개를 취소해 주세요. 정확히 {pick_n}개만 선택 가능합니다.")
    else:
        st.success("선택 완료!")

    # 점수 저장
    for i, dim in enumerate(dim_list):
        qid = questions[i]["id"]
        current_answers[qid] = 5 if dim in selected_dims else 1
    st.session_state.answers[sec_key] = current_answers

    # 이전/다음 버튼 (form 밖이므로 일반 button)
    lang = get_lang()
    _next_labels = {"ko":"다음 검사","en":"Next","zh":"下一步","es":"Siguiente","hi":"अगला","ar":"التالي","pt":"Próximo"}
    _done_labels = {"ko":"결과 확인","en":"See Results","zh":"查看结果","es":"Ver Resultados","hi":"परिणाम देखें","ar":"عرض النتائج","pt":"Ver Resultados"}
    st.markdown("")
    col_a, col_b = st.columns(2)
    with col_a:
        prev_lbl = t("prev_btn", lang) if current_sec_idx > 0 else t("home_btn", lang)
        if st.button(prev_lbl, use_container_width=True, key=f"fc_prev_{current_sec_idx}"):
            if current_sec_idx > 0:
                st.session_state.current_section -= 1
            else:
                go_to("info")
            st.rerun()
    with col_b:
        next_label = _next_labels.get(lang, "다음") if current_sec_idx < total_sections - 1 else _done_labels.get(lang, "결과 확인")
        next_disabled = (count != pick_n)
        if st.button(next_label, type="primary", use_container_width=True,
                     disabled=next_disabled, key=f"fc_next_{current_sec_idx}"):
            st.session_state.current_section += 1
            st.rerun()


def _render_nav_buttons(current_sec_idx, total_sections):
    """이전/다음 버튼 렌더링, 버튼 객체 반환"""
    lang = get_lang()
    _next_labels = {"ko":"다음 검사","en":"Next","zh":"下一步","es":"Siguiente","hi":"अगला","ar":"التالي","pt":"Próximo"}
    _done_labels = {"ko":"결과 확인","en":"See Results","zh":"查看结果","es":"Ver Resultados","hi":"परिणाम देखें","ar":"عرض النتائج","pt":"Ver Resultados"}
    col_a, col_b = st.columns(2)
    with col_a:
        prev_lbl = t("prev_btn", lang) if current_sec_idx > 0 else t("home_btn", lang)
        prev_btn = st.form_submit_button(prev_lbl, use_container_width=True)
    with col_b:
        next_label = _next_labels.get(lang, "다음") if current_sec_idx < total_sections - 1 else _done_labels.get(lang, "결과 확인")
        next_btn = st.form_submit_button(next_label, type="primary", use_container_width=True)
    return prev_btn, next_btn


def _render_profile_tab(results: dict, career_situation: str, age_group: str):
    """
    나의 종합 프로파일 탭 - MBTI보다 깊은 다차원 자기이해
    좋아하는 것 + 잘하는 것 + 가치관 + 일하는 방식 + 성장 방향을 통합해서 보여줌
    """
    st.markdown("### 나를 입체적으로 이해하기")
    st.markdown("_좋아하는 것·잘하는 것을 넘어, 어떤 환경에서·어떤 방식으로·무엇을 위해 일할 때 가장 잘 맞는지 분석합니다._")

    # ── 1. 핵심 흥미 vs 강점 (좋아하는 것 vs 잘하는 것)
    if "holland" in results and "mi" in results:
        st.markdown("---")
        st.markdown("#### 좋아하는 것 vs 잘하는 것")

        h = results["holland"]
        mi = results["mi"]

        # Holland에서 상위 2개 흥미
        top_h = sorted(h.keys(), key=lambda k: h[k], reverse=True)[:2]
        # MI에서 상위 2개 강점
        top_mi = sorted(mi.keys(), key=lambda k: mi[k], reverse=True)[:2]

        h_labels = {"R":"실용·제작","I":"탐구·분석","A":"창작·표현","S":"사람·돕기","E":"리더·설득","C":"체계·관리"}
        mi_labels_map = {
            "언어":"언어 표현력","논리수학":"논리·분석력","공간":"시각·공간력",
            "음악":"음악·리듬감","신체운동":"신체·운동능력","자연탐구":"자연·탐구력",
            "대인관계":"사람 읽는 능력","자기이해":"자기 성찰력"
        }

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""<div class='profile-insight'>
            <div style='font-weight:700;color:#667eea;margin-bottom:0.3rem;'>내가 좋아하는 활동 유형</div>""",
            unsafe_allow_html=True)
            for hk in top_h:
                st.markdown(f"- **{h_labels.get(hk, hk)}** 활동 ({int(h[hk]*100)}점)")
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            st.markdown("""<div class='profile-insight'>
            <div style='font-weight:700;color:#764ba2;margin-bottom:0.3rem;'>내가 잘하는 능력 영역</div>""",
            unsafe_allow_html=True)
            for mk in top_mi:
                st.markdown(f"- **{mi_labels_map.get(mk, mk)}** ({int(mi[mk]*100)}점)")
            st.markdown("</div>", unsafe_allow_html=True)

        # 일치도 해석
        alignment_comment = _get_interest_skill_alignment(top_h, top_mi)
        if alignment_comment:
            st.info(alignment_comment)

    # ── 2. 일하는 방식 (성격 기반)
    if "big5" in results:
        st.markdown("---")
        st.markdown("#### 나는 어떤 방식으로 일하는가")
        b5 = results["big5"]

        work_styles = _get_work_style_profile(b5)
        cols = st.columns(len(work_styles))
        for i, (label, val, desc, color) in enumerate(work_styles):
            with cols[i]:
                bar_pct = int(val * 100)
                st.markdown(f"""
                <div style='text-align:center;padding:0.6rem 0.4rem;background:#f8f9ff;
                     border-radius:10px;border:1px solid #e8eaf6;'>
                    <div style='font-size:0.75rem;color:#666;margin-bottom:0.3rem;'>{label}</div>
                    <div style='font-size:1.4rem;font-weight:800;color:{color};'>{bar_pct}</div>
                    <div style='font-size:0.7rem;color:#888;'>{desc}</div>
                </div>""", unsafe_allow_html=True)

    # ── 3. 무엇을 위해 일하는가 (가치관)
    if "values" in results:
        st.markdown("---")
        st.markdown("#### 일에서 가장 중요하게 여기는 것")
        vl = results["values"]
        top_v = sorted(vl.keys(), key=lambda k: vl[k], reverse=True)[:3]
        values_meaning = {
            "능력발휘": "내 능력을 최대한 쓸 수 있는 일을 원합니다",
            "자율성": "스스로 결정하고 자유롭게 일하고 싶습니다",
            "보수": "경제적 보상이 일의 중요한 동기입니다",
            "안정성": "오래 안정적으로 일할 수 있는 환경을 원합니다",
            "사회적인정": "내 일이 사회에서 인정받길 원합니다",
            "사회봉사": "다른 사람에게 도움이 되는 일을 하고 싶습니다",
            "자기계발": "계속 배우고 성장하는 일을 원합니다",
            "창의성": "창의적으로 새로운 것을 만드는 일을 원합니다",
            "대인관계": "좋은 사람들과 함께 일하고 싶습니다",
        }
        for i, vk in enumerate(top_v, 1):
            meaning = values_meaning.get(vk, vk)
            st.markdown(f"""
            <div class='profile-insight'>
                <span style='font-weight:800;color:#f59e0b;font-size:1.1rem;'>{i}순위</span>
                <span style='font-weight:700;margin-left:0.5rem;'>{vk}</span>
                <span style='color:#555;margin-left:0.5rem;font-size:0.9rem;'>— {meaning}</span>
            </div>""", unsafe_allow_html=True)

    # ── 4. 리스크 프로파일 & 환경 적합도
    if "big5" in results and "values" in results:
        st.markdown("---")
        st.markdown("#### 나에게 맞는 직업 환경")
        risk_profile = _get_environment_fit(results)
        st.markdown(risk_profile, unsafe_allow_html=True)

    # ── 5. 성인 전용: 현재 상황별 맞춤 해석
    if age_group in ("adult", "young_adult") and career_situation:
        st.markdown("---")
        st.markdown("#### 현재 상황에 맞는 조언")
        _render_adult_situation_advice(career_situation, results)


def _get_interest_skill_alignment(top_h: list, top_mi: list) -> str:
    """흥미-강점 일치도 코멘트"""
    # 흥미유형과 강점지능의 자연스러운 연결
    h_mi_links = {
        "R": ["신체운동", "공간", "자연탐구"],
        "I": ["논리수학", "자연탐구", "공간"],
        "A": ["언어", "음악", "공간"],
        "S": ["대인관계", "언어", "자기이해"],
        "E": ["대인관계", "언어", "자기이해"],
        "C": ["논리수학", "언어"],
    }
    matches = 0
    for hk in top_h:
        for mk in top_mi:
            if mk in h_mi_links.get(hk, []):
                matches += 1
    if matches >= 2:
        return "흥미와 강점이 매우 잘 일치합니다. 자연스럽게 잘할 수 있는 분야를 좋아하는 유형입니다. 해당 분야에서 전문성을 키우면 강점이 됩니다."
    elif matches == 1:
        return "흥미와 강점이 일부 겹칩니다. 좋아하는 분야를 더 연습하면 강점으로 발전할 수 있습니다."
    else:
        return "흥미와 강점이 다른 방향을 가리킵니다. 좋아하는 일을 해도 될지, 잘하는 일을 해도 될지 두 방향을 모두 탐색해보세요."


def _get_work_style_profile(b5: dict) -> list:
    """성격 기반 일하는 방식 프로파일 반환 [(라벨, 값, 설명, 색)]"""
    e_val = b5.get("E", 0.5)
    c_val = b5.get("C", 0.5)
    o_val = b5.get("O", 0.5)
    a_val = b5.get("A", 0.5)
    n_val = b5.get("N", 0.5)

    styles = [
        ("혼자 vs 함께", e_val,
         "함께 일하기 선호" if e_val > 0.6 else ("혼자 집중 선호" if e_val < 0.4 else "유연"),
         "#667eea"),
        ("자유 vs 체계", 1 - c_val if c_val < 0.5 else c_val,
         "체계적·계획적" if c_val > 0.6 else ("자유·유연" if c_val < 0.4 else "균형"),
         "#764ba2"),
        ("창의 vs 안정", o_val,
         "새로운 도전 선호" if o_val > 0.6 else ("익숙한 환경 선호" if o_val < 0.4 else "균형"),
         "#f59e0b"),
        ("경쟁 vs 협력", a_val,
         "협력·배려 중심" if a_val > 0.6 else ("독립·경쟁 선호" if a_val < 0.4 else "균형"),
         "#22c55e"),
        ("감정 안정성", n_val,
         "스트레스 내성 높음" if n_val > 0.6 else ("고압 환경 주의" if n_val < 0.4 else "보통"),
         "#ef4444"),
    ]
    return styles


def _get_environment_fit(results: dict) -> str:
    """가치관 + 성격 기반 환경 적합도 HTML"""
    vl = results.get("values", {})
    b5 = results.get("big5", {})
    anchors = results.get("anchors", {})

    stability = vl.get("안정성", 0.5)
    autonomy = vl.get("자율성", 0.5)
    creativity = vl.get("창의성", 0.5)
    service = vl.get("사회봉사", 0.5)
    openness = b5.get("O", 0.5)
    conscientious = b5.get("C", 0.5)

    environments = []

    if stability > 0.65:
        environments.append(("공공기관·대기업", "안정적인 조직 환경이 잘 맞습니다", "#22c55e"))
    if autonomy > 0.65 and openness > 0.6:
        environments.append(("스타트업·프리랜서", "자율성이 보장된 유연한 환경이 맞습니다", "#667eea"))
    if creativity > 0.65:
        environments.append(("크리에이티브 직군", "창의적 표현이 가능한 환경이 맞습니다", "#f59e0b"))
    if service > 0.7:
        environments.append(("사회공헌 조직·NGO·교육", "사람을 직접 돕는 환경이 맞습니다", "#764ba2"))
    if conscientious > 0.7 and stability > 0.6:
        environments.append(("전문직·연구직", "정확성과 전문성이 요구되는 환경이 맞습니다", "#ef4444"))

    if not environments:
        environments.append(("다양한 환경", "특정 환경에 제한 없이 적응 가능한 유형입니다", "#667eea"))

    html = "<div style='display:flex;flex-wrap:wrap;gap:0.5rem;'>"
    for label, desc, color in environments:
        html += f"""<div style='background:{color}18;border:1px solid {color}60;border-radius:10px;
            padding:0.6rem 0.9rem;flex:1;min-width:200px;'>
            <div style='font-weight:700;color:{color};'>{label}</div>
            <div style='font-size:0.83rem;color:#555;margin-top:0.2rem;'>{desc}</div>
        </div>"""
    html += "</div>"
    return html


def _render_adult_situation_advice(situation: str, results: dict):
    """성인의 현재 상황별 맞춤 조언"""
    vl = results.get("values", {})
    b5 = results.get("big5", {})
    anchors = results.get("anchors", {})

    if "처음" in situation:
        st.markdown("""
        <div class='profile-insight'>
        <b>방향 찾기 전략</b><br>
        직업 추천 탭의 상위 3개 직업을 먼저 탐색하세요.
        흥미와 강점이 모두 높은 직업이 장기적으로 지속 가능한 커리어가 됩니다.
        </div>""", unsafe_allow_html=True)

    elif "성장" in situation:
        top_anchor = max(anchors.keys(), key=lambda k: anchors[k]) if anchors else None
        anchor_labels = {
            "전문역량": "현재 직무의 전문성을 더 깊이 파고드세요 — 해당 분야 자격증·석사를 고려하세요.",
            "관리역량": "팀 리더·프로젝트 관리 경험을 쌓으세요.",
            "자율독립": "부업·사이드 프로젝트로 자신만의 영역을 만들어가세요.",
            "안전안정": "현 직장에서 핵심 포지션을 확보하는 방향으로 성장하세요.",
            "기업가창의": "사내 혁신팀·신사업 기회를 찾아보세요.",
            "봉사헌신": "사회공헌 활동·멘토링을 커리어에 통합해보세요.",
        }
        advice = anchor_labels.get(top_anchor, "현재 강점을 심화하는 방향으로 성장 계획을 세워보세요.")
        st.markdown(f"""
        <div class='profile-insight'>
        <b>현직 성장 전략</b><br>
        당신의 핵심 커리어 동기: <b>{top_anchor}</b><br>
        {advice}
        </div>""", unsafe_allow_html=True)

    elif "이직" in situation or "전환" in situation:
        # 현재 가치관과 다른 방향 제시
        top_v = sorted(vl.keys(), key=lambda k: vl[k], reverse=True)[:2]
        st.markdown(f"""
        <div class='profile-insight'>
        <b>이직/전환 포인트</b><br>
        이직 시 가장 먼저 점검해야 할 것: 새 직장이 내 핵심 가치관 (<b>{', '.join(top_v)}</b>)을 충족하는가?<br>
        직업 추천 결과에서 현재 카테고리가 아닌 다른 분야의 직업도 확인해보세요.
        </div>""", unsafe_allow_html=True)

    elif "번아웃" in situation or "혼란" in situation:
        service_val = vl.get("사회봉사", 0)
        autonomy_val = vl.get("자율성", 0)
        n_val = b5.get("N", 0.5)
        if n_val < 0.5:
            st.warning("현재 감정 안정성 지표가 낮게 나타났습니다. 직업 결정 전 충분한 회복 시간을 갖는 것을 권장합니다.")
        st.markdown(f"""
        <div class='profile-insight'>
        <b>회복 후 방향 재점검</b><br>
        번아웃의 주요 원인은 가치관과 실제 업무의 불일치입니다.<br>
        당신이 중요하게 여기는 것(<b>{', '.join(sorted(vl.keys(), key=lambda k:vl[k], reverse=True)[:2])}</b>)이
        현재 직업에서 충족되고 있는지 점검해보세요.<br>
        직업 추천 결과에서 가치관 점수가 높은 직업을 우선 살펴보세요.
        </div>""", unsafe_allow_html=True)


def _compute_and_go_to_result():
    with st.spinner("결과를 분석하는 중입니다..."):
        plan = st.session_state.plan
        answers = st.session_state.answers
        age_group = st.session_state.age_group

        results = score_all_modules(answers, plan)
        ranked = rank_careers(results, age_group, top_n=12)

        st.session_state.results = results
        st.session_state.ranked_careers = ranked

    go_to("result")


# ────────────────────────────────────────────────
# 직업별 상세 정보 (연봉 실데이터, 취업 경로)
# 출처: 고용노동부 임금정보시스템, 커리어넷 (2024 기준)
# ────────────────────────────────────────────────
CAREER_DETAIL_DB = {
    "software_dev":      {"salary_range": "3,500~7,000만원 (신입~5년차)", "career_path": ["컴퓨터공학 전공 or 부트캠프", "공개 채용 / 인턴십 지원", "주니어 개발자 1~3년", "시니어 / 풀스택 3~7년", "테크리드 or 창업"]},
    "data_scientist":    {"salary_range": "4,000~9,000만원", "career_path": ["통계·수학·CS 전공 (대학원 권장)", "Kaggle 등 포트폴리오 구축", "주니어 분석가 2~3년", "시니어 데이터 과학자", "ML 리서처 or 수석 과학자"]},
    "ai_engineer":       {"salary_range": "4,500~1억원+", "career_path": ["CS/수학 대학원", "논문 및 오픈소스 기여", "AI 스타트업 or 대기업 연구소", "ML 엔지니어 → 리서처", "AI 연구소 팀장"]},
    "doctor":            {"salary_range": "1억~2억5천만원 (전문의 기준)", "career_path": ["의과대학 6년", "인턴 1년 + 레지던트 4년", "전문의 자격 취득", "개원 or 대학병원 교수 트랙"]},
    "lawyer":            {"salary_range": "4,000~1억5천만원 (경력별)", "career_path": ["법학전문대학원(로스쿨) 3년", "변호사 시험 합격", "로펌 or 검사/판사 임용", "파트너 변호사 or 전문 분야 개업"]},
    "teacher":           {"salary_range": "3,200~5,500만원 (공립 기준)", "career_path": ["사범대 or 교직 이수", "임용고시 준비·합격", "기간제 교사 → 정교사", "수석교사 or 교감·교장"]},
    "nurse":             {"salary_range": "3,000~5,000만원", "career_path": ["간호학과 4년", "국가시험 합격 (간호사 면허)", "병원 신규 간호사", "전문 간호사 자격 취득", "수간호사 or 관리직"]},
    "pharmacist":        {"salary_range": "4,000~7,000만원", "career_path": ["약학대학 6년", "약사 면허 취득", "약국 취업 or 병원 약사", "개인 약국 창업"]},
    "architect":         {"salary_range": "3,000~7,000만원", "career_path": ["건축학과 5년", "건축사 시험 준비 (실무 3년)", "건축사 자격 취득", "설계사무소 or 건설사"]},
    "accountant":        {"salary_range": "3,500~8,000만원 (CPA 기준)", "career_path": ["경영·회계학과", "공인회계사(CPA) 시험", "회계법인 입사 (Big4 등)", "파트너 or CFO 트랙"]},
    "journalist":        {"salary_range": "3,000~6,000만원", "career_path": ["언론학·국문학 전공", "방송·신문사 공채 준비", "수습기자 1년", "취재기자 → 데스크 → 부장"]},
    "designer_graphic":  {"salary_range": "2,500~5,500만원", "career_path": ["시각디자인 전공 or 독학", "포트폴리오 구축", "디자인 에이전시 or 인하우스", "시니어 디자이너 / 아트디렉터"]},
    "musician":          {"salary_range": "불규칙 (무대·음반 수입 중심)", "career_path": ["음악 전공 or 독학 (재능 필수)", "콩쿠르·오디션 참가", "연주·레코딩 활동", "앙상블 or 솔로 무대", "교수직 병행 가능"]},
    "chef":              {"salary_range": "2,200~6,000만원 (경력별)", "career_path": ["조리학과 or 요리학원", "레스토랑 보조 요리사", "수셰프(부주방장)", "총주방장 or 오너셰프"]},
    "researcher":        {"salary_range": "4,000~8,000만원 (정부출연연 기준)", "career_path": ["이공계 대학원 (박사 권장)", "포스트닥터(포닥)", "연구소 입소 or 교수 공채", "책임연구원 or 부교수"]},
    "professor":         {"salary_range": "5,000~9,000만원", "career_path": ["박사 학위 취득", "포닥/연구원 경험", "신진교수 공개채용 (경쟁률 높음)", "조교수 → 부교수 → 정교수"]},
    "police":            {"salary_range": "3,000~5,500만원", "career_path": ["경찰대학 or 경찰공무원 채용시험", "순경 임용", "경장 → 경사 → 경위 (승진시험)", "경찰서 각 부서 순환 근무"]},
    "firefighter":       {"salary_range": "3,000~5,200만원", "career_path": ["소방공무원 채용시험 합격", "소방사 임용 (체력 필수)", "소방장 → 소방위 승진", "구조대·구급대 등 특수부서"]},
    "social_worker":     {"salary_range": "2,500~4,000만원", "career_path": ["사회복지학과", "사회복지사 1급 자격증", "복지관·NGO 취업", "시설장 or 전문 상담사"]},
    "counselor":         {"salary_range": "2,800~5,000만원", "career_path": ["심리학·상담학 전공 (석사 권장)", "임상심리사·상담심리사 자격", "상담센터·학교상담 취업", "사설 상담소 개업"]},
    "financial_analyst": {"salary_range": "4,000~1억원+ (성과급 포함)", "career_path": ["경제·경영·수학 전공", "증권사·투자은행 인턴", "애널리스트 CFA 취득", "선임 애널리스트 / 펀드매니저"]},
    "marketing_manager": {"salary_range": "3,500~7,000만원", "career_path": ["경영·광고·미디어 전공", "마케팅 인턴십 경험", "대리 → 과장 → 마케팅 팀장", "CMO (최고마케팅책임자)"]},
    "entrepreneur":      {"salary_range": "불규칙 (초기 낮음→성공 시 무제한)", "career_path": ["아이디어·시장조사", "팀 구성 + 투자 유치 (AC/VC)", "MVP 출시 → 피드백 반복", "스케일업 → 투자 시리즈 A/B", "IPO or M&A 엑싯"]},
    "pilot":             {"salary_range": "7,000만~1억5천만원 (항공사 기준)", "career_path": ["항공운항학과 or 공군 조종사", "자가용 조종사(PPL) → 계기비행(IR) → 사업용(CPL)", "부기장 채용 (500시간+)", "기장 승격 (3,000시간+)"]},
    "dentist":           {"salary_range": "8,000만~2억원", "career_path": ["치과대학 6년", "치과의사 면허 취득", "인턴·레지던트 (전문의 선택)", "치과 개원 or 대학병원 교수"]},
    "clinical_psychologist": {"salary_range": "3,000~5,500만원", "career_path": ["심리학 전공 (석사·박사 권장)", "임상심리사 2급→1급 자격", "병원·센터 수련 3년", "정신건강임상심리사"]},
    "kindergarten_teacher": {"salary_range": "2,200~3,800만원", "career_path": ["유아교육학과 or 아동학과", "보육교사 2급 → 1급 자격", "어린이집·유치원 취업", "원장 자격증 취득 후 개원"]},
    "hr_manager":        {"salary_range": "3,500~7,000만원", "career_path": ["경영·심리·교육학 전공", "채용담당 or 노무팀 입사", "HR 제너럴리스트 경력", "CHRO (최고인사책임자)"]},
    "tax_accountant":    {"salary_range": "4,000~9,000만원 (개업 시 변동)", "career_path": ["세무·회계학 전공", "세무사 시험 합격", "세무법인 or 세무서 근무", "개인 세무 사무소 개업"]},
    "actuary":           {"salary_range": "5,000~1억2천만원", "career_path": ["수학·통계·보험계리학 전공", "계리사 1차→2차 시험 합격", "보험사·연금공단 입사", "선임 계리사 → 계리 부서장"]},
    "webtoon_artist":    {"salary_range": "불규칙 (플랫폼 정산, 상위 작가 수억원)", "career_path": ["그림 실력 독학 or 학원", "단편 웹툰 플랫폼 공모전 도전", "연재 작가 계약", "인기 작품→2차 저작물(드라마·굿즈)"]},
    "vr_ar_developer":   {"salary_range": "4,000~8,000만원", "career_path": ["컴퓨터공학·게임공학 전공", "Unity/Unreal 포트폴리오", "게임사 or XR 스타트업 입사", "시니어 XR 개발자"]},
    "biotech_researcher":{"salary_range": "3,500~7,000만원", "career_path": ["생명공학·화학·의학 전공 (대학원)", "연구소 인턴십", "바이오테크 기업 입사", "연구책임자 or 기술이전 전문가"]},
    "renewable_energy_engineer": {"salary_range": "3,500~7,000만원", "career_path": ["기계·전기·환경공학 전공", "에너지공단·발전사 취업", "태양광·풍력 설계 엔지니어", "신재생에너지 PM"]},
    "urban_planner":     {"salary_range": "3,500~6,500만원", "career_path": ["도시공학·건축·지리학 전공", "국토연구원·LH공사 입사", "도시계획기사 자격증", "도시계획 전문위원"]},
    "flight_attendant":  {"salary_range": "3,000~5,500만원 (항공사별 차이)", "career_path": ["어학능력 준비 (영어 필수)", "항공사 채용 공고 지원", "훈련원 교육 (6~8주)", "국내선 → 국제선 → 사무장"]},
    "game_developer":    {"salary_range": "3,500~7,000만원", "career_path": ["컴퓨터공학·게임공학 전공", "개인 게임 포트폴리오 제작", "게임사 공채 or 인디 개발", "리드 개발자 → 게임 디렉터"]},
}

# ────────────────────────────────────────────────
# 결과 공유 URL 생성 / HTML 보고서 생성
# ────────────────────────────────────────────────

def _generate_share_url(name: str, holland_code: str, ranked: list) -> str:
    """상위 결과를 base64로 인코딩한 공유 URL 반환"""
    share_data = {
        "n": name,
        "h": holland_code,
        "t": [(r["career_name"], round(r["score"])) for r in ranked[:5]],
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(share_data, ensure_ascii=False).encode()
    ).decode()
    base_url = st.secrets.get("APP_URL", "https://jinro-assessment.onrender.com")
    return f"{base_url}/?r={encoded}"


def _decode_share_param(param: str) -> dict | None:
    """URL 공유 파라미터 디코딩"""
    try:
        decoded = base64.urlsafe_b64decode(param.encode()).decode()
        return json.loads(decoded)
    except Exception:
        return None


def _generate_html_report(name: str, age_group: str, holland_code: str,
                           results: dict, ranked: list) -> str:
    """다운로드용 HTML 보고서 생성"""
    age_label = {"child": "아동", "teen": "청소년", "young_adult": "청년", "adult": "성인"}.get(age_group, "")

    top_careers_html = ""
    for i, fit in enumerate(ranked[:8]):
        c = fit["career_data"]
        diff = c.get("difficulty", "보통")
        diff_color = {"낮음": "#22c55e", "보통": "#3b82f6", "높음": "#f59e0b", "매우 높음": "#ef4444"}.get(diff, "#888")
        reasons_html = "".join(
            f"<li><b>[{r['theory']}]</b> {r['detail']}</li>"
            for r in fit.get("top_reasons", [])[:3]
        )
        detail = CAREER_DETAIL_DB.get(c["id"], {})
        salary_str = detail.get("salary_range", c.get("salary_level", ""))
        top_careers_html += f"""
        <div style="border:1px solid #e5e7eb;border-radius:10px;padding:14px;margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:1.1rem;font-weight:700;">{i+1}. {c['name']}</span>
                <span style="background:#667eea;color:white;padding:3px 10px;border-radius:20px;font-size:0.9rem;">{fit['score']:.0f}점</span>
            </div>
            <div style="color:#555;font-size:0.9rem;margin:6px 0;">{c['description']}</div>
            <div style="font-size:0.85rem;">
                <b>학력:</b> {c['education']} &nbsp;|&nbsp;
                <b>예상 연봉:</b> {salary_str} &nbsp;|&nbsp;
                <b>성장성:</b> {c['job_growth']} &nbsp;|&nbsp;
                <b style="color:{diff_color}">난이도: {diff}</b>
            </div>
            <ul style="font-size:0.85rem;margin:6px 0 0 0;">{reasons_html}</ul>
        </div>"""

    holland_html = ""
    if "holland" in results:
        for k, v in results["holland"].items():
            pct = int(v * 100)
            holland_html += f"""
            <div style="margin-bottom:6px;">
                <span style="display:inline-block;width:80px;">{k}</span>
                <div style="display:inline-block;background:#e5e7eb;width:200px;height:12px;border-radius:6px;vertical-align:middle;">
                    <div style="background:#667eea;width:{pct * 2}px;height:12px;border-radius:6px;"></div>
                </div>
                <span style="margin-left:8px;font-size:0.85rem;">{pct}</span>
            </div>"""

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{name}님 진로 탐색 결과</title>
<style>
  body {{ font-family: 'Malgun Gothic', sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1a1a2e; }}
  h1 {{ background: linear-gradient(135deg,#667eea,#764ba2); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
  .meta {{ background:#f8f9ff; border-radius:10px; padding:14px; margin-bottom:20px; }}
  @media print {{ body {{ margin:20px; }} }}
</style>
</head>
<body>
<h1>진로 탐색 결과 보고서</h1>
<div class="meta">
  <b>이름:</b> {name} &nbsp;&nbsp; <b>연령대:</b> {age_label} &nbsp;&nbsp; <b>흥미 코드:</b> {holland_code}
  <br><small style="color:#888;">본 결과는 다중이론 앙상블(MTECA) 기반 진로 탐색 프로그램이 생성한 참고 자료입니다.</small>
</div>

<h2 style="margin-bottom:10px;">추천 직업 상위 8개</h2>
{top_careers_html}

<h2 style="margin-bottom:10px;">흥미 유형 프로파일</h2>
<div style="padding:10px;">{holland_html}</div>

<p style="color:#999;font-size:0.8rem;margin-top:30px;border-top:1px solid #eee;padding-top:10px;">
생성일: {pd.Timestamp.now().strftime('%Y년 %m월 %d일')} | 진로 탐색 시스템 (jinro-assessment.onrender.com)
</p>
</body></html>"""
    return html


# ────────────────────────────────────────────────
# 화면 4: 결과 화면
# ────────────────────────────────────────────────

def render_result():
    results = st.session_state.results
    ranked = st.session_state.ranked_careers
    name = st.session_state.name
    age_group = st.session_state.age_group

    lang = get_lang()
    _result_titles = {
        "ko": f"{name}님의 진로 탐색 결과",
        "en": f"{name}'s Career Results",
        "zh": f"{name}的职业探索结果",
        "es": f"Resultados de {name}",
        "hi": f"{name} के करियर परिणाम",
        "ar": f"نتائج {name}",
        "pt": f"Resultados de {name}",
    }
    st.markdown(f'<div class="main-title">{_result_titles.get(lang, _result_titles["ko"])}</div>', unsafe_allow_html=True)

    # ── 상단 핵심 지표
    holland_code = results.get("holland_code", "---")
    top1 = ranked[0] if ranked else None
    top1_name = top1["career_name"] if top1 else "-"
    top1_score = f"{top1['score']:.0f}점" if top1 else "-"
    top_category = top1["career_data"]["category"] if top1 else "-"

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
        <div class='metric-box'>
            <div class='metric-val'>{holland_code}</div>
            <div class='metric-label'>{t("interest_code", lang)}</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        top1_display = tc(top1["career_id"], lang) if top1 and lang != "ko" else top1_name
        st.markdown(f"""
        <div class='metric-box'>
            <div class='metric-val' style='font-size:1.3rem;'>{top1_display}</div>
            <div class='metric-label'>{t("top1_career", lang)}</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class='metric-box'>
            <div class='metric-val'>{top1_score}</div>
            <div class='metric-label'>{t("top_score", lang)}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    has_maturity = "maturity" in results
    tab_labels = [
        t("tab_recommend", lang), t("tab_profile", lang), t("tab_holland", lang),
        t("tab_mi", lang), t("tab_values", lang), t("tab_personality", lang),
    ]
    if has_maturity:
        tab_labels.append(t("tab_maturity", lang))
    tabs = st.tabs(tab_labels)

    # ──────────────────────────────────
    # 탭 1: 직업 추천
    # ──────────────────────────────────
    with tabs[0]:
        # 상황 반영 안내 배너
        situation = st.session_state.get("career_situation")
        if situation:
            situation_guide = {
                "처음 직업 방향을 정하고 있습니다":
                    "흥미·강점·가치관을 종합해 가장 잘 맞는 직업을 추천합니다. 상위 3개를 중심으로 탐색해보세요.",
                "현재 직업에서 성장 방향을 찾고 있습니다":
                    "현재 커리어 방향성과 일치하는 직업군을 우선 확인하세요. '나의 프로파일' 탭의 성장 전략도 참고하세요.",
                "이직 또는 직무 전환을 고려 중입니다":
                    "현재 업종과 다른 카테고리 직업도 살펴보세요. 필터로 카테고리를 바꿔 새로운 방향을 탐색할 수 있습니다.",
                "번아웃 또는 진로 혼란 상태입니다":
                    "가치관 일치도(녹색)가 높은 직업을 우선 확인하세요. 지금 느끼는 공허함은 가치관 불일치 신호일 수 있습니다.",
            }
            guide_msg = situation_guide.get(situation, "")
            if guide_msg:
                st.info(f"**현재 상황:** {situation}\n\n{guide_msg}")

        st.markdown(f"### {t('top12_title', lang)}")

        # 카테고리 필터
        categories = sorted(set(c["category"] for c in [r["career_data"] for r in ranked]))
        all_cats_ko = ["전체"] + categories
        all_cats_display = [t("all_category", lang)] + [tcat(c, lang) for c in categories]
        sel_cat_display = st.selectbox(t("category_filter", lang), all_cats_display)
        sel_cat_ko = all_cats_ko[all_cats_display.index(sel_cat_display)]

        filtered = [r for r in ranked if sel_cat_ko == "전체" or r["career_data"]["category"] == sel_cat_ko]

        for i, fit in enumerate(filtered):
            score = fit["score"]
            lo = fit["confidence_lo"]
            hi = fit["confidence_hi"]
            career = fit["career_data"]
            reasons = fit["top_reasons"]
            summary = get_career_fit_summary(fit)
            career_display_name = tc(career["id"], lang)

            badge_cls = "fit-badge-high" if score >= 60 else "fit-badge-mid" if score >= 45 else "fit-badge-low"
            rank_label = "[#1]" if i == 0 else f"#{i+1}"

            with st.expander(
                f"{rank_label}  {career_display_name}  |  {score:.0f}  ({lo:.0f}~{hi:.0f})",
                expanded=(i == 0)
            ):
                col_l, col_r = st.columns([2, 1])
                with col_l:
                    # 적합도 + 카테고리 배지
                    diff = career.get("difficulty", "보통")
                    diff_cls = {"낮음": "diff-low", "보통": "diff-mid",
                                "높음": "diff-high", "매우 높음": "diff-very-high"}.get(diff, "diff-mid")
                    diff_display = t({"낮음":"diff_low","보통":"diff_mid","높음":"diff_high","매우 높음":"diff_very_high"}.get(diff,"diff_mid"), lang)
                    cat_display = tcat(career["category"], lang)
                    st.markdown(
                        f"<span class='{badge_cls}'>{summary}</span> "
                        f"<span class='theory-badge'>{cat_display}</span> "
                        f"<span class='{diff_cls}'>{t('difficulty_label', lang)}: {diff_display}</span>",
                        unsafe_allow_html=True
                    )
                    st.markdown(f"**{career['description']}**")

                    # 추천 이유
                    if reasons:
                        st.markdown("**이 직업이 추천된 이유:**")
                        for r in reasons:
                            st.markdown(
                                f"<div class='reason-item'><b>[{r['theory']}]</b> {r['detail']}</div>",
                                unsafe_allow_html=True
                            )

                    # 기본 정보
                    # 상세 정보 (연봉 실데이터 우선)
                    detail = CAREER_DETAIL_DB.get(career["id"], {})
                    salary_display = detail.get("salary_range") or career["salary_level"]
                    st.markdown(f"""
                    - **{t('education_label', lang)}:** {career['education']}
                    - **{t('salary_label', lang)}:** {salary_display}
                    - **{t('growth_label', lang)}:** {career['job_growth']}
                    - **{t('major_label', lang)}:** {', '.join(career.get('related_majors', []))}
                    """)

                    # 취업 경로 (있을 때만)
                    career_path = detail.get("career_path")
                    if career_path:
                        steps = " → ".join(career_path)
                        st.markdown(
                            f"<div style='background:#f0f4ff;border-radius:8px;padding:0.5rem 0.8rem;"
                            f"margin-top:0.3rem;font-size:0.84rem;border-left:3px solid #667eea;'>"
                            f"<b>{t('path_label', lang)}:</b> {steps}</div>",
                            unsafe_allow_html=True
                        )

                    # 재능 전제 경고
                    talent_note = career.get("talent_note", "")
                    if talent_note:
                        st.markdown(
                            f"<div style='background:#fff7ed;border-radius:8px;padding:0.5rem 0.8rem;"
                            f"margin-top:0.4rem;border-left:3px solid #f97316;font-size:0.85rem;'>"
                            f"<b>{t('notice_caution', lang)}:</b> {talent_note}</div>",
                            unsafe_allow_html=True
                        )

                    # 대안 직업 (접근하기 쉬운 경로)
                    alt_careers = career.get("alt_careers", [])
                    if alt_careers:
                        alts_str = " · ".join(alt_careers)
                        st.markdown(
                            f"<div class='alt-careers-box'>"
                            f"<b>{t('alt_label', lang)}:</b> {alts_str}"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                with col_r:
                    # 나와 이 직업의 특성별 일치도
                    module_sc = fit["module_scores"]
                    if module_sc:
                        _mn = {
                            "ko": {"holland":"활동 흥미","mi":"강점 능력","big5":"성격","values":"직업 가치관","anchors":"성장 방향"},
                            "en": {"holland":"Interests","mi":"Strengths","big5":"Personality","values":"Values","anchors":"Career Dir."},
                            "zh": {"holland":"兴趣","mi":"优势","big5":"性格","values":"价值观","anchors":"职业方向"},
                            "es": {"holland":"Intereses","mi":"Aptitudes","big5":"Personalidad","values":"Valores","anchors":"Dirección"},
                            "hi": {"holland":"रुचि","mi":"ताकत","big5":"व्यक्तित्व","values":"मूल्य","anchors":"दिशा"},
                            "ar": {"holland":"الاهتمامات","mi":"نقاط القوة","big5":"الشخصية","values":"القيم","anchors":"الاتجاه"},
                            "pt": {"holland":"Interesses","mi":"Aptidões","big5":"Personalidade","values":"Valores","anchors":"Direção"},
                        }
                        module_names = _mn.get(lang, _mn["ko"])
                        labels = [module_names.get(k, k) for k in module_sc.keys()]
                        values_list = list(module_sc.values())
                        # 색: 70+ 녹색, 50~70 노랑, 50미만 빨강
                        bar_colors = [
                            "#22c55e" if v >= 70 else "#f59e0b" if v >= 50 else "#ef4444"
                            for v in values_list
                        ]
                        fig = go.Figure(go.Bar(
                            x=labels, y=values_list,
                            marker_color=bar_colors,
                            text=[f"{v:.0f}" for v in values_list],
                            textposition="outside",
                        ))
                        fig.update_layout(
                            title=dict(text=t("match_chart_title", lang), font=dict(size=12)),
                            height=240, margin=dict(l=5, r=5, t=35, b=5),
                            yaxis=dict(range=[0, 110], showgrid=True),
                            showlegend=False,
                            plot_bgcolor="rgba(0,0,0,0)",
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        st.caption(t("match_caption", lang))

    # ──────────────────────────────────
    # 탭 2: 나의 종합 프로파일 (심층 분석)
    # ──────────────────────────────────
    with tabs[1]:
        _render_profile_tab(results, st.session_state.get("career_situation"), age_group)

    # ──────────────────────────────────
    # 탭 3: 흥미 프로파일 (Holland)
    # ──────────────────────────────────
    with tabs[2]:
        if "holland" in results:
            h = results["holland"]
            dims = list(h.keys())
            vals = [h[d] * 100 for d in dims]
            labels = [HOLLAND_LABELS.get(d, d) for d in dims]

            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=labels + [labels[0]],
                fill="toself",
                fillcolor="rgba(102,126,234,0.2)",
                line=dict(color="#667eea", width=2),
                name="나의 흥미 프로파일",
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=False, height=420,
                title="나의 흥미 유형 프로파일",
            )
            st.plotly_chart(fig, use_container_width=True)

            # 상위 유형 설명
            top_types = sorted(dims, key=lambda d: h[d], reverse=True)[:3]
            st.markdown(f"**나의 흥미 유형 코드: `{results.get('holland_code', '')}`**")
            for d in top_types:
                score_pct = int(h[d] * 100)
                st.markdown(f"""
                <div style='background:#f8f9ff;border-radius:8px;padding:0.5rem 0.8rem;margin-bottom:0.5rem;'>
                    <b>{HOLLAND_LABELS.get(d, d)}</b> ({score_pct}점): {HOLLAND_DESC.get(d, '')}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("이 연령대에서는 흥미 유형 검사를 실시하지 않았습니다.")

    # ──────────────────────────────────
    # 탭 4: 다중지능 프로파일
    # ──────────────────────────────────
    with tabs[3]:
        if "mi" in results:
            mi = results["mi"]
            dims = list(mi.keys())
            vals = [mi[d] * 100 for d in dims]
            labels = [MI_LABELS.get(d, d) for d in dims]

            fig = px.bar(
                x=vals, y=labels, orientation="h",
                color=vals,
                color_continuous_scale=["#e8eaf6", "#667eea", "#3f51b5"],
                labels={"x": "점수 (0-100)", "y": "강점 영역"},
                title="나의 강점 지능 프로파일",
            )
            fig.update_layout(
                height=400, coloraxis_showscale=False,
                xaxis=dict(range=[0, 100]),
                plot_bgcolor="rgba(0,0,0,0)",
            )
            fig.update_traces(text=[f"{v:.0f}" for v in vals], textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

            # 상위 지능 설명
            top_mi = sorted(dims, key=lambda d: mi[d], reverse=True)[:3]
            st.markdown("**강점 지능 TOP 3:**")
            for d in top_mi:
                score_pct = int(mi[d] * 100)
                st.markdown(f"""
                <div style='background:#f8f9ff;border-radius:8px;padding:0.5rem 0.8rem;margin-bottom:0.5rem;'>
                    <b>{MI_LABELS.get(d, d)}</b> ({score_pct}점): {MI_DESC.get(d, '')}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("이 연령대에서는 강점 지능 검사를 실시하지 않았습니다.")

    # ──────────────────────────────────
    # 탭 5: 가치관 분석
    # ──────────────────────────────────
    with tabs[4]:
        col_v, col_a = st.columns(2)

        with col_v:
            if "values" in results:
                vl = results["values"]
                dims = list(vl.keys())
                vals = [vl[d] * 100 for d in dims]
                labels = [VALUES_LABELS.get(d, d) for d in dims]

                fig = go.Figure(go.Scatterpolar(
                    r=vals + [vals[0]],
                    theta=labels + [labels[0]],
                    fill="toself",
                    fillcolor="rgba(245,158,11,0.2)",
                    line=dict(color="#f59e0b", width=2),
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    showlegend=False, height=380,
                    title="직업 가치관 프로파일",
                )
                st.plotly_chart(fig, use_container_width=True)

                top_vals = sorted(dims, key=lambda d: vl[d], reverse=True)[:3]
                st.markdown("**핵심 가치관 TOP 3:**")
                for d in top_vals:
                    st.markdown(f"- **{VALUES_LABELS.get(d, d)}** ({int(vl[d]*100)}점)")
            else:
                st.info("직업가치관 검사 데이터가 없습니다.")

        with col_a:
            if "anchors" in results:
                an = results["anchors"]
                dims = list(an.keys())
                vals = [an[d] * 100 for d in dims]
                labels = [ANCHOR_LABELS.get(d, d) for d in dims]

                fig = px.bar(
                    x=labels, y=vals,
                    color=vals,
                    color_continuous_scale=["#e8f5e9", "#22c55e", "#15803d"],
                    title="커리어 방향성 프로파일",
                )
                fig.update_layout(
                    height=380, coloraxis_showscale=False,
                    yaxis=dict(range=[0, 100]),
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                fig.update_traces(text=[f"{v:.0f}" for v in vals], textposition="outside")
                st.plotly_chart(fig, use_container_width=True)

                top_anchor = max(dims, key=lambda d: an[d])
                st.markdown(f"**주요 앵커: {ANCHOR_LABELS.get(top_anchor, top_anchor)}** ({int(an[top_anchor]*100)}점)")
            else:
                st.info("이 연령대에서는 Career Anchors 검사를 실시하지 않았습니다.")

    # ──────────────────────────────────
    # 탭 6: 성격 특성
    # ──────────────────────────────────
    with tabs[5]:
        if "big5" in results:
            b5 = results["big5"]
            dims = list(b5.keys())
            vals = [b5[d] * 100 for d in dims]
            labels = [BIG5_LABELS.get(d, d) for d in dims]

            fig = go.Figure(go.Bar(
                x=labels, y=vals,
                marker_color=["#667eea", "#764ba2", "#f59e0b", "#22c55e", "#ef4444"],
                text=[f"{v:.0f}" for v in vals], textposition="outside"
            ))
            fig.update_layout(
                height=320, yaxis=dict(range=[0, 100]),
                plot_bgcolor="rgba(0,0,0,0)",
                title="나의 성격 특성",
            )
            st.plotly_chart(fig, use_container_width=True)

            # 성격별 간단 설명
            big5_desc = {
                "O": ("개방성", "새로운 경험·아이디어에 열려 있는 정도"),
                "C": ("성실성", "계획적이고 책임감 있게 행동하는 정도"),
                "E": ("외향성", "사람들과 어울리고 활발하게 행동하는 정도"),
                "A": ("친화성", "타인을 배려하고 협력하는 정도"),
                "N": ("감정안정성", "스트레스 상황에서 안정적으로 대처하는 정도"),
            }
            top_traits = sorted(dims, key=lambda d: b5[d], reverse=True)[:3]
            st.markdown("**나의 강점 성격 TOP 3:**")
            for d in top_traits:
                label, desc = big5_desc.get(d, (d, ""))
                st.markdown(f"""
                <div style='background:#f8f9ff;border-radius:8px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;'>
                    <b>{label}</b> ({int(b5[d]*100)}점): {desc}
                </div>""", unsafe_allow_html=True)
        else:
            st.info("이 연령대에서는 성격 검사를 실시하지 않았습니다.")

    # ──────────────────────────────────
    # 탭 7: 진로 탐색 현황 (청소년 전용)
    # ──────────────────────────────────
    if has_maturity:
        with tabs[6]:
            from data.questions import MATURITY_LABELS
            mt = results["maturity"]
            total_score = results.get("maturity_total", 0)
            dims = list(mt.keys())
            vals = [mt[d] * 100 for d in dims]
            labels = [MATURITY_LABELS.get(d, d) for d in dims]

            # 성숙도 총점 해석
            if total_score >= 75:
                level, color, msg = "탐색 활성화", "#22c55e", "진로 탐색이 매우 활발합니다. 지금 수준을 유지하면서 깊이를 더해가세요."
            elif total_score >= 50:
                level, color, msg = "탐색 진행 중", "#f59e0b", "진로 탐색을 시작하고 있습니다. 더 다양한 직업을 알아보세요."
            else:
                level, color, msg = "탐색 초기 단계", "#ef4444", "아직 진로 탐색이 많이 이루어지지 않았습니다. 이 결과를 시작점으로 활용하세요."

            st.markdown(f"""
            <div style='background:#f8f9ff;border-radius:12px;padding:1rem 1.2rem;margin-bottom:1rem;
                 border-left:4px solid {color};'>
                <div style='font-size:1.5rem;font-weight:800;color:{color};'>{total_score:.0f}점 — {level}</div>
                <div style='color:#555;margin-top:0.3rem;'>{msg}</div>
            </div>
            """, unsafe_allow_html=True)

            fig = px.bar(
                x=labels, y=vals,
                color=vals,
                color_continuous_scale=["#fef3c7", "#f59e0b", "#d97706"],
                title="진로 탐색 현황 (영역별)",
            )
            fig.update_layout(
                height=300, coloraxis_showscale=False,
                yaxis=dict(range=[0, 100]),
                plot_bgcolor="rgba(0,0,0,0)",
            )
            fig.update_traces(text=[f"{v:.0f}" for v in vals], textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

            # 낮은 영역 개선 제안
            low_dims = sorted(dims, key=lambda d: mt[d])[:2]
            st.markdown("**지금 당장 할 수 있는 것:**")
            suggestions = {
                "자기이해": "좋아하는 활동 목록 작성 / 진로 관련 앱·온라인 검사 활용",
                "탐색행동": "관심 직업인 인터뷰 영상 시청 / 직업 체험 프로그램 참가",
                "직업세계이해": "고용24, 커리어넷에서 직업 정보 탐색",
                "의사결정": "직업 선택 기준(가치관) 목록 스스로 작성해보기",
                "진로계획": "5년 후 목표를 종이에 써보기",
            }
            for d in low_dims:
                label = MATURITY_LABELS.get(d, d)
                sug = suggestions.get(d, "")
                st.markdown(f"""
                <div style='background:#fff7ed;border-radius:8px;padding:0.5rem 0.8rem;
                     margin-bottom:0.4rem;border-left:3px solid #f59e0b;'>
                    <b>{label}</b> 강화 → {sug}
                </div>""", unsafe_allow_html=True)

    # ──────────────────────────────────
    # 결과 공유 / 저장
    # ──────────────────────────────────
    st.markdown("---")
    st.markdown(f"### {t('share_title', lang)}")
    share_col, dl_col = st.columns(2)
    with share_col:
        share_url = _generate_share_url(name, holland_code, ranked)
        st.text_input(t("share_link", lang), value=share_url, key="share_url_input")
    with dl_col:
        html_report = _generate_html_report(name, age_group, holland_code, results, ranked)
        st.download_button(
            label=t("download_btn", lang),
            data=html_report.encode("utf-8"),
            file_name=f"career_result_{name}.html",
            mime="text/html",
            use_container_width=True,
        )

    st.markdown("---")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button(t("retake_btn", lang), use_container_width=True):
            reset()
    with col_r2:
        if st.button(t("home_btn", lang), use_container_width=True):
            go_to("welcome")


# ────────────────────────────────────────────────
# 라우터
# ────────────────────────────────────────────────

def main():
    step = st.session_state.step
    lang = get_lang()

    # 사이드바: 언어 선택 + 결과 후 빠른 탐색
    with st.sidebar:
        _render_lang_selector()
        if step == "result":
            st.markdown("---")
            if st.session_state.ranked_careers:
                for i, fit in enumerate(st.session_state.ranked_careers[:5]):
                    cname = tc(fit["career_id"], lang) if lang != "ko" else fit["career_name"]
                    st.markdown(f"**{i+1}.** {cname} ({fit['score']:.0f})")
            if st.button(t("retake_btn", lang)):
                reset()

    if step == "welcome":
        render_welcome()
    elif step == "info":
        render_info()
    elif step == "survey":
        render_survey()
    elif step == "result":
        render_result()
    else:
        go_to("welcome")


if __name__ == "__main__":
    main()
