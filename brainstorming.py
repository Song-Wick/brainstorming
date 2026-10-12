import streamlit as st
import re
import json
from google import genai

# ========== [Settings] ==========
PAGE_TITLE = "🚀 SV & McKinsey Brainstorming Board"
LIB_MODE = "📚 대학도서관 HMW 브레인스토밍 (넓게→좁게→계획)"
LIB_MODEL = "gemini-2.5-flash"
MATRIX_MIDPOINT = 3  # 2x2 매트릭스에서 이 점수 이상이면 영향력/노력이 '큼'
# =================================

# 페이지 설정
st.set_page_config(page_title=PAGE_TITLE, layout="wide", initial_sidebar_state="expanded")

# 커스텀 CSS 주입 (고급스럽고 직관적인 UI)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Noto+Sans+KR:wght@300;400;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Outfit', 'Noto Sans KR', sans-serif;
}

/* 메인 타이틀 스타일 */
.title-container {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem 1rem;
    background: radial-gradient(circle at 50% 50%, rgba(255, 75, 75, 0.05) 0%, rgba(255, 255, 255, 0) 70%);
    border-radius: 20px;
    margin-bottom: 2rem;
}
.sv-title {
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, #FF4B4B 0%, #8A2387 50%, #E94057 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
}
.mck-title {
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, #0A2540 0%, #0070F3 50%, #00D4B2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
}
.lib-title {
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, #1B4332 0%, #2D6A4F 50%, #B08968 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
}
.subtitle {
    font-size: 1.1rem;
    color: #4A5568;
    margin-top: 0.5rem;
}

/* 페르소나 카드 스타일 */
.persona-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
    margin-bottom: 20px;
}
.persona-card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 15px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
    transition: transform 0.2s, box-shadow 0.2s;
}
.persona-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.03);
    border-color: #cbd5e1;
}
.persona-icon {
    font-size: 1.5rem;
    margin-bottom: 5px;
}
.persona-name {
    font-weight: 700;
    font-size: 1rem;
    color: #1e293b;
    margin-bottom: 4px;
}
.persona-desc {
    font-size: 0.85rem;
    color: #64748b;
    line-height: 1.35;
}

/* 구분선 데코레이션 */
.stDivider {
    margin-top: 2rem;
    margin-bottom: 2rem;
}
</style>
""", unsafe_allow_html=True)


# API 키 획득 함수 (Secrets 우선, 없을 시 예외 처리하여 사이드바 입력창 유도)
def get_gemini_api_key():
    api_key = ""
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        # secrets.toml 파일 자체가 없을 때의 예외 처리
        pass
        
    if not api_key:
        api_key = st.sidebar.text_input("GEMINI_API_KEY 입력", type="password", help="Streamlit Secrets에 API 키가 없는 경우 직접 입력해 주세요.")
    return api_key.strip()


# ========== [대학도서관 모드: 넓게 → 좁게 → 계획] ==========
# OpenAI Academy 'ChatGPT로 브레인스토밍' 가이드의 흐름(결정 → 제약 조건 → 발산과 평가 분리 → 실행 계획)을
# 3번의 개별 호출로 나누고, 단계 사이마다 사서가 직접 고르고 메모를 남기도록 구성
LIB_PERSONAS = [
    ("🧭", "퍼실리테이터", "단계 규칙을 지키게 합니다. 발산 단계에서는 비판을 막고, 수렴 단계에서는 비교와 선택을 이끕니다."),
    ("🎓", "학부생", "설문 응답자의 다수. 수업, 시험기간, 과제 중심의 일상적 불편과 기대를 대변합니다."),
    ("🔬", "대학원생·연구자", "연구 자료 접근, 장시간 집중 공간, 전문 데이터베이스와 연구 지원 요구를 대변합니다."),
    ("👩‍🏫", "교수", "수업 연계 자료, 정보 리터러시 교육, 연구 지원에 대한 교수자 관점을 제시합니다."),
    ("📚", "주제전문사서", "참고봉사와 이용자 교육 현장 경험, 장서와 서비스 운영 실무 지식을 제공합니다."),
    ("🖥️", "디지털·시스템 사서", "도서관 시스템, 전자자원, 예약·인증 등 디지털 서비스의 구현 가능성을 검토합니다."),
    ("🏛️", "행정·예산 담당", "교내 예산 편성 주기, 인력, 학칙·규정, 본부 보고 절차의 현실을 짚습니다."),
    ("♿", "접근성·포용 담당", "장애학생, 유학생, 야간·원격 이용자 등 놓치기 쉬운 이용자의 입장을 대변합니다."),
]

# (키, 라벨, 예시)
LIB_CONTEXT_FIELDS = [
    ("audience", "대상 이용자", "예: 학부 1~2학년, 시험기간 열람실 이용자"),
    ("timeline", "기간", "예: 다음 학기 안에 시범 운영"),
    ("resources", "예산·인력", "예: 추가 예산 없음, 사서 2명이 업무 일부 할애"),
    ("success", "성공 측정 방법", "예: 좌석 이용률, 학기말 만족도 조사"),
    ("tried", "이미 해 본 시도와 결과", "예: 좌석 예약 앱을 도입했으나 노쇼 문제가 계속됨"),
    ("non_negotiables", "양보할 수 없는 조건", "예: 개인정보 최소 수집, 24시간 개방 불가"),
]

# 단계별로 생성되는 세션 상태 키 (앞 단계를 다시 실행하면 뒤 단계 결과를 지움)
LIB_STAGE_KEYS = [["lib_ctx", "lib_ideas"], ["lib_eval"], ["lib_plan"]]

SCORE_COLUMNS = [
    ("impact", "영향력"),
    ("effort", "노력"),
    ("confidence", "확신"),
    ("user_value", "이용자 체감"),
    ("equity", "형평성"),
]


def reset_library_state(from_stage=1):
    for keys in LIB_STAGE_KEYS[from_stage - 1:]:
        for key in keys:
            st.session_state.pop(key, None)


def call_gemini(api_key, prompt, json_mode=False, temperature=0.7):
    client = genai.Client(api_key=api_key)
    config = {'temperature': temperature}
    if json_mode:
        config['response_mime_type'] = 'application/json'
    response = client.models.generate_content(model=LIB_MODEL, contents=prompt, config=config)
    text = getattr(response, "text", None)
    if not text:
        raise ValueError("Gemini 응답이 비어 있습니다.")
    return text


def parse_json_response(text):
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    return json.loads(cleaned)


def to_score(value):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return 0


def md_cell(value):
    # 마크다운 표 안에서 줄바꿈과 | 문자가 표를 깨뜨리지 않도록 정리
    return str(value).replace("|", "/").replace("\n", " ").strip()


def build_context_block(ctx):
    lines = [f"- 결정해야 할 것: {ctx['decision']}"]
    if ctx.get("hmw"):
        lines.append(f"- HMW 질문: {ctx['hmw']}")
    for key, label, _ in LIB_CONTEXT_FIELDS:
        if ctx.get(key):
            lines.append(f"- {label}: {ctx[key]}")
    if ctx.get("voices"):
        lines.append(f"\n[설문 주관식 답변·공감 지도 발췌]\n{ctx['voices']}")
    return "\n".join(lines)


def build_persona_block():
    return "\n".join(f"- {icon} {name}: {desc}" for icon, name, desc in LIB_PERSONAS)


def build_diverge_prompt(ctx):
    return f"""
당신은 대학도서관 서비스 개선을 위한 브레인스토밍 세션의 참여자들입니다.
이 세션은 '결정 → 제약 조건 → 넓게 → 좁게 → 계획' 흐름으로 진행되며, 지금은 첫 번째 '넓게(발산)' 단계입니다.

[세션 맥락]
{build_context_block(ctx)}

[참여자]
{build_persona_block()}

[이번 단계 규칙]
1. 아이디어를 평가하거나 비판하지 마세요. 실현 가능성 검토는 다음 단계에서 합니다.
2. 퍼실리테이터를 제외한 참여자들이 각자의 관점에서 고르게 아이디어를 내어 총 15~20개를 만드세요.
3. 공간, 서비스, 디지털, 프로그램·교육, 운영·정책, 교내 협력 등 다양한 유형을 섞고, 작고 바로 할 수 있는 안과 과감한 안을 함께 포함하세요.
4. 제약 조건과 '이미 해 본 시도'를 반영해, 같은 시도를 반복하지 말고 그 위에서 발전시키세요.
5. 설문 발췌가 있으면 각 아이디어의 근거가 된 이용자 목소리를 짧게 적으세요. 발췌에 없는 인용을 지어내지 말고, 근거가 없으면 빈 문자열로 두세요.
6. 수익 모델, 시장 규모 같은 비즈니스 용어 대신 이용자와 교육·연구 지원의 언어를 쓰세요.

[출력 형식]
아래 구조의 JSON만 출력하세요.
{{"ideas": [{{"id": 1, "title": "짧은 아이디어 이름", "description": "2~3문장 설명", "proposer": "🎓 학부생", "evidence": "근거가 된 이용자 목소리 또는 빈 문자열"}}]}}
"""


def format_ideas(ideas):
    return "\n".join(
        f"- [{idea['id']}] {idea.get('title', '')} ({idea.get('proposer', '')}): {idea.get('description', '')}"
        + (f" / 근거: {idea['evidence']}" if idea.get('evidence') else "")
        for idea in ideas
    )


def build_converge_prompt(ctx, selected_ideas, memo):
    return f"""
당신은 대학도서관 서비스 개선을 위한 브레인스토밍 세션의 참여자들입니다.
지금은 두 번째 '좁게(수렴)' 단계입니다. 사서가 1단계 아이디어 중 아래 것들을 골랐습니다.

[세션 맥락]
{build_context_block(ctx)}

[참여자]
{build_persona_block()}

[선택된 아이디어]
{format_ideas(selected_ideas)}

[사서의 메모]
{memo or "없음"}

[이번 단계에서 할 일]
1. 아이디어를 2~5개 주제로 묶고, 주제마다 한 문장 요약을 쓰세요.
2. 각 아이디어를 1~5점 정수로 평가하세요.
   - impact: 결정 목표에 대한 영향력
   - effort: 필요한 노력 (높을수록 예산·인력·시간이 많이 듦)
   - confidence: 효과에 대한 확신 (설문 근거와 선행 사례가 있을수록 높음)
   - user_value: 이용자가 직접 체감하는 정도
   - equity: 형평성·접근성 (소외되기 쉬운 이용자에게도 도움이 되는 정도)
3. 각 아이디어에 "빠른 성과" 또는 "기반 작업" 라벨을 붙이고, 점수의 이유를 한 문장으로 쓰세요.
4. 각 아이디어를 더 낫게 만들 방법을 한 가지씩 건설적으로 제안하세요.
5. 전체의 빈틈을 확인하세요. 숨은 가정, 트레이드오프, 놓친 이용자군을 3~5개 적으세요.
6. 하나만 할 수 있다면 무엇을 고를지 정하고 그 이유를 설명하세요.
7. 참여자들의 관점을 종합해 평가하되, 근거 없이 단정하지 마세요. 사서의 메모를 우선 반영하세요.

[출력 형식]
아래 구조의 JSON만 출력하세요. idea_id는 선택된 아이디어의 [번호]를 그대로 쓰세요.
{{"themes": [{{"name": "주제 이름", "summary": "한 문장 요약", "idea_ids": [1, 2]}}],
 "scores": [{{"idea_id": 1, "impact": 4, "effort": 2, "confidence": 3, "user_value": 5, "equity": 3, "label": "빠른 성과", "rationale": "점수 이유", "improvement": "개선 제안 한 가지"}}],
 "gaps": ["빈틈 1", "빈틈 2"],
 "pick_one": {{"idea_id": 1, "reason": "이유"}}}}
"""


def build_plan_prompt(ctx, chosen_idea, chosen_score, evaluation_md, memo):
    score_text = ", ".join(f"{label} {to_score(chosen_score.get(key))}" for key, label in SCORE_COLUMNS) if chosen_score else "없음"
    return f"""
당신은 대학도서관 서비스 개선을 위한 브레인스토밍 세션의 참여자들입니다.
지금은 마지막 '계획' 단계입니다. 사서가 2단계 평가를 보고 아래 방향을 선택했습니다.

[세션 맥락]
{build_context_block(ctx)}

[참여자]
{build_persona_block()}

[선택한 방향]
- {chosen_idea.get('title', '')}: {chosen_idea.get('description', '')}
- 2단계 점수: {score_text}

[2단계 평가 요약]
{evaluation_md}

[사서의 메모]
{memo or "없음"}

[작성할 내용]
아래 제목을 그대로 사용해 마크다운으로 작성하세요.

#### 1. 선택한 방향과 이유
#### 2. 빠른 성과와 기반 작업
바로 시작할 수 있는 일과 시간이 걸리는 기반 작업을 나누어 적으세요.
#### 3. 한 학기 파일럿 실행 계획
표로 작성하세요. (기간 | 마일스톤 | 담당 부서·역할 | 산출물)
#### 4. 성과 지표
이용, 만족, 학습·연구 성과 측면에서 지표와 측정 방법, 목표치를 적으세요.
#### 5. 세 가지 경로: 보수적 · 균형적 · 진보적
경로마다 예상 결과, 위험 요소, 의존 관계, 결정하기 전에 살펴볼 신호를 적으세요.
#### 6. 이해관계자 맵
교내 부서, 학생 대표, 교수 등 관련자와 각자에게 전할 설득 포인트를 표로 적으세요.
#### 7. 시작 · 중단 · 계속 · 재검토할 것

[규칙]
1. 참여자들의 관점이 드러나도록 필요한 곳에 이모지와 역할명으로 짧은 발언을 넣으세요.
2. 수익 모델, 시장 규모, ROI 같은 비즈니스 용어 대신 공공·교육 기관의 언어를 쓰세요.
3. 확인되지 않은 수치는 단정하지 말고 앞에 [가정]을 붙이세요.
4. 제약 조건과 양보할 수 없는 조건을 어기는 계획을 세우지 마세요.
"""


def score_quadrant(score):
    high_impact = to_score(score.get("impact")) >= MATRIX_MIDPOINT
    high_effort = to_score(score.get("effort")) >= MATRIX_MIDPOINT
    if high_impact and not high_effort:
        return "🎯 먼저 할 것 (영향 큼 · 노력 적음)"
    if high_impact:
        return "🏗️ 큰 도전 (영향 큼 · 노력 큼)"
    if not high_effort:
        return "🧩 틈새 과제 (영향 작음 · 노력 적음)"
    return "⏸️ 보류 (영향 작음 · 노력 큼)"


def evaluation_to_markdown(evaluation, ideas_by_id):
    def title(idea_id):
        return ideas_by_id.get(str(idea_id), {}).get("title", f"아이디어 {idea_id}")

    scores = evaluation.get("scores", [])
    lines = ["#### 🗂️ 주제별 묶음"]
    for theme in evaluation.get("themes", []):
        names = ", ".join(title(i) for i in theme.get("idea_ids", []))
        lines.append(f"- **{theme.get('name', '')}**: {theme.get('summary', '')}  \n  └ {names}")

    lines += [
        "",
        "#### 📊 평가 (1~5점, 노력은 높을수록 부담이 큼)",
        "",
        "| 아이디어 | " + " | ".join(label for _, label in SCORE_COLUMNS) + " | 구분 | 이유 |",
        "|---" * (len(SCORE_COLUMNS) + 3) + "|",
    ]
    for score in scores:
        values = " | ".join(str(to_score(score.get(key))) for key, _ in SCORE_COLUMNS)
        lines.append(
            f"| {md_cell(title(score.get('idea_id')))} | {values} | {md_cell(score.get('label', ''))} | {md_cell(score.get('rationale', ''))} |"
        )

    quadrants = {name: [] for name in [
        "🎯 먼저 할 것 (영향 큼 · 노력 적음)",
        "🏗️ 큰 도전 (영향 큼 · 노력 큼)",
        "🧩 틈새 과제 (영향 작음 · 노력 적음)",
        "⏸️ 보류 (영향 작음 · 노력 큼)",
    ]}
    for score in scores:
        quadrants[score_quadrant(score)].append(title(score.get("idea_id")))
    lines += ["", f"#### 🔲 영향력 × 노력 2x2 ({MATRIX_MIDPOINT}점 이상을 '큼'으로 분류)"]
    for name, items in quadrants.items():
        lines.append(f"- **{name}**: {', '.join(items) if items else '없음'}")

    lines += ["", "#### 💡 아이디어별 개선 제안"]
    for score in scores:
        if score.get("improvement"):
            lines.append(f"- **{title(score.get('idea_id'))}**: {score['improvement']}")

    gaps = evaluation.get("gaps", [])
    if gaps:
        lines += ["", "#### 🔍 빈틈 확인 (숨은 가정 · 트레이드오프 · 놓친 이용자)"]
        lines += [f"- {gap}" for gap in gaps]

    pick = evaluation.get("pick_one") or {}
    if pick.get("idea_id") is not None:
        lines += ["", "#### ☝️ 하나만 고른다면", f"**{title(pick['idea_id'])}**: {pick.get('reason', '')}"]
    return "\n".join(lines)


def build_library_transcript():
    ctx = st.session_state.get("lib_ctx")
    ideas = st.session_state.get("lib_ideas") or []
    parts = ["# 대학도서관 HMW 브레인스토밍 기록", "", "## 결정과 제약 조건", build_context_block(ctx) if ctx else ""]
    if ideas:
        parts += ["", "## 1단계 · 넓게 (아이디어 발산)"]
        for idea in ideas:
            parts.append(f"- **[{idea['id']}] {idea.get('title', '')}** ({idea.get('proposer', '')}): {idea.get('description', '')}")
            if idea.get("evidence"):
                parts.append(f"  - 근거: {idea['evidence']}")
    if st.session_state.get("lib_eval"):
        parts += ["", "## 2단계 · 좁게 (수렴과 평가)", st.session_state.lib_eval["markdown"]]
    if st.session_state.get("lib_plan"):
        parts += ["", "## 3단계 · 계획", st.session_state.lib_plan]
    return "\n".join(parts)


def render_library_personas():
    cards = "".join(
        f'<div class="persona-card"><div class="persona-icon">{icon}</div>'
        f'<div class="persona-name">{name}</div><div class="persona-desc">{desc}</div></div>'
        for icon, name, desc in LIB_PERSONAS
    )
    st.markdown(f'<div class="persona-grid">{cards}</div>', unsafe_allow_html=True)


def render_library_mode():
    api_key = get_gemini_api_key()

    # ----- 결정과 제약 조건 -----
    st.write("### 🎯 결정과 제약 조건")
    st.caption("막연한 주제 대신 '무엇을 결정할지'를 적고, 현실적인 제약과 지금까지의 맥락을 알려 주세요.")
    decision = st.text_input(
        "이번 브레인스토밍으로 결정할 것",
        key="lib_in_decision",
        placeholder="예: 다음 학기에 시범 운영할 열람실 개선 서비스 1개를 정한다",
    )
    st.text_input(
        "HMW 질문 (선택)",
        key="lib_in_hmw",
        placeholder="예: 어떻게 하면 시험기간에도 학생들이 자리를 찾느라 시간을 허비하지 않게 할 수 있을까?",
    )
    with st.expander("제약 조건과 지금까지의 맥락", expanded=True):
        cols = st.columns(2)
        for idx, (key, label, placeholder) in enumerate(LIB_CONTEXT_FIELDS):
            with cols[idx % 2]:
                st.text_input(label, key=f"lib_in_{key}", placeholder=placeholder)
    st.text_area(
        "설문 주관식 답변 또는 공감 지도 발췌 (선택)",
        key="lib_in_voices",
        height=150,
        help="붙여 넣은 이용자 목소리를 아이디어의 근거로 사용합니다. 여기에 없는 인용은 만들지 않도록 지시합니다.",
    )

    # ----- 1단계: 넓게 -----
    st.divider()
    st.write("### 🌱 1단계 · 넓게")
    st.caption("평가 없이 다양한 아이디어를 냅니다. 비판과 실현 가능성 검토는 2단계에서 합니다.")
    if st.button("🌱 아이디어 발산하기"):
        if not decision.strip():
            st.warning("결정할 것을 입력해 주세요.")
        elif not api_key:
            st.error("GEMINI_API_KEY를 설정해 주세요. (Streamlit secrets 또는 사이드바 수동 입력)")
        else:
            ctx = {"decision": decision.strip()}
            for key in ["hmw", "voices"] + [field[0] for field in LIB_CONTEXT_FIELDS]:
                ctx[key] = st.session_state.get(f"lib_in_{key}", "").strip()
            with st.spinner("가상 팀원들이 아이디어를 내고 있습니다..."):
                try:
                    data = parse_json_response(call_gemini(api_key, build_diverge_prompt(ctx), json_mode=True, temperature=0.9))
                    ideas = data.get("ideas") if isinstance(data, dict) else None
                    if not ideas:
                        raise ValueError("아이디어 목록이 비어 있습니다.")
                    for idx, idea in enumerate(ideas, start=1):
                        idea["id"] = str(idea.get("id", idx))
                    reset_library_state(1)
                    st.session_state.lib_ctx = ctx
                    st.session_state.lib_ideas = ideas
                    # 체크박스 키를 새로 만들어 이전 선택이 남지 않게 함
                    st.session_state.lib_ideas_gen = st.session_state.get("lib_ideas_gen", 0) + 1
                except Exception as e:
                    st.error(f"아이디어 생성 중 오류가 발생했습니다: {e}")

    ideas = st.session_state.get("lib_ideas")
    if not ideas:
        return
    ctx = st.session_state.lib_ctx
    ideas_by_id = {idea["id"]: idea for idea in ideas}
    gen = st.session_state.lib_ideas_gen

    st.write(f"**{len(ideas)}개의 아이디어**가 나왔습니다. 2단계에서 다룰 아이디어를 골라 주세요.")
    selected_ids = []
    with st.container(border=True):
        for idea in ideas:
            if st.checkbox(f"**{idea.get('title', '')}** · {idea.get('proposer', '')}", key=f"lib_pick_{gen}_{idea['id']}"):
                selected_ids.append(idea["id"])
            st.caption(idea.get("description", ""))
            if idea.get("evidence"):
                st.caption(f"🗣️ 근거: {idea['evidence']}")

    # ----- 2단계: 좁게 -----
    st.divider()
    st.write("### 🔎 2단계 · 좁게")
    st.caption("고른 아이디어를 주제로 묶고, 영향력·노력·확신·이용자 체감·형평성으로 비교합니다.")
    converge_memo = st.text_area(
        "평가할 때 반영할 메모 (선택)",
        key="lib_in_memo2",
        placeholder="예: 예산보다 인력 부담이 더 큰 제약입니다. 유학생 관점을 더 고려해 주세요.",
    )
    if st.button(f"🔎 고른 아이디어 {len(selected_ids)}개 좁히기", disabled=not selected_ids):
        if not api_key:
            st.error("GEMINI_API_KEY를 설정해 주세요. (Streamlit secrets 또는 사이드바 수동 입력)")
        else:
            selected_ideas = [ideas_by_id[i] for i in selected_ids]
            with st.spinner("아이디어를 묶고 비교하고 있습니다..."):
                try:
                    evaluation = parse_json_response(call_gemini(
                        api_key, build_converge_prompt(ctx, selected_ideas, converge_memo.strip()), json_mode=True, temperature=0.4
                    ))
                    if not isinstance(evaluation, dict) or not evaluation.get("scores"):
                        raise ValueError("평가 결과가 비어 있습니다.")
                    for score in evaluation["scores"]:
                        score["idea_id"] = str(score.get("idea_id"))
                    reset_library_state(2)
                    st.session_state.lib_eval = {
                        "data": evaluation,
                        "markdown": evaluation_to_markdown(evaluation, ideas_by_id),
                    }
                except Exception as e:
                    st.error(f"평가 중 오류가 발생했습니다: {e}")

    evaluation = st.session_state.get("lib_eval")
    if not evaluation:
        return
    with st.container(border=True):
        st.markdown(evaluation["markdown"])

    # ----- 3단계: 계획 -----
    st.divider()
    st.write("### 🗺️ 3단계 · 계획")
    st.caption("방향을 하나 정하면 파일럿 계획, 성과 지표, 세 가지 경로를 만듭니다.")
    scores_by_id = {score["idea_id"]: score for score in evaluation["data"]["scores"] if score["idea_id"] in ideas_by_id}
    options = list(scores_by_id)
    if not options:
        st.warning("평가 결과의 아이디어 번호를 1단계 목록과 연결하지 못했습니다. 2단계를 다시 실행해 주세요.")
        return
    pick_id = str((evaluation["data"].get("pick_one") or {}).get("idea_id"))
    chosen_id = st.radio(
        "진행할 방향",
        options,
        index=options.index(pick_id) if pick_id in options else 0,
        format_func=lambda i: ideas_by_id[i].get("title", i) + (" ☝️ 추천" if i == pick_id else ""),
        key=f"lib_choice_{gen}",
    )
    plan_memo = st.text_area(
        "계획에 반영할 메모 (선택)",
        key="lib_in_memo3",
        placeholder="예: 다른 아이디어 '시험기간 야간 연장'과 결합해 주세요. 학생회와 함께 추진하고 싶습니다.",
    )
    if st.button("🗺️ 실행 계획 만들기"):
        if not api_key:
            st.error("GEMINI_API_KEY를 설정해 주세요. (Streamlit secrets 또는 사이드바 수동 입력)")
        else:
            with st.spinner("실행 계획을 세우고 있습니다..."):
                try:
                    st.session_state.lib_plan = call_gemini(api_key, build_plan_prompt(
                        ctx, ideas_by_id[chosen_id], scores_by_id[chosen_id], evaluation["markdown"], plan_memo.strip()
                    ))
                except Exception as e:
                    st.error(f"계획 생성 중 오류가 발생했습니다: {e}")

    if st.session_state.get("lib_plan"):
        with st.container(border=True):
            st.markdown(st.session_state.lib_plan)


# 사이드바 설정 (깨지는 외부 이미지 링크 대신, 네트워크 환경에 지장 없는 세련된 이모지 로고 적용)
st.sidebar.markdown("<h1 style='text-align: center; margin-bottom: 1rem; font-size: 4.5rem;'>🧠</h1>", unsafe_allow_html=True)
st.sidebar.title("🛠️ 설정 패널")

# 모드 선택
mode = st.sidebar.selectbox(
    "토론 프레임워크 선택",
    ["🚀 실리콘밸리식 10단계 브레인스토밍", "👔 맥킨지/BCG식 10단계 전략 수립", LIB_MODE],
    index=0
)

# 세션 상태 초기화
if 'transcript' not in st.session_state:
    st.session_state.transcript = None
if 'last_mode' not in st.session_state:
    st.session_state.last_mode = None

# 모드가 변경되면 이전 결과 초기화
if st.session_state.last_mode != mode:
    st.session_state.transcript = None
    reset_library_state(1)
    st.session_state.last_mode = mode


# 타이틀 및 인트로 영역
if mode == "🚀 실리콘밸리식 10단계 브레인스토밍":
    st.markdown("""
    <div class="title-container">
        <div class="sv-title">🚀 실리콘밸리식 10단계 브레인스토밍 대시보드</div>
        <div class="subtitle">빠른 아이디어 발산, MVP 검증, 에지 케이스 분석을 통해 아이디어를 파괴적으로 스케일업합니다.</div>
    </div>
    """, unsafe_allow_html=True)
elif mode == LIB_MODE:
    st.markdown("""
    <div class="title-container">
        <div class="lib-title">📚 대학도서관 HMW 브레인스토밍</div>
        <div class="subtitle">결정과 제약 조건에서 출발해, 넓게 발산하고 이용자 관점으로 좁힌 뒤 실행 가능한 파일럿 계획으로 만듭니다.</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="title-container">
        <div class="mck-title">👔 맥킨지/BCG식 10단계 전략 수립 대시보드</div>
        <div class="subtitle">MECE 문제 정의, 가설 수립, 2x2 매트릭스, BCG 포트폴리오, 시나리오 플래닝으로 구조적인 최적의 전략을 도출합니다.</div>
    </div>
    """, unsafe_allow_html=True)


# 참여 페르소나 소개 영역
st.write("### 👥 오늘 토론에 참여할 가상 팀원")
if mode == "🚀 실리콘밸리식 10단계 브레인스토밍":
    st.markdown("""
    <div class="persona-grid">
        <div class="persona-card">
            <div class="persona-icon">🦄</div>
            <div class="persona-name">창업자 (Founder)</div>
            <div class="persona-desc">거대한 비전 제시, 미친 아이디어 제안, 팀 독려 및 도전적 방향 설정.</div>
        </div>
        <div class="persona-card">
            <div class="persona-icon">🎯</div>
            <div class="persona-name">PM (Product Manager)</div>
            <div class="persona-desc">사용자 중심 사고, 비즈니스 가치 증명, 일정 관리 및 피처 우선순위화.</div>
        </div>
        <div class="persona-card">
            <div class="persona-icon">💻</div>
            <div class="persona-name">엔지니어 (Engineer)</div>
            <div class="persona-desc">기술적 구현 가능성 태클, 시스템 아키텍처, 데이터 무결성 및 확장성 검증.</div>
        </div>
        <div class="persona-card">
            <div class="persona-icon">🎨</div>
            <div class="persona-name">디자이너 (Designer)</div>
            <div class="persona-desc">UX/UI 직관성 확보, 마찰 없는 사용자 저니 설계 및 시각적 일관성 확보.</div>
        </div>
        <div class="persona-card">
            <div class="persona-icon">💰</div>
            <div class="persona-name">투자자 (VC)</div>
            <div class="persona-desc">시장 규모(TAM) 평가, 수익 모델(BM) 검증, 경쟁적 진입장벽(Moat) 요구.</div>
        </div>
        <div class="persona-card">
            <div class="persona-icon">📚</div>
            <div class="persona-name">주니어 사서 (Jr. Librarian)</div>
            <div class="persona-desc">도서관 현장 실무 및 일상적 애로사항, 디지털 도구에 친숙한 학생들의 반응 대변.</div>
        </div>
        <div class="persona-card">
            <div class="persona-icon">👵</div>
            <div class="persona-name">시니어 사서 (Sr. Librarian)</div>
            <div class="persona-desc">행정적/조직적 현실 규명, 예산 확보 타당성, 규정 준수 및 안정적 공간 관리 노하우.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
elif mode == LIB_MODE:
    render_library_personas()
else:
    st.markdown("""
    <div class="persona-grid">
        <div class="persona-card">
            <div class="persona-icon">👔</div>
            <div class="persona-name">파트너 (Partner)</div>
            <div class="persona-desc">의사결정권자 아젠다 조율, 거시적 방향성 제시 및 궁극적 핵심 가치 제안.</div>
        </div>
        <div class="persona-card">
            <div class="persona-icon">📊</div>
            <div class="persona-name">프로젝트 매니저 (EM)</div>
            <div class="persona-desc">MECE 문제 정의 및 논리 트리 설계, 마일스톤 관리 및 결과 산출 조율.</div>
        </div>
        <div class="persona-card">
            <div class="persona-icon">📈</div>
            <div class="persona-name">어소시에이트 (Associate)</div>
            <div class="persona-desc">정량적/정성적 벤치마킹, 가설 검증용 실증 데이터 분석 및 재무 모델링.</div>
        </div>
        <div class="persona-card">
            <div class="persona-icon">🎨</div>
            <div class="persona-name">비주얼 스페셜리스트</div>
            <div class="persona-desc">논리적 장표의 구조화 및 시각적 스토리텔링, 설득력 높은 프레젠테이션 설계.</div>
        </div>
        <div class="persona-card">
            <div class="persona-icon">🏢</div>
            <div class="persona-name">외부 자문위원 (Advisor)</div>
            <div class="persona-desc">산업 도메인 전문 지식 제공, 시장의 최신 트렌드 및 실행 리스크 사전 검토.</div>
        </div>
        <div class="persona-card">
            <div class="persona-icon">📚</div>
            <div class="persona-name">주니어 사서 (Jr. Librarian)</div>
            <div class="persona-desc">도서관 현장 실무 및 일상적 애로사항, 디지털 도구에 친숙한 학생들의 반응 대변.</div>
        </div>
        <div class="persona-card">
            <div class="persona-icon">👵</div>
            <div class="persona-name">시니어 사서 (Sr. Librarian)</div>
            <div class="persona-desc">행정적/조직적 현실 규명, 예산 확보 타당성, 규정 준수 및 안정적 공간 관리 노하우.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# 대학도서관 모드는 단계별 흐름을 따로 그리고 여기서 종료
if mode == LIB_MODE:
    render_library_mode()
    if st.session_state.get("lib_ideas"):
        st.sidebar.divider()
        st.sidebar.subheader("📥 결과 다운로드")
        st.sidebar.download_button(
            label="📝 세션 기록 다운로드 (Markdown)",
            data=build_library_transcript(),
            file_name="library_brainstorming.md",
            mime="text/markdown"
        )
    st.stop()


# 메인 화면: 주제 입력
topic = st.text_input(
    "브레인스토밍 및 전략 수립할 핵심 질문이나 주제를 입력하세요.", 
    value="여기에 질문이나 주제를 입력하세요",
    help="구체적인 맥락(대상 이용자, 목표, 제한 조건)을 포함하면 더욱 심도 깊은 결과가 나옵니다."
)


# 대시보드 로직
if st.button("🔥 소집 완료 및 토론 시작"):
    if not topic.strip():
        st.warning("주제를 입력해주세요.")
    else:
        api_key = get_gemini_api_key()
        if not api_key:
            st.error("GEMINI_API_KEY를 설정해 주세요. (Streamlit secrets 또는 사이드바 수동 입력)")
        else:
            with st.spinner('가상 전문가들과 도서관 사서팀이 열띤 토론을 진행 중입니다... (약 15~25초 소요)'):
                client = genai.Client(api_key=api_key)
                
                # 모드에 따른 프롬프트 생성
                if mode == "🚀 실리콘밸리식 10단계 브레인스토밍":
                    prompt = f"""
                    당신은 실리콘밸리 최고의 유니콘 스타트업 빌딩 팀과 대학 도서관 전문가들입니다.
                    오늘의 토론 주제는 다음과 같습니다.
                    
                    주제: "{topic}"
                    
                    이 주제에 대해 [Level 1]부터 [Level 10]까지 점진적으로 깊어지는 브레인스토밍 회의록을 작성하세요.
                    처음에는 가벼운 아이디어로 시작하지만, 레벨이 올라갈수록 기술적 한계, 수익화, 예외 케이스 처리, 데이터 아키텍처 등 구체적이고 날카로운 논의로 발전해야 합니다.

                    [참여 역할 (반드시 아래 이모지와 페르소나를 지켜서 발언을 구성하세요)]
                    - 🦄 창업자(Founder): 거대한 비전 제시, 미친 아이디어 제안, 팀 독려
                    - 🎯 PM(Product Manager): 사용자 중심 사고, 비즈니스 가치 증명, 일정 및 스펙 관리
                    - 💻 엔지니어(Engineer): 기술적 구현 가능성 태클, 시스템 아키텍처 제안, 데이터 무결성 지적
                    - 🎨 디자이너(Product Designer): UX/UI의 직관성, 사용자 경험의 마찰 최소화 집중
                    - 💰 투자자(VC): 시장 규모(TAM), 수익 모델(BM), 경쟁 우위(Moat), ROI 압박
                    - 📚 주니어 사서(Junior Librarian): 실무적/현장 관점, 일상적 애로사항, 이용자 반응, 디지털 전환 트렌드 접목
                    - 👵 시니어 사서(Senior Librarian): 행정적/조직적 관점, 예산 확보 및 규정 준수, 장기적 도서관 운영 안정성 및 공간 활용 노하우

                    [10단계 레벨 구성 가이드]
                    - ### [Level 1]: 아이디어 발산 및 브레인덤프 (Divergence & Braindump)
                    - ### [Level 2]: 타겟 사용자 페르소나 및 핵심 Pain Point 정의
                    - ### [Level 3]: MVP 정의 및 핵심 가치 제안 (Value Proposition)
                    - ### [Level 4]: 사용자 경험 디자인 (UX/UI & User Journey)
                    - ### [Level 5]: 기술 아키텍처 및 구현 스택 논의 (Tech Stack)
                    - ### [Level 6]: 시장 규모(TAM) 분석 및 비즈니스 모델(BM) 설계
                    - ### [Level 7]: 기술적 예외 처리 및 에지 케이스 (Edge Cases)
                    - ### [Level 8]: 데이터 스키마 및 확장성 (Scalability)
                    - ### [Level 9]: 성장 지표 및 A/B 테스트 시나리오 (Growth Hacking)
                    - ### [Level 10]: 로드맵, Go-to-Market 전략 및 피보팅 조건

                    [출력 규칙]
                    1. 마크다운을 사용하여 가독성 높은 실제 회의록 형태로 작성하세요.
                    2. 반드시 `### [Level 1]: 주제명` 부터 `### [Level 10]: 주제명` 까지 명확하게 단계를 나누어 작성하세요.
                    3. 각 레벨마다 주제가 심화되는 과정이 논리적으로 보여야 합니다. 
                       (예: 사서분들이 현장의 어려움이나 공간 운영의 제약 사항을 제시하면, 실리콘밸리 팀원들이 이를 해결할 수 있는 기술적/비즈니스적 솔루션을 제안하고 반박하는 형태의 티키타카)
                    4. 일반적인 뻔한 대답을 피하고, 해당 분야의 전문 용어(Fail Fast, MVP, A/B Testing, Scalability, MECE 등)와 사서 실무 용어를 적극적으로 사용하세요.
                    """
                else:
                    prompt = f"""
                    당신은 맥킨지/BCG 최고의 글로벌 전략 컨설팅 팀과 대학 도서관 전문가들입니다.
                    오늘의 전략 수립 주제는 다음과 같습니다.
                    
                    주제: "{topic}"
                    
                    이 주제에 대해 [Level 1]부터 [Level 10]까지 점진적으로 고도화되는 전략 기획 회의록을 작성하세요.
                    맥킨지/BCG의 과학적인 전략 기획 프레임워크를 기반으로, 가벼운 현황 파악에서 시작해 MECE 분석, 우선순위 매트릭스, BCG 포트폴리오, 시나리오 및 실행 KPI까지 정교하게 전개해야 합니다.

                    [참여 역할 (반드시 아래 이모지와 페르소나를 지켜서 발언을 구성하세요)]
                    - 👔 파트너(Partner): 의사결정권자 아젠다 조율, 거시적 방향성 제시 및 궁극적 핵심 가치 제안
                    - 📊 프로젝트 매니저(EM/Project Leader): MECE 문제 정의 및 논리 트리 설계, 마일스톤 관리 및 결과 산출 조율
                    - 📈 어소시에이트(Associate): 정량적/정성적 벤치마킹, 가설 검증용 실증 데이터 분석 및 재무 모델링
                    - 🎨 비주얼 디자인 스페셜리스트(Visual Designer): 논리적 장표의 구조화 및 시각적 스토리텔링, 설득력 높은 프레젠테이션 설계
                    - 🏢 외부 자문위원(Advisor): 산업 도메인 전문 지식 제공, 시장의 최신 트렌드 및 실행 리스크 사전 검토
                    - 📚 주니어 사서(Junior Librarian): 실무적/현장 관점, 일상적 애로사항, 이용자 반응, 디지털 전환 트렌드 접목
                    - 👵 시니어 사서(Senior Librarian): 행정적/조직적 관점, 예산 확보 및 규정 준수, 장기적 도서관 운영 안정성 및 공간 활용 노하우

                    [10단계 레벨 구성 가이드]
                    - ### [Level 1]: 문제 정의 및 핵심 질문 설정 (Problem Framing)
                    - ### [Level 2]: MECE 로직 트리를 통한 이슈 구조화 (Issue Structuring)
                    - ### [Level 3]: 우선순위 설정 및 2x2 매트릭스 분석 (Prioritization Matrix)
                    - ### [Level 4]: 글로벌 베스트 프랙티스 및 벤치마킹 (Benchmarking)
                    - ### [Level 5]: 비용-편익 분석(CBA) 및 비즈니스 케이스 (Quantitative Analysis)
                    - ### [Level 6]: BCG 매트릭스 기반 전략적 포트폴리오 구성 (BCG Matrix)
                    - ### [Level 7]: 운영 모델(Operating Model) 및 조직 설계 (Governance & Ops Model)
                    - ### [Level 8]: 리스크 관리 및 시나리오 플래닝 (Scenario Planning)
                    - ### [Level 9]: 이해관계자 관리(Stakeholder Management) 및 변화 관리(Change Management)
                    - ### [Level 10]: 성과 지표(KPI) 및 지속 가능한 성과 관리 체계 구축 (Monitoring & Balanced Scorecard)

                    [출력 규칙]
                    1. 마크다운을 사용하여 가독성 높은 실제 컨설팅 회의록/워크샵 형태로 작성하세요.
                    2. 반드시 `### [Level 1]: 주제명` 부터 `### [Level 10]: 주제명` 까지 명확하게 단계를 나누어 작성하세요.
                    3. 각 레벨마다 논리적으로 발전하는 티키타카가 있어야 합니다. 
                       (예: 사서분들이 예산 제약과 공간 보존의 시급성을 지적하면, 컨설턴트들이 ROI 분석이나 이해관계자 관리 장표 구성을 제안하며 설득하는 형태)
                    4. 단순 나열을 피하고 맥킨지/BCG 전략 컨설팅 프레임워크와 용어(MECE, Logic Tree, BCG Matrix, CBA, BSC, Stakeholder alignment, Change management 등)를 적극적으로 사용하세요.
                    """
                
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config={'temperature': 0.7} 
                    )
                    
                    if not getattr(response, "text", None):
                        raise ValueError("Gemini 응답이 비어 있습니다.")
                    
                    st.session_state.transcript = response.text
                    
                except Exception as e:
                    st.error(f"토론 생성 중 오류가 발생했습니다: {e}")

# 결과 출력
if st.session_state.transcript:
    st.divider()
    st.subheader("📝 심층 브레인스토밍/전략 수립 회의록")
    
    # 다운로드 버튼 제공
    st.sidebar.divider()
    st.sidebar.subheader("📥 결과 다운로드")
    st.sidebar.download_button(
        label="📝 회의록 다운로드 (Markdown)",
        data=st.session_state.transcript,
        file_name=f"{'sv' if '실리콘밸리' in mode else 'mck'}_strategy_transcript.md",
        mime="text/markdown"
    )
    
    # 두 가지 뷰 모드 제공: 전체보기 vs 탭으로 레벨별로 보기
    view_option = st.radio("보기 옵션 선택", ["📑 전체 회의록 한눈에 보기", "🗂️ 레벨별로 나누어 보기"], horizontal=True)
    
    if view_option == "📑 전체 회의록 한눈에 보기":
        # HTML 태그 내부에 마크다운을 넣어 발생하는 파싱 깨짐 방지를 위해 Streamlit 기본 container(border=True) 사용
        with st.container(border=True):
            st.markdown(st.session_state.transcript)
    else:
        # 정규식을 이용해 각 레벨 파싱
        pattern = r'(###\s*\[?Level\s*(?:10|[1-9])\]?:?\s*[^\n]*)'
        parts = re.split(pattern, st.session_state.transcript)
        
        if len(parts) <= 1:
            # 파싱이 안 된 경우 일반 출력으로 폴백
            st.warning("레벨별 자동 파싱에 실패했습니다. 전체 회의록 모드로 확인해 주세요.")
            with st.container(border=True):
                st.markdown(st.session_state.transcript)
        else:
            intro = parts[0].strip()
            if intro:
                st.markdown(intro)
            
            # 레벨 타이틀과 내용을 묶기
            levels = []
            i = 1
            while i < len(parts):
                level_title = parts[i].replace("###", "").strip()
                level_content = parts[i+1].strip() if i+1 < len(parts) else ""
                levels.append((level_title, level_content))
                i += 2
            
            # 탭 생성
            tab_titles = [f"L{idx+1}" for idx in range(len(levels))]
            tabs = st.tabs(tab_titles)
            
            for idx, (title, content) in enumerate(levels):
                with tabs[idx]:
                    st.markdown(f"### {title}")
                    # HTML div 내에 마크다운이 들어가 발생하는 </div> 태그 노출 방지를 위해 container(border=True) 사용
                    with st.container(border=True):
                        st.markdown(content)
