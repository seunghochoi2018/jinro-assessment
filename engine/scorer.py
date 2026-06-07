# ────────────────────────────────────────────────────────────────────────
# Multi-Theory Ensemble Career Assessment (MTECA) - 점수 계산 엔진
#
# 독창적 요소 (특허 가능성):
#   1. Response Consistency Score (RCS) : 각 이론 내 응답 내적 일관성 측정
#   2. Cross-Theory Congruence Index (CTCI) : 복수 이론 간 프로파일 일치도
#   3. Adaptive Ensemble Weights : RCS·CTCI 기반 동적 가중치 재조정
#   4. Confidence Band : 각 직업 추천에 불확실성 구간 부여
#
# 참고 이론 (이론 프레임워크만 사용, 상용 검사지 문항 미사용):
#   Holland (1997) - RIASEC Occupational Theory
#   Gardner (1983) - Theory of Multiple Intelligences
#   Costa & McCrae (1992) - Five-Factor Model of Personality
#   Schein (1978, 1990) - Career Anchors Theory
#   Super (1957, 1990) - Life-Span, Life-Space Approach
# ────────────────────────────────────────────────────────────────────────

import numpy as np
from typing import Any


# ────────────────────────────────────────────────
# 상수
# ────────────────────────────────────────────────
LIKERT_MAX = 5.0
LIKERT_MIN = 1.0
NORM_RANGE = LIKERT_MAX - LIKERT_MIN  # 4.0

# Holland 차원 순서 (벡터화용)
HOLLAND_DIMS = ["R", "I", "A", "S", "E", "C"]
# 다중지능 차원
MI_DIMS = ["언어", "논리수학", "공간", "음악", "신체운동", "자연탐구", "대인관계", "자기이해"]
# Big Five (N은 역채점 후 감정안정성)
BIG5_DIMS = ["O", "C", "E", "A", "N"]
# 직업가치관
VALUES_DIMS = ["능력발휘", "자율성", "보수", "안정성", "사회적인정", "사회봉사", "자기계발", "창의성", "대인관계"]
# Career Anchors
ANCHOR_DIMS = ["전문역량", "관리역량", "자율독립", "안전안정", "기업가창의", "봉사헌신", "순수도전", "라이프스타일"]
MATURITY_DIMS = ["자기이해", "탐색행동", "직업세계이해", "의사결정", "진로계획"]


# ────────────────────────────────────────────────
# 1. 원시 응답 → 차원별 정규화 점수
# ────────────────────────────────────────────────

def normalize_score(raw: float, reverse: bool = False) -> float:
    """5점 리커트 원점수 → [0, 1] 정규화 (역채점 포함)"""
    if reverse:
        raw = LIKERT_MAX + LIKERT_MIN - raw
    return (raw - LIKERT_MIN) / NORM_RANGE


def compute_dimension_scores(answers: dict, questions: list, target_dims: list) -> dict:
    """
    answers: {question_id: raw_score (1-5)}
    questions: 해당 모듈의 문항 리스트
    target_dims: 집계할 차원 목록
    반환: {dim: 정규화 평균 점수 (0~1)}
    """
    dim_scores: dict = {d: [] for d in target_dims}
    for q in questions:
        qid = q["id"]
        if qid not in answers:
            continue
        raw = float(answers[qid])
        reverse = q.get("reverse", False)
        normalized = normalize_score(raw, reverse)
        dim = q["dim"]
        if dim in dim_scores:
            dim_scores[dim].append(normalized)

    return {d: float(np.mean(v)) if v else 0.5 for d, v in dim_scores.items()}


# ────────────────────────────────────────────────
# 2. Response Consistency Score (RCS) - 독창적 지표
#    같은 차원 내 응답 분산이 낮을수록 일관성 높음
#    RCS = 1 - (차원내 분산의 평균) / (최대 가능 분산)
# ────────────────────────────────────────────────

def compute_rcs(answers: dict, questions: list, target_dims: list) -> dict:
    """
    각 차원별 내적 일관성 점수 (0~1, 높을수록 일관된 응답)
    최대 분산 기준: 1점과 5점만 섞어 응답 시 분산 = 4.0
    """
    dim_vals: dict = {d: [] for d in target_dims}
    for q in questions:
        qid = q["id"]
        if qid not in answers:
            continue
        dim = q["dim"]
        if dim in dim_vals:
            dim_vals[dim].append(float(answers[qid]))

    rcs = {}
    for d, vals in dim_vals.items():
        if len(vals) < 2:
            rcs[d] = 1.0  # 문항 1개면 분산 측정 불가, 기본값
        else:
            variance = float(np.var(vals))
            max_variance = 4.0  # ((5-1)/2)^2 * 4 approximation
            rcs[d] = max(0.0, 1.0 - (variance / max_variance))
    return rcs


# ────────────────────────────────────────────────
# 3. Cross-Theory Congruence Index (CTCI) - 독창적 지표
#    복수 이론 간 프로파일이 얼마나 일치하는지 측정
#    - Holland-Big5 일치도: 이론적으로 I형은 개방성(O)↑ 예측 등
#    - Holland-Values 일치도: S형은 사회봉사↑ 예측 등
#    CTCI 높음 → 자기 이해가 명확, 추천 신뢰도 높음
#    CTCI 낮음 → 정체성 탐색 중, 더 많은 탐색 필요
# ────────────────────────────────────────────────

# Holland-Big5 이론적 매핑 (Holland 1997, Barrick et al. 2003 참고)
HOLLAND_BIG5_MAPPING = {
    "R": {"C": 0.4, "O": -0.3},   # 현실형: 성실↑, 개방↓
    "I": {"O": 0.6, "E": -0.3},   # 탐구형: 개방↑, 외향↓
    "A": {"O": 0.7, "C": -0.2},   # 예술형: 개방↑↑, 성실↓
    "S": {"A": 0.5, "E": 0.3},    # 사회형: 친화↑, 외향↑
    "E": {"E": 0.6, "A": -0.2},   # 진취형: 외향↑, 친화↓
    "C": {"C": 0.6, "N": 0.2},    # 관습형: 성실↑, 안정성 중립
}

# Holland-Values 이론적 매핑
HOLLAND_VALUES_MAPPING = {
    "R": {"능력발휘": 0.6, "안정성": 0.4},
    "I": {"능력발휘": 0.7, "자기계발": 0.7, "자율성": 0.5},
    "A": {"창의성": 0.9, "자율성": 0.7, "자기계발": 0.5},
    "S": {"사회봉사": 0.8, "대인관계": 0.6, "사회적인정": 0.4},
    "E": {"사회적인정": 0.7, "보수": 0.5, "능력발휘": 0.6},
    "C": {"안정성": 0.7, "보수": 0.5},
}


def compute_ctci(
    holland_scores: dict,
    values_scores: dict | None = None,
    big5_scores: dict | None = None,
) -> float:
    """
    Cross-Theory Congruence Index: 0~1 (높을수록 이론 간 프로파일 일치)
    각 이론 쌍의 예측 방향성과 실제 응답 방향성 상관도로 계산
    """
    agreements = []

    # Holland-Values 일치도
    if values_scores:
        for h_dim, v_map in HOLLAND_VALUES_MAPPING.items():
            h_score = holland_scores.get(h_dim, 0.5)
            for v_dim, expected_dir in v_map.items():
                v_score = values_scores.get(v_dim, 0.5)
                # h_score 높으면 v_score도 높아야 한다 (양의 기대 관계)
                # 방향 일치 여부 측정
                h_dev = h_score - 0.5  # 중앙 기준 편차
                v_dev = v_score - 0.5
                expected_sign = 1 if expected_dir > 0 else -1
                actual_sign = 1 if (h_dev * v_dev) >= 0 else -1
                # 일치도 = 방향 일치 여부 * 강도 기반 가중치
                agreement = expected_sign * actual_sign * abs(expected_dir)
                agreements.append(agreement)

    # Holland-Big5 일치도
    if big5_scores:
        for h_dim, b5_map in HOLLAND_BIG5_MAPPING.items():
            h_score = holland_scores.get(h_dim, 0.5)
            for b5_dim, expected_dir in b5_map.items():
                b5_score = big5_scores.get(b5_dim, 0.5)
                h_dev = h_score - 0.5
                b5_dev = b5_score - 0.5
                expected_sign = 1 if expected_dir > 0 else -1
                actual_sign = 1 if (h_dev * b5_dev) >= 0 else -1
                agreement = expected_sign * actual_sign * abs(expected_dir)
                agreements.append(agreement)

    if not agreements:
        return 0.5  # 단일 이론만 사용 시 중립값

    raw_ctci = float(np.mean(agreements))
    # [-1, 1] → [0, 1] 정규화
    return (raw_ctci + 1.0) / 2.0


# ────────────────────────────────────────────────
# 4. Adaptive Ensemble Weights - 독창적 요소
#    기본 가중치 × RCS 보정 → 정규화
# ────────────────────────────────────────────────

def compute_adaptive_weights(
    base_weights: dict,
    rcs_per_module: dict,
) -> dict:
    """
    base_weights: {'holland': 0.3, 'mi': 0.25, ...}
    rcs_per_module: {'holland': 0.85, 'mi': 0.70, ...}
    반환: RCS 보정 후 재정규화된 가중치
    """
    adjusted = {}
    for module, base_w in base_weights.items():
        rcs_avg = rcs_per_module.get(module, 1.0)
        # 일관성이 낮은 모듈은 가중치 감소 (0.5 이하 RCS는 50%까지 감소)
        consistency_factor = 0.5 + 0.5 * rcs_avg
        adjusted[module] = base_w * consistency_factor

    total = sum(adjusted.values())
    if total == 0:
        return base_weights
    return {k: v / total for k, v in adjusted.items()}


# ────────────────────────────────────────────────
# 5. 전체 채점 파이프라인
# ────────────────────────────────────────────────

def score_all_modules(session_answers: dict, assessment_plan: dict) -> dict:
    """
    session_answers: {'holland': {qid: score, ...}, 'big5': {...}, ...}
    assessment_plan: get_assessment_plan()의 반환값
    반환: 전체 점수 딕셔너리
    """
    # HOLLAND_DIMS 등은 이 모듈 상단에 이미 정의되어 있음

    results = {}
    rcs_per_module = {}

    for section in assessment_plan["sections"]:
        key = section["key"]
        answers = session_answers.get(key, {})
        questions = section["questions"]

        if key == "holland":
            dims = HOLLAND_DIMS
            scores = compute_dimension_scores(answers, questions, dims)
            rcs = compute_rcs(answers, questions, dims)
            results["holland"] = scores
            rcs_per_module["holland"] = float(np.mean(list(rcs.values())))

        elif key == "holland_child":
            dims = HOLLAND_DIMS
            scores = compute_dimension_scores(answers, questions, dims)
            rcs = compute_rcs(answers, questions, dims)
            results["holland"] = scores
            rcs_per_module["holland"] = float(np.mean(list(rcs.values())))

        elif key == "mi":
            dims = MI_DIMS
            scores = compute_dimension_scores(answers, questions, dims)
            rcs = compute_rcs(answers, questions, dims)
            results["mi"] = scores
            rcs_per_module["mi"] = float(np.mean(list(rcs.values())))

        elif key == "big5":
            dims = BIG5_DIMS
            scores = compute_dimension_scores(answers, questions, dims)
            rcs = compute_rcs(answers, questions, dims)
            results["big5"] = scores
            rcs_per_module["big5"] = float(np.mean(list(rcs.values())))

        elif key == "values":
            dims = VALUES_DIMS
            scores = compute_dimension_scores(answers, questions, dims)
            rcs = compute_rcs(answers, questions, dims)
            results["values"] = scores
            rcs_per_module["values"] = float(np.mean(list(rcs.values())))

        elif key == "anchors":
            dims = ANCHOR_DIMS
            scores = compute_dimension_scores(answers, questions, dims)
            rcs = compute_rcs(answers, questions, dims)
            results["anchors"] = scores
            rcs_per_module["anchors"] = float(np.mean(list(rcs.values())))

        elif key == "maturity":
            dims = MATURITY_DIMS
            scores = compute_dimension_scores(answers, questions, dims)
            rcs = compute_rcs(answers, questions, dims)
            results["maturity"] = scores
            rcs_per_module["maturity"] = float(np.mean(list(rcs.values())))
            # 진로성숙도 총점 (0~100) - 직업 매칭 가중치가 아닌 별도 해석용
            results["maturity_total"] = round(float(np.mean(list(scores.values()))) * 100, 1)

    # CTCI 계산
    ctci = compute_ctci(
        holland_scores=results.get("holland", {}),
        values_scores=results.get("values"),
        big5_scores=results.get("big5"),
    )
    results["ctci"] = ctci
    results["rcs_per_module"] = rcs_per_module

    # 적응형 가중치 계산
    base_weights = assessment_plan["weights"].copy()
    adaptive_weights = compute_adaptive_weights(base_weights, rcs_per_module)
    results["adaptive_weights"] = adaptive_weights

    # Holland 유형 코드 (상위 3개)
    if "holland" in results:
        h = results["holland"]
        top3 = sorted(h.keys(), key=lambda k: h[k], reverse=True)[:3]
        results["holland_code"] = "".join(top3)

    return results


# ────────────────────────────────────────────────
# 6. 프로파일 해석 텍스트 생성
# ────────────────────────────────────────────────

def get_ctci_interpretation(ctci: float) -> dict:
    """CTCI 값에 따른 해석"""
    if ctci >= 0.70:
        return {
            "level": "높음",
            "color": "green",
            "desc": "자기 이해도가 높고 응답이 여러 이론에서 일관됩니다. 추천 결과의 신뢰도가 높습니다.",
        }
    elif ctci >= 0.50:
        return {
            "level": "보통",
            "color": "orange",
            "desc": "전반적으로 일관성이 있지만 일부 영역에서 탐색 중인 부분이 있습니다.",
        }
    else:
        return {
            "level": "낮음",
            "color": "red",
            "desc": "아직 진로 정체성을 탐색하는 중입니다. 다양한 경험을 통해 자신을 더 알아가는 것이 좋습니다.",
        }


def get_rcs_interpretation(rcs_avg: float) -> str:
    if rcs_avg >= 0.75:
        return "응답이 매우 일관되어 신뢰할 수 있는 결과입니다."
    elif rcs_avg >= 0.50:
        return "응답이 대체로 일관됩니다."
    else:
        return "일부 응답에 일관성이 부족합니다. 천천히 다시 생각해보시는 것을 권장합니다."
