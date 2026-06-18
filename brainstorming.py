import streamlit as st
from google import genai
import time

# ========== [Settings] ==========
PAGE_TITLE = "🚀 SV Brainstorming Board"
# =================================

def get_gemini_api_key():
    """Streamlit secrets에서 API 키를 가져옵니다."""
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key or not api_key.strip():
        st.error("GEMINI_API_KEY가 Streamlit secrets에 설정되어 있지 않습니다.")
        st.stop()
    return api_key.strip()

# 페이지 설정
st.set_page_config(page_title=PAGE_TITLE, layout="wide")

st.title("🚀 실리콘밸리식 10단계 브레인스토밍 대시보드")
st.markdown("""
입력하신 주제에 대해 **창업자, PM, 엔지니어, 디자이너, 투자자** 페르소나가 등장하여 
Level 1(가벼운 발산)부터 Level 10(심층 검증 및 스케일업)까지 치열한 난상토론을 벌입니다.
""")

# 세션 상태 초기화
if 'transcript' not in st.session_state:
    st.session_state.transcript = None

# 메인 화면: 주제 입력
topic = st.text_input(
    "브레인스토밍할 핵심 질문이나 주제를 입력하세요.", 
    value="학술정보관·민주광장 통합 메가 플라자(Mega-Plaza) 구축 시 4대 가치 창출 방안",
    help="구체적인 상황이나 타겟을 포함하면 더 깊이 있는 토론이 진행됩니다."
)

if st.button("🔥 실리콘밸리 팀 소집 및 토론 시작"):
    if not topic.strip():
        st.warning("주제를 입력해주세요.")
    else:
        with st.spinner('가상 팀원들이 주제를 학습하고 Level 10 심도까지 토론을 진행 중입니다... (약 10~20초 소요)'):
            clean_api_key = get_gemini_api_key()
            client = genai.Client(api_key=clean_api_key)
            
            # 페르소나 및 레벨업 시스템이 적용된 프롬프트
            prompt = f"""
            당신은 실리콘밸리 최고의 유니콘 스타트업을 만드는 핵심 팀입니다.
            오늘의 브레인스토밍 주제는 다음과 같습니다.
            
            주제: "{topic}"
            
            당신은 이 주제에 대해 [Level 1]부터 [Level 10]까지 점진적으로 깊어지는 회의록을 작성해야 합니다.
            처음에는 가벼운 아이디어로 시작하지만, 레벨이 올라갈수록 기술적 한계, 수익화, 예외 케이스 처리, 데이터 아키텍처 등 구체적이고 날카로운 논의로 발전해야 합니다.

            [참여 역할 (반드시 아래 이모지와 페르소나를 지켜서 발언하세요)]
            - 🦄 창업자(Founder): 거대한 비전 제시, 미친 아이디어 제안, 팀 독려
            - 🎯 PM(Product Manager): 사용자 중심 사고, 비즈니스 가치 증명, 일정 및 스펙 관리
            - 💻 엔지니어(Engineer): 기술적 구현 가능성 태클, 시스템 아키텍처 제안, 데이터 무결성 지적
            - 🎨 디자이너(Product Designer): UX/UI의 직관성, 사용자 경험의 마찰 최소화 집중
            - 💰 투자자(VC): 시장 규모(TAM), 수익 모델(BM), 경쟁 우위(Moat), ROI 압박

            [출력 규칙]
            1. 마크다운을 사용하여 가독성 높은 실제 회의록 형태로 작성하세요.
            2. 반드시 `### [Level 1]: ~~~` 부터 `### [Level 10]: ~~~` 까지 명확하게 단계를 나누어 작성하세요.
            3. 각 레벨마다 주제가 심화되는 과정이 논리적으로 보여야 합니다. (예: Level 3에서 디자이너가 낸 아이디어를 Level 4에서 엔지니어가 기술적으로 비판하고, Level 5에서 PM이 절충안을 내는 식의 티키타카)
            4. 일반적인 뻔한 대답을 피하고, 해당 분야의 전문 용어와 실리콘밸리식 사고방식(Fail Fast, MVP, A/B Testing, Scalability 등)을 적극적으로 사용하세요.
            """
            
            try:
                # 창의적이고 다양한 아이디어 발산을 위해 temperature를 0.7로 설정
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
    st.subheader("📝 심층 브레인스토밍 회의록")
    
    # 다운로드 버튼 제공
    st.download_button(
        label="📥 회의록 다운로드 (Markdown)",
        data=st.session_state.transcript,
        file_name="sv_brainstorming_transcript.md",
        mime="text/markdown"
    )
    
    # 마크다운 렌더링을 위한 컨테이너 (여백 및 배경색 지정)
    with st.container():
        st.markdown(
            f"""
            <div style="background-color: #ffffff; padding: 30px; border-radius: 10px; border: 1px solid #e3e8ef;">
                {st.session_state.transcript}
            </div>
            """,
            unsafe_allow_html=True
        )