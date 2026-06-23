import streamlit as st
import re
from google import genai

# ========== [Settings] ==========
PAGE_TITLE = "🚀 SV & McKinsey Brainstorming Board"
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

/* 회의록 출력 스타일 */
.transcript-box {
    background-color: #ffffff;
    padding: 35px;
    border-radius: 16px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
    margin-top: 20px;
    line-height: 1.6;
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


# 사이드바 설정
st.sidebar.image("https://img.icons8.com/clouds/100/000000/brainstorming.png", width=80)
st.sidebar.title("🛠️ 설정 패널")

# 모드 선택
mode = st.sidebar.selectbox(
    "토론 프레임워크 선택",
    ["🚀 실리콘밸리식 10단계 브레인스토밍", "👔 맥킨지/BCG식 10단계 전략 수립"],
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
    st.session_state.last_mode = mode

# 사이드바 회의록 다운로드 버튼 추가
if st.session_state.transcript:
    st.sidebar.divider()
    st.sidebar.subheader("📥 결과 다운로드")
    st.sidebar.download_button(
        label="📝 회의록 다운로드 (Markdown)",
        data=st.session_state.transcript,
        file_name=f"{'sv' if '실리콘밸리' in mode else 'mck'}_strategy_transcript.md",
        mime="text/markdown"
    )


# 타이틀 및 인트로 영역
if mode == "🚀 실리콘밸리식 10단계 브레인스토밍":
    st.markdown("""
    <div class="title-container">
        <div class="sv-title">🚀 실리콘밸리식 10단계 브레인스토밍 대시보드</div>
        <div class="subtitle">빠른 아이디어 발산, MVP 검증, 에지 케이스 분석을 통해 아이디어를 파괴적으로 스케일업합니다.</div>
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


# 메인 화면: 주제 입력
topic = st.text_input(
    "브레인스토밍 및 전략 수립할 핵심 질문이나 주제를 입력하세요.", 
    value="학술정보관·민주광장 통합 메가 플라자(Mega-Plaza) 구축 시 4대 가치 창출 방안",
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
    st.download_button(
        label="📥 회의록 다운로드 (Markdown)",
        data=st.session_state.transcript,
        file_name=f"{'sv' if '실리콘밸리' in mode else 'mck'}_strategy_transcript.md",
        mime="text/markdown"
    )
    
    # 두 가지 뷰 모드 제공: 전체보기 vs 탭으로 레벨별로 보기
    view_option = st.radio("보기 옵션 선택", ["📑 전체 회의록 한눈에 보기", "🗂️ 레벨별로 나누어 보기"], horizontal=True)
    
    if view_option == "📑 전체 회의록 한눈에 보기":
        st.markdown(
            f"""
            <div class="transcript-box">
                {st.session_state.transcript}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # 정규식을 이용해 각 레벨 파싱
        # 패턴: Level 1부터 10까지 헤더 추출
        pattern = r'(###\s*\[?Level\s*(?:10|[1-9])\]?:?\s*[^\n]*)'
        parts = re.split(pattern, st.session_state.transcript)
        
        if len(parts) <= 1:
            # 파싱이 안 된 경우 일반 출력으로 폴백
            st.warning("레벨별 자동 파싱에 실패했습니다. 전체 회의록 모드로 확인해 주세요.")
            st.markdown(
                f"""
                <div class="transcript-box">
                    {st.session_state.transcript}
                </div>
                """,
                unsafe_allow_html=True
            )
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
                    st.markdown(
                        f"""
                        <div style="background-color: #f8fafc; padding: 25px; border-radius: 12px; border-left: 5px solid #0070F3; margin-top: 15px; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0;">
                            {content}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
