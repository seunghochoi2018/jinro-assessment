# ────────────────────────────────────────────────────────────────────────
# Multi-Theory Ensemble Career Assessment (MTECA) - 개인화 인사이트 생성기
#
# 순수 rule-based 텍스트 생성: Holland + Big5 + Values 조합
# 외부 API 없음, 순수 Python
# ────────────────────────────────────────────────────────────────────────

from __future__ import annotations

# ────────────────────────────────────────────────
# Holland 2-letter 조합 프로파일
# key: top1+top2 Holland code (e.g. "RI")
# ────────────────────────────────────────────────

HOLLAND_PROFILES: dict[str, dict] = {
    # ── R 시작
    "RI": {
        "en": {
            "label": "Analytical Builder",
            "desc": "A hands-on problem solver who combines technical precision with intellectual curiosity. You thrive when turning abstract ideas into concrete, working systems.",
        },
        "ko": {
            "label": "분석적 제작자",
            "desc": "지적 호기심과 실제 제작 능력을 함께 갖춘 문제 해결사입니다. 아이디어를 실제 작동하는 시스템으로 만들 때 진가를 발휘합니다.",
        },
        "zh": {
            "label": "分析型建造者",
            "desc": "将技术精准与智识好奇心融为一体的实践型问题解决者。你在将抽象概念转化为具体可运行系统时最为出色。",
        },
    },
    "RA": {
        "en": {
            "label": "Craftsman Creator",
            "desc": "A maker at heart who blends technical skill with artistic sensibility. You produce work that is both functionally sound and aesthetically considered.",
        },
        "ko": {
            "label": "장인형 창작자",
            "desc": "기술적 역량과 예술적 감각을 동시에 가진 진정한 제작자입니다. 기능적으로 완성도 높고 미적으로도 섬세한 결과물을 만들어냅니다.",
        },
        "zh": {
            "label": "工匠型创作者",
            "desc": "将技术技能与艺术感知融合的天生创作者。你的作品兼具功能性与美学价值。",
        },
    },
    "RS": {
        "en": {
            "label": "Practical Helper",
            "desc": "A grounded individual who connects physical competence with genuine care for others. You are most fulfilled when your skills directly improve someone's daily life.",
        },
        "ko": {
            "label": "실용적 조력자",
            "desc": "현실적 역량과 타인에 대한 진심 어린 관심을 함께 갖춘 사람입니다. 자신의 기술이 누군가의 일상에 직접적으로 도움이 될 때 가장 큰 보람을 느낍니다.",
        },
        "zh": {
            "label": "务实助人者",
            "desc": "将实际能力与真诚关爱融合的踏实人。当你的技能直接改善他人生活时，你感到最大的成就感。",
        },
    },
    "RC": {
        "en": {
            "label": "Systematic Craftsman",
            "desc": "A precise, reliable, and detail-focused builder who excels within clear structures. You deliver consistent quality by combining practical expertise with disciplined process.",
        },
        "ko": {
            "label": "체계적 장인",
            "desc": "명확한 구조 안에서 빛을 발하는 정밀하고 신뢰할 수 있는 전문가입니다. 실용적 전문성과 철저한 프로세스를 결합해 일관된 품질을 만들어냅니다.",
        },
        "zh": {
            "label": "系统化工匠",
            "desc": "在清晰结构中表现卓越的精准可靠专家。通过将实践专长与严格流程相结合，持续产出高质量成果。",
        },
    },
    # ── I 시작
    "IA": {
        "en": {
            "label": "Creative Analyst",
            "desc": "A rare blend of deep intellectual curiosity and artistic vision. You approach problems not just analytically but imaginatively, finding solutions others miss.",
        },
        "ko": {
            "label": "창의적 분석가",
            "desc": "깊은 지적 호기심과 예술적 비전이 공존하는 보기 드문 유형입니다. 문제를 분석적으로뿐만 아니라 상상력으로 접근해 다른 사람들이 놓치는 해법을 찾아냅니다.",
        },
        "zh": {
            "label": "创意分析师",
            "desc": "深邃智识好奇心与艺术视野的罕见融合体。你不仅从分析角度，更以想象力来解决问题，发现他人遗漏的方案。",
        },
    },
    "IS": {
        "en": {
            "label": "Empathetic Researcher",
            "desc": "A thinker who combines deep analytical rigor with genuine care for people. You are drawn to understanding the human dimension behind data, systems, and ideas.",
        },
        "ko": {
            "label": "공감하는 연구자",
            "desc": "깊은 분석적 사고와 사람에 대한 진정한 관심을 함께 갖춘 탐구자입니다. 데이터와 시스템, 아이디어 뒤에 있는 인간적 측면을 이해하고자 하는 욕구가 강합니다.",
        },
        "zh": {
            "label": "共情型研究者",
            "desc": "将深度分析思维与真诚关怀人的特质融合的探究者。你致力于理解数据、系统和思想背后的人文维度。",
        },
    },
    "IE": {
        "en": {
            "label": "Visionary Thinker",
            "desc": "An intellectual with persuasive power who turns complex ideas into compelling arguments. You combine depth of analysis with the drive to influence and lead.",
        },
        "ko": {
            "label": "비전 있는 사상가",
            "desc": "복잡한 아이디어를 설득력 있는 주장으로 바꾸는 지적 리더입니다. 깊이 있는 분석력과 영향력을 발휘하려는 추진력을 함께 갖추고 있습니다.",
        },
        "zh": {
            "label": "有远见的思想家",
            "desc": "将复杂思想转化为有说服力论点的智识型领袖。你兼具深度分析力与影响他人的驱动力。",
        },
    },
    "IC": {
        "en": {
            "label": "Precise Investigator",
            "desc": "A methodical thinker who combines intellectual depth with structured, systematic execution. You are at your best when rigorous research meets organized workflow.",
        },
        "ko": {
            "label": "정밀한 탐구자",
            "desc": "지적 깊이와 체계적 실행을 결합한 방법론적 사고자입니다. 엄격한 연구가 조직화된 업무 흐름을 만날 때 최고의 성과를 냅니다.",
        },
        "zh": {
            "label": "精准探究者",
            "desc": "将智识深度与系统化执行相结合的方法论思考者。当严格研究遇到有序工作流程时，你表现最佳。",
        },
    },
    # ── A 시작
    "AS": {
        "en": {
            "label": "Creative Connector",
            "desc": "An artist who deeply understands people. You use creative expression as a bridge to human connection, making your work resonate far beyond aesthetics alone.",
        },
        "ko": {
            "label": "창의적 연결자",
            "desc": "사람을 깊이 이해하는 예술가입니다. 창의적 표현을 인간 연결의 다리로 활용해, 미적 아름다움을 넘어 사람들의 마음에 깊이 닿는 작업을 만들어냅니다.",
        },
        "zh": {
            "label": "创意连接者",
            "desc": "深刻理解人心的艺术家。你将创意表达作为连接人心的桥梁，使你的作品远超纯粹美学层面，直抵人心。",
        },
    },
    "AE": {
        "en": {
            "label": "Persuasive Creator",
            "desc": "A charismatic communicator with creative flair. You draw people in with originality, then move them with energy and conviction. Born for roles that blend storytelling with leadership.",
        },
        "ko": {
            "label": "설득력 있는 창작자",
            "desc": "창의적 재능과 카리스마를 겸비한 커뮤니케이터입니다. 독창성으로 사람들의 시선을 끌고, 에너지와 확신으로 그들을 움직입니다. 스토리텔링과 리더십이 결합된 역할에 최적화된 유형입니다.",
        },
        "zh": {
            "label": "有说服力的创作者",
            "desc": "兼具创意才华与个人魅力的沟通者。你以独创性吸引他人，再以能量与信念打动他们。天生适合融合叙事与领导力的角色。",
        },
    },
    "AI": {
        "en": {
            "label": "Imaginative Scholar",
            "desc": "A deep thinker who pairs intellectual rigor with creative vision. You are drawn to ideas at the frontier of knowledge and art, synthesizing them into something genuinely new.",
        },
        "ko": {
            "label": "상상력 있는 학자",
            "desc": "지적 엄격함과 창의적 비전을 결합한 깊은 사고자입니다. 지식과 예술의 경계에 있는 아이디어에 이끌리며, 이를 종합해 진정으로 새로운 무언가를 만들어냅니다.",
        },
        "zh": {
            "label": "富有想象力的学者",
            "desc": "将智识严谨与创意视野相结合的深刻思考者。你被知识与艺术边界的思想所吸引，将其综合成真正新颖的事物。",
        },
    },
    # ── S 시작
    "SE": {
        "en": {
            "label": "People Leader",
            "desc": "A natural relationship builder with genuine leadership drive. You inspire others not through authority alone but through authentic connection and a clear sense of purpose.",
        },
        "ko": {
            "label": "사람 중심 리더",
            "desc": "타고난 관계 형성 능력과 진정한 리더십 추진력을 갖춘 사람입니다. 권위만이 아니라 진정성 있는 연결과 명확한 목적의식으로 다른 사람들에게 영감을 줍니다.",
        },
        "zh": {
            "label": "以人为本的领袖",
            "desc": "天生的关系建立者，拥有真诚的领导驱动力。你不仅凭借权威，更通过真实的连接与清晰的使命感来激励他人。",
        },
    },
    "SI": {
        "en": {
            "label": "Empathetic Researcher",
            "desc": "A helper who thinks deeply. You bring intellectual rigor to human-centered work, combining data-driven insight with heartfelt concern for people's wellbeing.",
        },
        "ko": {
            "label": "공감하는 연구자",
            "desc": "깊이 생각하는 조력자입니다. 사람 중심 일에 지적 엄격함을 더해, 데이터 기반 통찰과 사람들의 안녕에 대한 진심 어린 관심을 결합합니다.",
        },
        "zh": {
            "label": "共情型研究者",
            "desc": "深刻思考的助人者。你为以人为本的工作带来智识严谨性，将数据驱动的洞察与对人们福祉的真诚关怀相结合。",
        },
    },
    "SA": {
        "en": {
            "label": "Expressive Helper",
            "desc": "A warm, creative soul who uses artistic expression in service of others. You make difficult topics accessible through storytelling, imagery, and genuine human warmth.",
        },
        "ko": {
            "label": "표현하는 조력자",
            "desc": "예술적 표현을 타인을 위해 활용하는 따뜻하고 창의적인 사람입니다. 스토리텔링, 이미지, 진정한 인간적 온기로 어려운 주제를 친근하게 만들어냅니다.",
        },
        "zh": {
            "label": "表达型助人者",
            "desc": "以艺术表达服务他人的温暖创意灵魂。你通过叙事、意象与真诚的人情味，让困难的话题变得易于理解。",
        },
    },
    "SC": {
        "en": {
            "label": "Dependable Caregiver",
            "desc": "A structured, reliable person who provides steady support to others. You create safety and trust through consistency, making you invaluable in roles that require both compassion and precision.",
        },
        "ko": {
            "label": "믿음직한 돌봄자",
            "desc": "체계적이고 신뢰할 수 있으며 타인에게 안정적인 지원을 제공하는 사람입니다. 일관성을 통해 안정감과 신뢰를 형성하며, 공감과 정밀함이 모두 필요한 역할에서 없어서는 안 될 존재입니다.",
        },
        "zh": {
            "label": "可靠型照护者",
            "desc": "为他人提供稳定支持的结构化可靠之人。你通过一致性建立安全感与信任，在需要兼具同理心与精确性的角色中不可或缺。",
        },
    },
    # ── E 시작
    "EC": {
        "en": {
            "label": "Strategic Organizer",
            "desc": "An entrepreneurial visionary who executes with systematic discipline. You see the big picture clearly and build the structures needed to make ambitious goals a reality.",
        },
        "ko": {
            "label": "전략적 조직자",
            "desc": "체계적 규율로 실행하는 기업가적 비전을 가진 사람입니다. 큰 그림을 명확히 보고, 야망 있는 목표를 현실로 만들기 위한 구조를 구축합니다.",
        },
        "zh": {
            "label": "战略型组织者",
            "desc": "以系统纪律执行的创业型远见者。你清晰地看到宏观全局，并构建将宏大目标转化为现实所需的结构。",
        },
    },
    "ES": {
        "en": {
            "label": "Inspiring Leader",
            "desc": "A leader who genuinely cares about the people they lead. You motivate through empathy as much as through vision, creating environments where others grow alongside you.",
        },
        "ko": {
            "label": "영감을 주는 리더",
            "desc": "이끄는 사람들을 진심으로 아끼는 리더입니다. 비전만큼 공감으로도 동기를 부여하며, 다른 사람들이 함께 성장할 수 있는 환경을 만들어냅니다.",
        },
        "zh": {
            "label": "激励型领袖",
            "desc": "真诚关心所领导之人的领袖。你用同理心与远见激励他人，创造让他人与你共同成长的环境。",
        },
    },
    "EA": {
        "en": {
            "label": "Charismatic Innovator",
            "desc": "A bold communicator with a creative edge. You make ideas come alive through compelling delivery and original thinking, naturally drawing people toward your vision.",
        },
        "ko": {
            "label": "카리스마 있는 혁신가",
            "desc": "창의적 감각을 가진 대담한 커뮤니케이터입니다. 설득력 있는 전달과 독창적 사고로 아이디어에 생명을 불어넣어, 자연스럽게 사람들을 자신의 비전으로 이끕니다.",
        },
        "zh": {
            "label": "魅力型创新者",
            "desc": "具有创意优势的大胆沟通者。你通过有说服力的表达和原创性思维让想法栩栩如生，自然地吸引他人认同你的愿景。",
        },
    },
    "EI": {
        "en": {
            "label": "Strategic Thinker",
            "desc": "An analytically minded leader who bases bold decisions on deep reasoning. You are most effective when you combine intellectual firepower with the confidence to act.",
        },
        "ko": {
            "label": "전략적 사고자",
            "desc": "깊은 추론에 기반해 대담한 결정을 내리는 분석적 리더입니다. 지적 역량과 행동하는 자신감을 결합할 때 가장 큰 효과를 발휘합니다.",
        },
        "zh": {
            "label": "战略型思考者",
            "desc": "以深度推理为基础做出大胆决策的分析型领袖。当你将智识火力与行动自信相结合时，效果最为显著。",
        },
    },
    # ── C 시작
    "CI": {
        "en": {
            "label": "Methodical Expert",
            "desc": "A structured thinker who grounds intellectual rigor in systematic practice. You are a trusted authority because your conclusions are always traceable, repeatable, and precise.",
        },
        "ko": {
            "label": "방법론적 전문가",
            "desc": "지적 엄격함을 체계적 실천에 기반시키는 구조적 사고자입니다. 결론이 항상 추적 가능하고, 재현 가능하며, 정밀하기 때문에 신뢰받는 권위자입니다.",
        },
        "zh": {
            "label": "方法论型专家",
            "desc": "将智识严谨性植根于系统实践的结构化思考者。你之所以是值得信赖的权威，是因为你的结论始终可追溯、可重复且精确。",
        },
    },
    "CE": {
        "en": {
            "label": "Operational Leader",
            "desc": "A results-driven organizer with leadership instincts. You excel at building efficient systems that scale, and you are not afraid to take command when direction is needed.",
        },
        "ko": {
            "label": "운영 리더",
            "desc": "리더십 본능을 가진 결과 지향적 조직자입니다. 확장 가능한 효율적인 시스템 구축에 탁월하며, 방향이 필요할 때 지휘를 맡는 것을 두려워하지 않습니다.",
        },
        "zh": {
            "label": "运营型领袖",
            "desc": "具有领导本能的结果导向型组织者。你擅长构建可扩展的高效系统，在需要方向时毫不畏惧地承担领导职责。",
        },
    },
}

# 프로파일이 정의되지 않은 조합의 폴백 생성
def _get_profile(top1: str, top2: str, lang: str) -> dict:
    """2-letter combo 프로파일 조회, 없으면 역순 또는 폴백 반환"""
    key = top1 + top2
    rev = top2 + top1
    profile = HOLLAND_PROFILES.get(key) or HOLLAND_PROFILES.get(rev)
    if profile:
        return profile.get(lang, profile.get("en", {}))
    # 폴백: 각 단일 코드 설명 기반 생성
    _single_labels = {
        "R": {"en": "Practical Doer", "ko": "실용적 실행가", "zh": "务实实践者"},
        "I": {"en": "Curious Thinker", "ko": "호기심 있는 사색가", "zh": "好奇思考者"},
        "A": {"en": "Creative Spirit", "ko": "창의적 영혼", "zh": "创意灵魂"},
        "S": {"en": "Caring Helper", "ko": "배려하는 조력자", "zh": "关怀助人者"},
        "E": {"en": "Driven Leader", "ko": "추진력 있는 리더", "zh": "进取型领袖"},
        "C": {"en": "Organized Specialist", "ko": "체계적 전문가", "zh": "有序专家"},
    }
    lbl1 = _single_labels.get(top1, {}).get(lang, top1)
    lbl2 = _single_labels.get(top2, {}).get(lang, top2)
    fallback_labels = {"en": f"{lbl1} & {lbl2}", "ko": f"{lbl1} & {lbl2}", "zh": f"{lbl1} & {lbl2}"}
    fallback_desc = {
        "en": f"A unique blend of {lbl1.lower()} and {lbl2.lower()} qualities that positions you for versatile, cross-disciplinary success.",
        "ko": f"{lbl1}와 {lbl2}의 독특한 조합으로, 다양한 분야를 가로지르는 성공에 최적화된 유형입니다.",
        "zh": f"融合{lbl1}与{lbl2}特质的独特组合，使你在跨学科领域中游刃有余。",
    }
    return {"label": fallback_labels.get(lang, lbl1), "desc": fallback_desc.get(lang, "")}


# ────────────────────────────────────────────────
# Big5 수식어
# ────────────────────────────────────────────────

_BIG5_MODIFIERS: dict[str, dict[str, dict]] = {
    "O_high": {
        "en": "strong intellectual and creative curiosity",
        "ko": "강한 지적·창의적 호기심",
        "zh": "强烈的智识与创意好奇心",
    },
    "C_high": {
        "en": "exceptional goal-driven discipline",
        "ko": "뛰어난 목표 지향적 자기 관리",
        "zh": "出色的目标导向自律性",
    },
    "E_high": {
        "en": "natural energy from social interaction",
        "ko": "사회적 교류에서 얻는 타고난 활력",
        "zh": "从社交互动中获得天然活力",
    },
    "A_high": {
        "en": "deep collaborative empathy",
        "ko": "깊은 협력적 공감 능력",
        "zh": "深度协作共情能力",
    },
    "N_low": {
        "en": "remarkable emotional resilience under pressure",
        "ko": "압박 상황에서 뛰어난 감정적 회복력",
        "zh": "在压力下出色的情绪韧性",
    },
}

def _get_big5_modifiers(big5: dict, lang: str) -> list[str]:
    mods = []
    if big5.get("O", 0.5) > 0.65:
        mods.append(_BIG5_MODIFIERS["O_high"][lang])
    if big5.get("C", 0.5) > 0.65:
        mods.append(_BIG5_MODIFIERS["C_high"][lang])
    if big5.get("E", 0.5) > 0.65:
        mods.append(_BIG5_MODIFIERS["E_high"][lang])
    if big5.get("A", 0.5) > 0.65:
        mods.append(_BIG5_MODIFIERS["A_high"][lang])
    if big5.get("N", 0.5) < 0.40:
        mods.append(_BIG5_MODIFIERS["N_low"][lang])
    return mods


# ────────────────────────────────────────────────
# Values 레이블
# ────────────────────────────────────────────────

_VALUES_LABELS: dict[str, dict[str, str]] = {
    "능력발휘": {"en": "using your full abilities", "ko": "능력 발휘", "zh": "充分发挥才能"},
    "자율성":   {"en": "autonomy and self-direction", "ko": "자율성", "zh": "自主性"},
    "보수":     {"en": "financial reward", "ko": "경제적 보상", "zh": "经济回报"},
    "안정성":   {"en": "job security", "ko": "안정성", "zh": "工作稳定"},
    "사회적인정": {"en": "social recognition", "ko": "사회적 인정", "zh": "社会认可"},
    "사회봉사": {"en": "contributing to society", "ko": "사회 봉사", "zh": "社会贡献"},
    "자기계발": {"en": "continuous self-development", "ko": "자기계발", "zh": "持续自我成长"},
    "창의성":   {"en": "creative expression", "ko": "창의성", "zh": "创意表达"},
    "대인관계": {"en": "meaningful relationships at work", "ko": "직장 내 의미 있는 관계", "zh": "工作中有意义的人际关系"},
}


# ────────────────────────────────────────────────
# Big5 차원 풀 레이블 (강점 추출용)
# ────────────────────────────────────────────────

_BIG5_STRENGTH_LABELS: dict[str, dict[str, str]] = {
    "O": {"en": "Openness & creative thinking", "ko": "개방성과 창의적 사고", "zh": "开放性与创造性思维"},
    "C": {"en": "Conscientiousness & follow-through", "ko": "성실성과 실행력", "zh": "尽责性与执行力"},
    "E": {"en": "Extraversion & social energy", "ko": "외향성과 사회적 에너지", "zh": "外向性与社交能量"},
    "A": {"en": "Agreeableness & teamwork", "ko": "친화성과 협업 능력", "zh": "宜人性与团队协作"},
    "N": {"en": "Emotional stability under pressure", "ko": "압박 속 감정적 안정성", "zh": "压力下的情绪稳定性"},
}

_HOLLAND_STRENGTH_LABELS: dict[str, dict[str, str]] = {
    "R": {"en": "Hands-on technical ability", "ko": "실기 기술 능력", "zh": "动手技术能力"},
    "I": {"en": "Analytical & research aptitude", "ko": "분석·연구 적성", "zh": "分析与研究能力"},
    "A": {"en": "Creative & expressive talent", "ko": "창의적 표현 재능", "zh": "创意表达天赋"},
    "S": {"en": "Interpersonal & coaching ability", "ko": "대인 관계 및 코칭 능력", "zh": "人际与辅导能力"},
    "E": {"en": "Leadership & persuasive communication", "ko": "리더십과 설득 소통", "zh": "领导力与说服沟通"},
    "C": {"en": "Organized, detail-oriented execution", "ko": "체계적이고 꼼꼼한 실행력", "zh": "有序且注重细节的执行力"},
}

_VALUES_STRENGTH_LABELS: dict[str, dict[str, str]] = {
    "능력발휘": {"en": "Drive to maximize your potential", "ko": "잠재력을 극대화하려는 추진력", "zh": "最大化潜力的驱动力"},
    "자율성":   {"en": "Self-directed work style", "ko": "자기 주도적 업무 방식", "zh": "自主导向的工作风格"},
    "보수":     {"en": "Results-oriented motivation", "ko": "결과 중심적 동기", "zh": "成果导向的动力"},
    "안정성":   {"en": "Reliability and long-term commitment", "ko": "신뢰성과 장기적 헌신", "zh": "可靠性与长期承诺"},
    "사회적인정": {"en": "Motivation through meaningful impact", "ko": "의미 있는 영향을 통한 동기", "zh": "通过有意义的影响激励自己"},
    "사회봉사": {"en": "Purpose-driven work ethic", "ko": "목적 중심적 직업 윤리", "zh": "目标驱动的职业道德"},
    "자기계발": {"en": "Growth mindset and lifelong learning", "ko": "성장 마인드셋과 평생 학습", "zh": "成长型思维与终身学习"},
    "창의성":   {"en": "Innovation and original thinking", "ko": "혁신과 독창적 사고", "zh": "创新与原创思维"},
    "대인관계": {"en": "Collaborative, team-first approach", "ko": "협력적이고 팀 우선적 접근", "zh": "协作、以团队为先的方式"},
}


# ────────────────────────────────────────────────
# Watch-out (맹점) 정의
# ────────────────────────────────────────────────

_WATCH_OUT: dict = {
    # Holland 저점 기반
    "R": {
        "en": "You may sometimes underestimate the value of hands-on, practical experience — push yourself to test ideas in the real world, not just on paper.",
        "ko": "실제 경험의 가치를 간과하는 경향이 있을 수 있습니다. 아이디어를 종이 위에서만이 아니라 현실에서 직접 검증해보는 시도가 필요합니다.",
        "zh": "你有时可能低估实践经验的价值——推动自己在现实中验证想法，而不仅仅停留在纸面上。",
    },
    "I": {
        "en": "A tendency toward over-analysis can slow decision-making. Practice trusting your instincts alongside your evidence.",
        "ko": "과도한 분석 경향이 의사결정을 늦출 수 있습니다. 증거뿐만 아니라 직관도 함께 신뢰하는 연습이 필요합니다.",
        "zh": "过度分析的倾向可能拖慢决策。练习在依据证据的同时也信任你的直觉。",
    },
    "A": {
        "en": "High creative standards can make it hard to ship imperfect work. Remember: done and useful often beats perfect and delayed.",
        "ko": "높은 창의적 기준이 불완전한 결과물을 내보내기 어렵게 만들 수 있습니다. 완벽하지만 늦은 것보다 완성되어 유용한 것이 더 낫다는 점을 기억하세요.",
        "zh": "高创意标准可能让你难以发布不完美的作品。记住：完成且有用往往胜过完美但延迟。",
    },
    "S": {
        "en": "A strong orientation toward helping others can sometimes lead to neglecting your own needs and boundaries. Invest in yourself too.",
        "ko": "타인 돕기에 강하게 초점이 맞춰지면 자신의 필요와 경계를 소홀히 할 수 있습니다. 자신에게도 투자하는 것을 잊지 마세요.",
        "zh": "强烈的助人导向有时会导致忽视自身需求和边界。也要记得投资自己。",
    },
    "E": {
        "en": "A drive for action and results can sometimes outpace careful listening. Slowing down to fully understand others strengthens your leadership.",
        "ko": "행동과 결과에 대한 추진력이 세심한 경청을 앞서갈 수 있습니다. 타인을 완전히 이해하기 위해 속도를 늦추는 것이 리더십을 강화합니다.",
        "zh": "对行动和成果的驱动有时会超过仔细倾听。放慢脚步充分理解他人，能强化你的领导力。",
    },
    "C": {
        "en": "Comfort with structure may limit appetite for ambiguity and change. Deliberately seek out situations where the rules are not yet written.",
        "ko": "구조에 대한 편안함이 모호함과 변화에 대한 수용도를 낮출 수 있습니다. 규칙이 아직 정해지지 않은 상황을 의도적으로 찾아보세요.",
        "zh": "对结构的偏好可能限制对模糊性和变化的接受度。主动寻找规则尚未确立的情境。",
    },
    # Big5 저점 기반 (Holland 저점이 없을 때 사용)
    "O_low": {
        "en": "Trying approaches outside your usual methods could unlock unexpected value. Experiment more, even when it feels uncomfortable.",
        "ko": "평소 방식 밖의 접근법을 시도하면 예상치 못한 가치를 발견할 수 있습니다. 불편하게 느껴지더라도 더 많이 실험해보세요.",
        "zh": "尝试日常方法之外的途径可能带来意想不到的价值。多做实验，即使感到不舒适。",
    },
    "C_low": {
        "en": "Big ideas need follow-through to have impact. Investing in planning habits and accountability systems will help turn vision into reality.",
        "ko": "큰 아이디어가 영향력을 가지려면 실행이 뒤따라야 합니다. 계획 습관과 책임 시스템에 투자하면 비전을 현실로 만드는 데 도움이 됩니다.",
        "zh": "宏大的想法需要持续跟进才能产生影响。投资于计划习惯和问责系统将帮助你将愿景转化为现实。",
    },
    "E_low": {
        "en": "Valuable ideas sometimes stay invisible because they aren't communicated with enough energy. Seek low-pressure ways to build your visibility.",
        "ko": "가치 있는 아이디어가 충분한 에너지로 전달되지 않으면 보이지 않는 채로 남을 수 있습니다. 낮은 부담감으로 존재감을 키울 수 있는 방법을 찾아보세요.",
        "zh": "有价值的想法有时因传递能量不足而无人知晓。寻找低压力的方式来提升你的可见度。",
    },
    "A_low": {
        "en": "A direct, results-focused style can sometimes feel abrasive in collaborative settings. Pausing to consider others' perspectives builds stronger alliances.",
        "ko": "직접적이고 결과 중심적인 스타일이 협력 환경에서 거칠게 느껴질 수 있습니다. 타인의 관점을 고려하기 위해 잠시 멈추면 더 강한 동맹 관계를 구축할 수 있습니다.",
        "zh": "直接、结果导向的风格在协作环境中有时会显得生硬。停下来考虑他人的观点，有助于建立更牢固的联盟。",
    },
}


def _get_watch_out(holland: dict, big5: dict, lang: str) -> str:
    """가장 낮은 Holland 차원 또는 Big5 차원에 기반한 맹점 반환"""
    # Holland에서 가장 낮은 차원 (상위 2개 제외)
    sorted_h = sorted(holland.items(), key=lambda x: x[1])
    for dim, score in sorted_h:
        if score < 0.45 and dim in _WATCH_OUT:
            return _WATCH_OUT[dim][lang]

    # Big5에서 낮은 차원
    if big5.get("O", 0.5) < 0.40:
        return _WATCH_OUT["O_low"][lang]
    if big5.get("C", 0.5) < 0.40:
        return _WATCH_OUT["C_low"][lang]
    if big5.get("E", 0.5) < 0.40:
        return _WATCH_OUT["E_low"][lang]
    if big5.get("A", 0.5) < 0.40:
        return _WATCH_OUT["A_low"][lang]

    # 폴백: Holland 최저점
    if sorted_h:
        lowest_dim = sorted_h[0][0]
        if lowest_dim in _WATCH_OUT:
            return _WATCH_OUT[lowest_dim][lang]

    _default = {
        "en": "Be mindful of over-focusing on your strongest areas at the expense of skills that don't come naturally.",
        "ko": "자연스럽게 잘 되지 않는 기술을 희생하면서 가장 강한 영역에만 과도하게 집중하지 않도록 주의하세요.",
        "zh": "注意不要过度专注于最擅长的领域，而牺牲那些不自然的技能。",
    }
    return _default[lang]


# ────────────────────────────────────────────────
# 강점 추출 (Holland + Big5 + Values 통합)
# ────────────────────────────────────────────────

def _get_strengths(holland: dict, big5: dict, values: dict, lang: str) -> list[str]:
    """상위 점수 차원들에서 3개의 핵심 강점 추출"""
    candidates: list[tuple[float, str]] = []

    # Holland 상위
    for dim, score in holland.items():
        if dim in _HOLLAND_STRENGTH_LABELS:
            candidates.append((score, _HOLLAND_STRENGTH_LABELS[dim][lang]))

    # Big5 상위 (0.65 초과만)
    for dim, score in big5.items():
        if score > 0.65 and dim in _BIG5_STRENGTH_LABELS:
            candidates.append((score, _BIG5_STRENGTH_LABELS[dim][lang]))
        elif dim == "N" and score < 0.40:
            # N 역채점: 낮을수록 안정적
            candidates.append((1.0 - score, _BIG5_STRENGTH_LABELS["N"][lang]))

    # Values 상위
    if values:
        for dim, score in values.items():
            if score > 0.65 and dim in _VALUES_STRENGTH_LABELS:
                candidates.append((score * 0.9, _VALUES_STRENGTH_LABELS[dim][lang]))  # 약간 낮게 가중

    # 점수 기준 정렬 후 중복 텍스트 제거
    candidates.sort(key=lambda x: x[0], reverse=True)
    seen: set[str] = set()
    result: list[str] = []
    for _, label in candidates:
        if label not in seen:
            seen.add(label)
            result.append(label)
        if len(result) == 3:
            break

    # 3개 미만이면 Holland 상위 코드로 채우기
    if len(result) < 3:
        for dim in sorted(holland, key=lambda k: holland[k], reverse=True):
            lbl = _HOLLAND_STRENGTH_LABELS.get(dim, {}).get(lang, dim)
            if lbl not in seen:
                seen.add(lbl)
                result.append(lbl)
            if len(result) == 3:
                break

    return result


# ────────────────────────────────────────────────
# Values-기반 커리어 적합 이유
# ────────────────────────────────────────────────

_CAREER_FIT_TEMPLATES: dict[str, dict[str, str]] = {
    "en": (
        "The careers recommended for you align with your drive for {v1} and {v2}. "
        "Combined with your {h_label} personality, these roles give you the right environment "
        "to operate at your best — where your natural strengths meet meaningful work."
    ),
    "ko": (
        "추천된 직업들은 {v1}과(와) {v2}에 대한 당신의 욕구와 잘 맞습니다. "
        "{h_label} 성향과 결합되어, 이 직업들은 당신이 최고의 역량을 발휘할 수 있는 "
        "환경을 제공합니다 — 타고난 강점이 의미 있는 일과 만나는 곳에서."
    ),
    "zh": (
        "推荐给你的职业与你对{v1}和{v2}的追求高度契合。"
        "结合你的{h_label}特质，这些职业为你提供了发挥最佳状态的合适环境——"
        "在你的天然优势与有意义的工作相遇之处。"
    ),
}

def _get_career_fit_reason(
    top_holland: list[str],
    top_values: list[str],
    profile_label: str,
    lang: str,
) -> str:
    v_labels = [_VALUES_LABELS.get(v, {}).get(lang, v) for v in top_values[:2]]
    v1 = v_labels[0] if len(v_labels) > 0 else ("ability" if lang == "en" else "능력 발휘" if lang == "ko" else "能力发挥")
    v2 = v_labels[1] if len(v_labels) > 1 else ("growth" if lang == "en" else "성장" if lang == "ko" else "成长")
    template = _CAREER_FIT_TEMPLATES[lang]
    return template.format(v1=v1, v2=v2, h_label=profile_label)


# ────────────────────────────────────────────────
# 요약 문장 생성
# ────────────────────────────────────────────────

def _build_summary(
    profile_desc: str,
    big5_mods: list[str],
    top_values: list[str],
    lang: str,
) -> str:
    """2-3 문장 개인화 요약 생성"""
    v_labels = [_VALUES_LABELS.get(v, {}).get(lang, v) for v in top_values[:2]]

    if lang == "en":
        base = profile_desc
        if big5_mods:
            mod_str = " and ".join(big5_mods[:2])
            base += f" You bring {mod_str} to everything you do."
        if v_labels:
            v_str = " and ".join(v_labels[:2])
            base += f" At your core, you are motivated by {v_str} — look for roles that honor both."
        return base

    elif lang == "ko":
        base = profile_desc
        if big5_mods:
            mod_str = ", ".join(big5_mods[:2])
            base += f" 모든 일에서 {mod_str}을(를) 발휘합니다."
        if v_labels:
            v_str = "과(와) ".join(v_labels[:2])
            base += f" 당신의 핵심 동기는 {v_str}입니다. 이 두 가지를 모두 충족하는 역할을 찾으세요."
        return base

    elif lang == "zh":
        base = profile_desc
        if big5_mods:
            mod_str = "与".join(big5_mods[:2])
            base += f" 你在所有事情上都展现出{mod_str}。"
        if v_labels:
            v_str = "和".join(v_labels[:2])
            base += f" 你的核心动力是{v_str}——寻找能同时满足这两者的角色。"
        return base

    return profile_desc


# ────────────────────────────────────────────────
# 메인 공개 함수
# ────────────────────────────────────────────────

def generate_insight(results: dict, lang: str = "en") -> dict:
    """
    결과 딕셔너리(score_all_modules 반환값 또는 호환 구조)를 받아
    개인화된 커리어 인사이트 텍스트를 생성합니다.

    Parameters
    ----------
    results : dict
        score_all_modules()의 반환값.
        최소 "holland" 키가 필요하며, "big5" / "values" 는 선택.
    lang : str
        "en" | "ko" | "zh"

    Returns
    -------
    dict with keys:
        headline        : str  (1 문장, 굵게 표시할 성격 유형 레이블)
        summary         : str  (2-3 문장 개인화 분석)
        strengths       : list[str]  (3개 핵심 강점)
        watch_out       : str  (1개 잠재적 맹점)
        career_fit_reason : str  (상위 직업이 적합한 이유)
    """
    if lang not in ("en", "ko", "zh"):
        lang = "en"

    # ── 데이터 추출 (없으면 중립값 사용)
    holland: dict = results.get("holland", {})
    big5: dict = results.get("big5", {})
    values: dict = results.get("values", {})

    # Holland 상위 2 차원
    sorted_h = sorted(holland.items(), key=lambda x: x[1], reverse=True)
    top1 = sorted_h[0][0] if len(sorted_h) > 0 else "I"
    top2 = sorted_h[1][0] if len(sorted_h) > 1 else "S"

    # Big5 (없으면 중립 0.5)
    b5 = {d: big5.get(d, 0.5) for d in ("O", "C", "E", "A", "N")}

    # Values 상위 2개
    sorted_v = sorted(values.items(), key=lambda x: x[1], reverse=True) if values else []
    top_values = [k for k, _ in sorted_v[:2]]

    # ── 프로파일 조회
    profile = _get_profile(top1, top2, lang)
    profile_label: str = profile.get("label", f"{top1}{top2}")
    profile_desc: str = profile.get("desc", "")

    # ── Big5 수식어
    big5_mods = _get_big5_modifiers(b5, lang)

    # ── 강점 목록
    strengths = _get_strengths(holland, b5, values, lang)

    # ── 맹점
    watch_out = _get_watch_out(holland, b5, lang)

    # ── 커리어 적합 이유
    career_fit_reason = _get_career_fit_reason(
        top_holland=[top1, top2],
        top_values=top_values,
        profile_label=profile_label,
        lang=lang,
    )

    # ── 요약
    summary = _build_summary(profile_desc, big5_mods, top_values, lang)

    # ── 헤드라인
    _headline_templates = {
        "en": f"You are a {profile_label}.",
        "ko": f"당신은 {profile_label}입니다.",
        "zh": f"你是一位{profile_label}。",
    }
    headline = _headline_templates.get(lang, f"{profile_label}")

    return {
        "headline": headline,
        "summary": summary,
        "strengths": strengths,
        "watch_out": watch_out,
        "career_fit_reason": career_fit_reason,
    }
