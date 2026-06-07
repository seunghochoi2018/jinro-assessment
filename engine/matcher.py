# ────────────────────────────────────────────────────────────────────────
# 직업 매칭 엔진 - Career Fit Score with Confidence Band
#
# 독창적 요소:
#   - 다차원 가중 유사도 (Holland + MI + Values + Big5 + Anchors)
#   - 적응형 가중치 (RCS 기반 동적 조정)
#   - 신뢰구간 있는 추천 (점수 ± 불확실성)
#   - Why-Score 분해 (어떤 차원이 매칭을 이끌었는지)
#   - 연령대별 발달 적합도 보정
# ────────────────────────────────────────────────────────────────────────

import numpy as np
from data.careers import CAREERS_DB
from engine.scorer import (
    HOLLAND_DIMS, MI_DIMS, BIG5_DIMS, VALUES_DIMS, ANCHOR_DIMS
)

AGE_GROUP_IDX = {"child": 0, "teen": 1, "young_adult": 2, "adult": 3}


def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """코사인 유사도 [0, 1]"""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.5
    sim = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
    # [-1, 1] → [0, 1]
    return (sim + 1.0) / 2.0


def _dimension_match(user_scores: dict, career_profile: dict, dims: list) -> tuple[float, dict]:
    """
    사용자 프로파일과 직업 프로파일의 차원별 매치 점수 계산
    반환: (전체 유사도, {dim: 기여도})
    """
    u_vec = np.array([user_scores.get(d, 0.5) for d in dims])
    c_vec = np.array([career_profile.get(d, 0.5) for d in dims])

    # 전체 코사인 유사도
    overall = _cosine_similarity(u_vec, c_vec)

    # 차원별 기여도 (얼마나 각 차원이 매칭에 기여했는가)
    contrib = {}
    total_c = sum(c_vec) + 1e-9
    for i, d in enumerate(dims):
        # 기여도 = 사용자 점수 × 직업 요구도 (정규화)
        alignment = 1.0 - abs(u_vec[i] - c_vec[i])  # 0~1, 가까울수록 1
        weight = c_vec[i] / total_c
        contrib[d] = float(alignment * weight)

    return overall, contrib


def compute_career_fit(
    user_results: dict,
    career: dict,
    adaptive_weights: dict,
    age_group: str,
) -> dict:
    """
    단일 직업에 대한 전체 적합도 계산

    반환:
      score: 종합 적합도 (0~1)
      confidence: 불확실성 (낮을수록 확실)
      breakdown: 이론별 점수 분해
      top_reasons: 추천 이유 상위 3개
    """
    module_scores = {}
    breakdown = {}

    # ── Holland
    if "holland" in user_results and "holland" in career:
        sim, contrib = _dimension_match(
            user_results["holland"], career["holland"], HOLLAND_DIMS
        )
        module_scores["holland"] = sim
        breakdown["holland"] = {"score": sim, "contrib": contrib}

    # ── 다중지능
    if "mi" in user_results and "mi" in career:
        sim, contrib = _dimension_match(
            user_results["mi"], career["mi"], MI_DIMS
        )
        module_scores["mi"] = sim
        breakdown["mi"] = {"score": sim, "contrib": contrib}

    # ── Big Five
    if "big5" in user_results and "big5" in career:
        sim, contrib = _dimension_match(
            user_results["big5"], career["big5"], BIG5_DIMS
        )
        module_scores["big5"] = sim
        breakdown["big5"] = {"score": sim, "contrib": contrib}

    # ── 가치관
    if "values" in user_results and "values" in career:
        sim, contrib = _dimension_match(
            user_results["values"], career["values"], VALUES_DIMS
        )
        module_scores["values"] = sim
        breakdown["values"] = {"score": sim, "contrib": contrib}

    # ── Career Anchors
    if "anchors" in user_results and "anchors" in career:
        sim, contrib = _dimension_match(
            user_results["anchors"], career["anchors"], ANCHOR_DIMS
        )
        module_scores["anchors"] = sim
        breakdown["anchors"] = {"score": sim, "contrib": contrib}

    # ── 적응형 가중 앙상블 점수
    weighted_sum = 0.0
    weight_total = 0.0
    for mod, w in adaptive_weights.items():
        if mod in module_scores:
            weighted_sum += module_scores[mod] * w
            weight_total += w

    base_score = weighted_sum / weight_total if weight_total > 0 else 0.5

    # ── 연령 발달 적합도 보정 (Super의 발달이론 적용)
    # age_fit=1.0 → 패널티 없음 / age_fit=0.0 → 50% 감소 (강한 억제)
    age_idx = AGE_GROUP_IDX.get(age_group, 2)
    age_fit = career.get("age_fit", [0.5, 0.7, 1.0, 0.9])[age_idx]
    age_penalty = 0.5 + 0.5 * age_fit
    final_score = base_score * age_penalty

    # ── 불확실성 (Confidence Band)
    # 각 모듈 점수의 분산이 클수록 불확실성 증가
    scores_list = list(module_scores.values())
    score_std = float(np.std(scores_list)) if len(scores_list) > 1 else 0.0
    rcs_avg = np.mean(list(user_results.get("rcs_per_module", {1.0: 1.0}).values()))
    ctci = user_results.get("ctci", 0.7)
    # 불확실성 = 모듈 간 불일치 + 내적 일관성 부족 + CTCI 낮음
    uncertainty = (score_std * 0.5 + (1 - rcs_avg) * 0.3 + (1 - ctci) * 0.2) * 0.15

    # ── 추천 이유 도출 (Why-Score)
    top_reasons = _extract_top_reasons(breakdown, user_results, career, adaptive_weights)

    return {
        "career_id": career["id"],
        "career_name": career["name"],
        "category": career["category"],
        "score": round(final_score * 100, 1),      # 0~100점
        "confidence_lo": round(max(0, (final_score - uncertainty) * 100), 1),
        "confidence_hi": round(min(100, (final_score + uncertainty) * 100), 1),
        "uncertainty": round(uncertainty * 100, 1),
        "breakdown": breakdown,
        "module_scores": {k: round(v * 100, 1) for k, v in module_scores.items()},
        "top_reasons": top_reasons,
        "career_data": career,
    }


def _extract_top_reasons(
    breakdown: dict,
    user_results: dict,
    career: dict,
    adaptive_weights: dict,
) -> list[dict]:
    """
    매칭 이유 상위 요인 추출
    각 이론별 핵심 기여 차원을 텍스트로 변환
    """
    from data.questions import (
        HOLLAND_LABELS, HOLLAND_DESC,
        MI_LABELS, MI_DESC,
        BIG5_LABELS, VALUES_LABELS, ANCHOR_LABELS
    )

    reasons = []

    # Holland 이유
    if "holland" in breakdown:
        h_contrib = breakdown["holland"]["contrib"]
        h_score = breakdown["holland"]["score"]
        if h_score > 0.55:
            top_dims = sorted(h_contrib.keys(), key=lambda k: h_contrib[k], reverse=True)[:2]
            for dim in top_dims:
                user_val = user_results.get("holland", {}).get(dim, 0.5)
                career_val = career.get("holland", {}).get(dim, 0.5)
                if user_val > 0.55 and career_val > 0.5:
                    label = HOLLAND_LABELS.get(dim, dim)
                    reasons.append({
                        "theory": "직업 흥미",
                        "detail": f"{label} 성향이 강하게 일치합니다.",
                        "strength": h_contrib[dim],
                        "icon": "흥미",
                    })

    # 다중지능 이유
    if "mi" in breakdown:
        mi_contrib = breakdown["mi"]["contrib"]
        mi_score = breakdown["mi"]["score"]
        if mi_score > 0.55:
            top_dims = sorted(mi_contrib.keys(), key=lambda k: mi_contrib[k], reverse=True)[:2]
            for dim in top_dims:
                user_val = user_results.get("mi", {}).get(dim, 0.5)
                career_val = career.get("mi", {}).get(dim, 0.5)
                if user_val > 0.55 and career_val > 0.5:
                    label = MI_LABELS.get(dim, dim)
                    reasons.append({
                        "theory": "강점 지능",
                        "detail": f"{label}이 이 직업에서 핵심 역량입니다.",
                        "strength": mi_contrib[dim],
                        "icon": "지능",
                    })

    # 가치관 이유
    if "values" in breakdown:
        v_contrib = breakdown["values"]["contrib"]
        v_score = breakdown["values"]["score"]
        if v_score > 0.55:
            top_dims = sorted(v_contrib.keys(), key=lambda k: v_contrib[k], reverse=True)[:2]
            for dim in top_dims:
                user_val = user_results.get("values", {}).get(dim, 0.5)
                career_val = career.get("values", {}).get(dim, 0.5)
                if user_val > 0.55 and career_val > 0.5:
                    label = VALUES_LABELS.get(dim, dim)
                    reasons.append({
                        "theory": "직업 가치관",
                        "detail": f"중시하는 '{label}' 가치가 이 직업과 잘 맞습니다.",
                        "strength": v_contrib[dim],
                        "icon": "가치관",
                    })

    # Big5 이유
    if "big5" in breakdown:
        b5_contrib = breakdown["big5"]["contrib"]
        b5_score = breakdown["big5"]["score"]
        if b5_score > 0.55:
            top_dims = sorted(b5_contrib.keys(), key=lambda k: b5_contrib[k], reverse=True)[:1]
            for dim in top_dims:
                user_val = user_results.get("big5", {}).get(dim, 0.5)
                career_val = career.get("big5", {}).get(dim, 0.5)
                if user_val > 0.55 and career_val > 0.5:
                    label = BIG5_LABELS.get(dim, dim)
                    reasons.append({
                        "theory": "성격 특성",
                        "detail": f"'{label}'이 높아 이 직업에 유리합니다.",
                        "strength": b5_contrib[dim],
                        "icon": "성격",
                    })

    # Anchors 이유
    if "anchors" in breakdown:
        a_contrib = breakdown["anchors"]["contrib"]
        a_score = breakdown["anchors"]["score"]
        if a_score > 0.55:
            top_dims = sorted(a_contrib.keys(), key=lambda k: a_contrib[k], reverse=True)[:1]
            for dim in top_dims:
                user_val = user_results.get("anchors", {}).get(dim, 0.5)
                career_val = career.get("anchors", {}).get(dim, 0.5)
                if user_val > 0.55 and career_val > 0.5:
                    label = ANCHOR_LABELS.get(dim, dim)
                    reasons.append({
                        "theory": "커리어 앵커",
                        "detail": f"'{label}' 앵커가 이 직업의 핵심 방향과 일치합니다.",
                        "strength": a_contrib[dim],
                        "icon": "앵커",
                    })

    # 강도 순 정렬 후 상위 3개
    reasons.sort(key=lambda x: x["strength"], reverse=True)
    return reasons[:3]


# ────────────────────────────────────────────────
# 전체 직업 매칭 + 랭킹
# ────────────────────────────────────────────────

def rank_careers(user_results: dict, age_group: str, top_n: int = 12) -> list[dict]:
    """
    모든 직업에 대해 적합도를 계산하고 상위 top_n개 반환
    user_results: score_all_modules()의 반환값
    """
    adaptive_weights = user_results.get("adaptive_weights", {})
    if not adaptive_weights:
        # 폴백: 균등 가중치
        adaptive_weights = {k: 1.0 for k in user_results.keys()
                            if k in ("holland", "mi", "big5", "values", "anchors")}
        total = max(sum(adaptive_weights.values()), 1)
        adaptive_weights = {k: v / total for k, v in adaptive_weights.items()}

    fits = []
    for career in CAREERS_DB:
        fit = compute_career_fit(user_results, career, adaptive_weights, age_group)
        fits.append(fit)

    fits.sort(key=lambda x: x["score"], reverse=True)
    return fits[:top_n]


def get_career_fit_summary(fit: dict) -> str:
    """적합도 수준 텍스트"""
    score = fit["score"]
    if score >= 80:
        return "매우 높음"
    elif score >= 65:
        return "높음"
    elif score >= 50:
        return "보통"
    else:
        return "낮음"
