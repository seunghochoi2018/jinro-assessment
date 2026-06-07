import os
import sys
import json
import base64
from datetime import datetime

from flask import Flask, render_template, request, session, redirect, url_for, make_response
import plotly.graph_objects as go
import numpy as np
import pandas as pd

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.i18n import t, tq, tc, tcat, LANG_CONFIG, UI
from data.questions import (
    get_assessment_plan, get_age_group,
    HOLLAND_LABELS, MI_LABELS, BIG5_LABELS, VALUES_LABELS, ANCHOR_LABELS,
)
from engine.scorer import score_all_modules
from engine.matcher import rank_careers, get_career_fit_summary

# ────────────────────────────────────────────────
# Flask app setup
# ────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "jinro-secret-key-change-in-prod")
DEFAULT_LANG = "en"


@app.context_processor
def inject_globals():
    lang = session.get("lang", DEFAULT_LANG)
    return {
        "UI": UI,
        "LANG_CONFIG": LANG_CONFIG,
        "lang": lang,
        "t": lambda key: t(key, lang),
        "tc": lambda cid: tc(cid, lang),
        "tcat": lambda cat: tcat(cat, lang),
    }


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
# 차트 생성 헬퍼
# ────────────────────────────────────────────────

def _make_holland_chart(results: dict) -> str:
    h = results.get("holland", {})
    dims = ["R", "I", "A", "S", "E", "C"]
    vals = [h.get(d, 0.5) * 100 for d in dims]
    labels = ["실용·제작", "탐구·분석", "창작·표현", "사람·돕기", "리더·설득", "체계·관리"]
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=labels + [labels[0]],
        fill="toself",
        line_color="#667eea",
        fillcolor="rgba(102,126,234,0.2)",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 100])),
        margin=dict(l=20, r=20, t=30, b=20),
        height=300,
    )
    return fig.to_html(include_plotlyjs=False, full_html=False)


def _make_mi_chart(results: dict) -> str:
    mi = results.get("mi", {})
    dims = ["언어", "논리수학", "공간", "음악", "신체운동", "자연탐구", "대인관계", "자기이해"]
    vals = [mi.get(d, 0.5) * 100 for d in dims]
    fig = go.Figure(go.Bar(x=dims, y=vals, marker_color="#667eea"))
    fig.update_layout(
        yaxis_range=[0, 100],
        margin=dict(l=10, r=10, t=30, b=10),
        height=280,
    )
    return fig.to_html(include_plotlyjs=False, full_html=False)


def _make_big5_chart(results: dict) -> str:
    b5 = results.get("big5", {})
    dims = ["O", "C", "E", "A", "N"]
    labels = ["개방성", "성실성", "외향성", "친화성", "정서안정"]
    vals = [b5.get(d, 0.5) * 100 for d in dims]
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=labels + [labels[0]],
        fill="toself",
        line_color="#764ba2",
        fillcolor="rgba(118,75,162,0.2)",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 100])),
        margin=dict(l=20, r=20, t=30, b=20),
        height=300,
    )
    return fig.to_html(include_plotlyjs=False, full_html=False)


def _make_values_chart(results: dict) -> str:
    vl = results.get("values", {})
    dims = list(vl.keys())
    vals = [vl[d] * 100 for d in dims]
    fig = go.Figure(go.Bar(x=dims, y=vals, marker_color="#f59e0b"))
    fig.update_layout(
        yaxis_range=[0, 100],
        margin=dict(l=10, r=10, t=30, b=10),
        height=280,
    )
    return fig.to_html(include_plotlyjs=False, full_html=False)


# ────────────────────────────────────────────────
# 공유 URL 생성
# ────────────────────────────────────────────────

def _build_share_url(name: str, holland_code: str, ranked: list) -> str:
    share_data = {
        "n": name,
        "h": holland_code,
        "t": [(r["career_name"], round(r["score"])) for r in ranked[:5]],
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(share_data, ensure_ascii=False).encode()
    ).decode()
    base_url = os.environ.get("APP_URL", "https://jinro-assessment.onrender.com")
    return f"{base_url}/?r={encoded}"


def _decode_share_param(param: str) -> dict | None:
    try:
        decoded = base64.urlsafe_b64decode(param.encode()).decode()
        return json.loads(decoded)
    except Exception:
        return None


# ────────────────────────────────────────────────
# HTML 보고서 생성
# ────────────────────────────────────────────────

def _generate_html_report(name: str, age_group: str, holland_code: str,
                           results: dict, ranked: list) -> str:
    age_label = {"child": "아동", "teen": "청소년", "young_adult": "청년", "adult": "성인"}.get(age_group, "")

    top_careers_html = ""
    for i, fit in enumerate(ranked[:8]):
        c = fit["career_data"]
        diff = c.get("difficulty", "보통")
        diff_color = {
            "낮음": "#22c55e",
            "보통": "#3b82f6",
            "높음": "#f59e0b",
            "매우 높음": "#ef4444",
        }.get(diff, "#888")
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

    now_str = pd.Timestamp.now().strftime("%Y년 %m월 %d일")
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
생성일: {now_str} | 진로 탐색 시스템 (jinro-assessment.onrender.com)
</p>
</body></html>"""
    return html


# ────────────────────────────────────────────────
# 세션 plan 직렬화 헬퍼
# ────────────────────────────────────────────────

def _plan_to_session(plan: dict) -> dict:
    """get_assessment_plan 결과를 JSON 직렬화 가능한 형태로 변환."""
    sections = []
    for sec in plan.get("sections", []):
        questions = []
        for q in sec.get("questions", []):
            entry = {"id": q["id"], "dim": q["dim"]}
            if "reverse" in q:
                entry["reverse"] = q["reverse"]
            questions.append(entry)
        sections.append({
            "key": sec["key"],
            "title": sec["title"],
            "desc": sec.get("desc", ""),
            "questions": questions,
        })
    return {
        "label": plan.get("label", ""),
        "sections": sections,
        "weights": plan.get("weights", {}),
        "use_anchors": plan.get("use_anchors", False),
        "use_big5": plan.get("use_big5", False),
    }


def _build_profile_html(results: dict) -> str:
    """간단한 프로파일 HTML 생성 (나의 프로파일 탭)"""
    html = ""
    h = results.get("holland", {})
    mi = results.get("mi", {})
    vl = results.get("values", {})

    if h:
        h_labels = {"R":"실용·제작","I":"탐구·분석","A":"창작·표현","S":"사람·돕기","E":"리더·설득","C":"체계·관리"}
        top_h = sorted(h.keys(), key=lambda k: h[k], reverse=True)[:3]
        html += "<h4 style='margin-bottom:0.5rem;'>좋아하는 활동 유형 (Holland)</h4>"
        for k in top_h:
            pct = int(h[k]*100)
            html += f"<div style='margin-bottom:0.4rem;'><span style='display:inline-block;width:100px;font-weight:600;'>{h_labels.get(k,k)}</span>"
            html += f"<div style='display:inline-block;background:#e8e8e8;width:200px;height:10px;border-radius:5px;vertical-align:middle;'>"
            html += f"<div style='background:#667eea;width:{pct*2}px;height:10px;border-radius:5px;'></div></div>"
            html += f"<span style='margin-left:8px;font-size:0.85rem;'>{pct}</span></div>"

    if mi:
        top_mi = sorted(mi.keys(), key=lambda k: mi[k], reverse=True)[:3]
        html += "<hr style='margin:1rem 0;'><h4 style='margin-bottom:0.5rem;'>잘하는 능력 영역 (다중지능)</h4>"
        for k in top_mi:
            pct = int(mi[k]*100)
            html += f"<div style='margin-bottom:0.4rem;'><span style='display:inline-block;width:100px;font-weight:600;'>{k}</span>"
            html += f"<div style='display:inline-block;background:#e8e8e8;width:200px;height:10px;border-radius:5px;vertical-align:middle;'>"
            html += f"<div style='background:#764ba2;width:{pct*2}px;height:10px;border-radius:5px;'></div></div>"
            html += f"<span style='margin-left:8px;font-size:0.85rem;'>{pct}</span></div>"

    if vl:
        top_v = sorted(vl.keys(), key=lambda k: vl[k], reverse=True)[:3]
        html += "<hr style='margin:1rem 0;'><h4 style='margin-bottom:0.5rem;'>일에서 중요하게 여기는 가치</h4>"
        values_meaning = {
            "능력발휘":"내 능력을 최대한 쓸 수 있는 일","자율성":"스스로 결정하고 자유롭게 일하기",
            "보수":"경제적 보상이 중요한 동기","안정성":"오래 안정적으로 일하는 환경",
            "사회적인정":"사회에서 인정받는 일","사회봉사":"다른 사람에게 도움이 되는 일",
            "자기계발":"계속 배우고 성장하는 일","창의성":"창의적으로 새로운 것을 만드는 일",
            "대인관계":"좋은 사람들과 함께 일하기",
        }
        for i, k in enumerate(top_v, 1):
            html += f"<div style='background:#f8f9ff;border-radius:8px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;border-left:3px solid #f59e0b;'>"
            html += f"<span style='font-weight:800;color:#f59e0b;'>{i}순위</span> <strong>{k}</strong> — {values_meaning.get(k, k)}</div>"

    return html or "<p style='color:#888;'>프로파일 데이터가 없습니다.</p>"


def _compute_holland_code(holland_scores: dict) -> str:
    if not holland_scores:
        return "---"
    sorted_dims = sorted(holland_scores.items(), key=lambda x: x[1], reverse=True)
    return "".join(d for d, _ in sorted_dims[:3])


# ────────────────────────────────────────────────
# 라우트
# ────────────────────────────────────────────────

@app.route("/")
def index():
    lang = session.get("lang", DEFAULT_LANG)
    shared_data = None
    r_param = request.args.get("r")
    if r_param:
        shared_data = _decode_share_param(r_param)
    return render_template("welcome.html", lang=lang, LANG_CONFIG=LANG_CONFIG, shared_data=shared_data)


@app.route("/set-lang", methods=["POST"])
def set_lang():
    lang = request.form.get("lang", DEFAULT_LANG)
    if lang in LANG_CONFIG:
        session["lang"] = lang
    referrer = request.referrer or "/"
    return redirect(referrer)


@app.route("/info", methods=["GET", "POST"])
def info():
    lang = session.get("lang", DEFAULT_LANG)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age_str = request.form.get("age", "").strip()
        career_situation = request.form.get("career_situation", "")

        errors = []
        if not name:
            errors.append(t("name_label", lang) + " 필수 입력")

        age = None
        if age_str:
            try:
                age = int(age_str)
                if age < 6 or age > 100:
                    errors.append("나이는 6~100 사이여야 합니다.")
            except ValueError:
                errors.append("나이를 숫자로 입력해주세요.")
        else:
            errors.append(t("age_label", lang) + " 필수 입력")

        if errors:
            return render_template(
                "info.html",
                lang=lang,
                errors=errors,
                saved_name=name,
                saved_age=age_str,
                saved_situation=career_situation,
            )

        age_group = get_age_group(age)
        plan_raw = get_assessment_plan(age_group)
        plan = _plan_to_session(plan_raw)

        session["name"] = name
        session["age"] = age
        session["age_group"] = age_group
        session["plan"] = plan
        session["current_section"] = 0
        session["answers"] = {}
        session["career_situation"] = career_situation
        session.modified = True

        return redirect(url_for("survey"))

    # GET: show form with any previously saved values
    return render_template(
        "info.html",
        lang=lang,
        errors=[],
        saved_name=session.get("name", ""),
        saved_age=session.get("age", ""),
        saved_situation=session.get("career_situation", ""),
    )


@app.route("/survey", methods=["GET"])
def survey():
    if "plan" not in session:
        return redirect(url_for("index"))

    lang = session.get("lang", DEFAULT_LANG)
    plan = session["plan"]
    sections = plan["sections"]
    current_section_idx = session.get("current_section", 0)

    if current_section_idx >= len(sections):
        return redirect(url_for("result"))

    section = sections[current_section_idx]
    sec_key = section["key"]

    questions = [
        {
            "id": q["id"],
            "text": tq(q["id"], lang),
            "dim": q["dim"],
        }
        for q in section["questions"]
    ]

    # Restore previously saved answers for this section (for back-navigation)
    saved_answers = session.get("answers", {}).get(sec_key, {})

    is_forced_choice = sec_key in ("values", "anchors")
    pick_n = 3 if sec_key == "values" else 2

    return render_template(
        "survey.html",
        lang=lang,
        section_title=section["title"],
        section_desc=section.get("desc", ""),
        section_idx=current_section_idx,
        total_sections=len(sections),
        sec_key=sec_key,
        questions=questions,
        is_forced_choice=is_forced_choice,
        pick_n=pick_n,
        saved_answers=saved_answers,
        progress_pct=int(current_section_idx / len(sections) * 100),
    )


@app.route("/survey", methods=["POST"])
def survey_post():
    if "plan" not in session:
        return redirect(url_for("index"))

    lang = session.get("lang", DEFAULT_LANG)
    plan = session["plan"]
    sections = plan["sections"]
    current_section_idx = session.get("current_section", 0)

    if current_section_idx >= len(sections):
        return redirect(url_for("result"))

    section = sections[current_section_idx]
    sec_key = section["key"]

    answers = dict(session.get("answers", {}))

    forced_choice_keys = {"values", "anchors"}

    if sec_key in forced_choice_keys:
        # forced_choice: selected dims score 5, others score 1
        selected_dims = request.form.getlist("selected_dims")
        sec_answers = {}
        for q in section["questions"]:
            qid = q["id"]
            score = 5 if q["dim"] in selected_dims else 1
            sec_answers[qid] = score
    else:
        # Likert scale
        sec_answers = {}
        for q in section["questions"]:
            qid = q["id"]
            try:
                val = int(request.form.get(f"q_{qid}", 3))
                val = max(1, min(5, val))
            except (ValueError, TypeError):
                val = 3
            sec_answers[qid] = val

    answers[sec_key] = sec_answers
    session["answers"] = answers
    session["current_section"] = current_section_idx + 1
    session.modified = True

    next_idx = current_section_idx + 1
    if next_idx >= len(sections):
        # All sections done — compute results
        return _compute_and_store_results()

    return redirect(url_for("survey"))


def _compute_and_store_results():
    """Score + match, store in session, redirect to result."""
    plan = session["plan"]
    answers = session.get("answers", {})
    age_group = session.get("age_group", "young_adult")
    name = session.get("name", "")

    # Re-hydrate plan questions with reverse flag from original data for scorer
    # score_all_modules expects the raw section dicts with full question objects
    # We rebuild from stored plan (reverse flag was dropped for non-Big5)
    # The scorer reads 'reverse' key — it's safe if missing (defaults False)
    sections_for_scorer = plan["sections"]

    try:
        results = score_all_modules(answers, plan)
        ranked = rank_careers(results, age_group, top_n=12)
    except Exception as e:
        session["result_error"] = str(e)
        session.modified = True
        return redirect(url_for("result"))

    holland_scores = results.get("holland", {})
    holland_code = _compute_holland_code(holland_scores)
    share_url = _build_share_url(name, holland_code, ranked)

    session["results"] = results
    session["ranked"] = [
        {
            "career_id": r.get("career_id", ""),
            "career_name": r.get("career_name", ""),
            "score": r.get("score", 0),
            "confidence_lo": r.get("confidence_lo", 0),
            "confidence_hi": r.get("confidence_hi", 0),
            "career_data": r.get("career_data", {}),
            "top_reasons": r.get("top_reasons", []),
            "module_scores": r.get("module_scores", {}),
        }
        for r in ranked
    ]
    session["holland_code"] = holland_code
    session["share_url"] = share_url
    session.modified = True

    return redirect(url_for("result"))


@app.route("/result")
def result():
    if "results" not in session and "result_error" not in session:
        return redirect(url_for("index"))

    lang = session.get("lang", DEFAULT_LANG)
    error = session.get("result_error")
    if error:
        return render_template("result.html", lang=lang, error=error)

    results = session["results"]
    ranked = session.get("ranked", [])
    name = session.get("name", "")
    age_group = session.get("age_group", "young_adult")
    holland_code = session.get("holland_code", "---")
    share_url = session.get("share_url", "")

    # Build charts (only if data present)
    holland_chart = _make_holland_chart(results) if results.get("holland") else None
    mi_chart = _make_mi_chart(results) if results.get("mi") else None
    big5_chart = _make_big5_chart(results) if results.get("big5") else None
    values_chart = _make_values_chart(results) if results.get("values") else None

    # Enrich ranked with CAREER_DETAIL_DB salary info
    for fit in ranked:
        cid = fit["career_data"].get("id", "")
        detail = CAREER_DETAIL_DB.get(cid, {})
        fit["salary_range"] = detail.get("salary_range", fit["career_data"].get("salary_level", ""))
        fit["career_path"] = detail.get("career_path", [])

    top_career = ranked[0] if ranked else None
    top1_name = top_career["career_name"] if top_career else "-"
    top1_score = round(top_career["score"]) if top_career else 0
    categories = sorted(set(r["career_data"].get("category", "") for r in ranked if r["career_data"]))
    has_maturity = "maturity" in results
    profile_html = _build_profile_html(results)

    return render_template(
        "result.html",
        lang=lang,
        error=None,
        name=name,
        age_group=age_group,
        holland_code=holland_code,
        top1_name=top1_name,
        top1_score=top1_score,
        share_url=share_url,
        results=results,
        ranked=ranked,
        categories=categories,
        has_maturity=has_maturity,
        profile_html=profile_html,
        career_situation=session.get("career_situation", ""),
        holland_chart=holland_chart,
        mi_chart=mi_chart,
        big5_chart=big5_chart,
        values_chart=values_chart,
        career_detail_db=CAREER_DETAIL_DB,
    )


@app.route("/survey-back", methods=["POST"])
def survey_back():
    session["current_section"] = max(0, session.get("current_section", 1) - 1)
    session.modified = True
    return redirect(url_for("survey"))


@app.route("/reset", methods=["POST"])
def reset():
    session.clear()
    return redirect(url_for("index"))


@app.route("/download-report")
def download_report():
    if "results" not in session:
        return redirect(url_for("index"))

    name = session.get("name", "익명")
    age_group = session.get("age_group", "young_adult")
    holland_code = session.get("holland_code", "---")
    results = session["results"]
    ranked = session.get("ranked", [])

    html_content = _generate_html_report(name, age_group, holland_code, results, ranked)

    response = make_response(html_content)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    safe_name = name.replace(" ", "_")
    response.headers["Content-Disposition"] = f'attachment; filename="{safe_name}_진로탐색결과.html"'
    return response


# ────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
