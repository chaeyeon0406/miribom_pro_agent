# app.py
# 최종 검증 및 대화형 로직 버전

import streamlit as st
import json
from core import process_patient_statement, generate_grouped_follow_up

# --- 1. 페이지 및 세션 상태 설정 ---
st.set_page_config(page_title="AI PRO 대화형 문진", layout="wide")

def initialize_session_state():
    """세션 상태를 초기화하는 함수"""
    if 'conversation_stage' not in st.session_state:
        st.session_state.conversation_stage = "initial_statement" # 현재 대화 단계: initial_statement, follow_up, completed
    if 'pro_data' not in st.session_state:
        try:
            with open("pro_phq9.json", "r", encoding="utf-8") as f:
                st.session_state.pro_data = json.load(f)
        except FileNotFoundError:
            st.error("'pro_phq9.json' 파일을 찾을 수 없습니다.")
            st.stop()
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = [] # AI와 환자의 대화 기록

initialize_session_state()

# --- 2. UI 렌더링 ---
st.title("🤖 AI PRO 대화형 문진 시스템")
st.markdown("환자의 이야기에 귀 기울여 스스로 설문을 완성하는 AI 에이전트입니다.")

col1, col2 = st.columns([1, 1])

# --- 왼쪽 컬럼: 대화 및 입력 ---
with col1:
    st.subheader("AI와의 대화")
    
    # 대화 기록 표시
    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])

    # 현재 대화 단계에 따라 입력 UI 변경
    if st.session_state.conversation_stage == "initial_statement":
        patient_input = st.text_area("안녕하세요, 어디가 불편해서 오셨나요? 편하게 말씀해주세요.", key="initial_input", height=200)
        if st.button("AI에게 전달하기", type="primary", use_container_width=True):
            if patient_input.strip():
                st.session_state.chat_history.append({"role": "user", "content": patient_input})
                with st.spinner("AI가 환자의 이야기를 분석 중입니다..."):
                    pro_json_str = json.dumps(st.session_state.pro_data, ensure_ascii=False)
                    result = process_patient_statement(pro_json_str, patient_input)
                    if isinstance(result, str):
                        st.error(result)
                    else:
                        st.session_state.pro_data = result
                        st.session_state.conversation_stage = "follow_up"
                        st.rerun()
            else:
                st.warning("환자의 이야기를 입력해주세요.")

    elif st.session_state.conversation_stage == "follow_up":
        # AI의 종합 추가 질문 생성 및 표시
        remaining_qs = [item['question'] for item in st.session_state.pro_data if item.get('answer_score') is None]
        if remaining_qs:
            # AI 질문을 대화 기록에 추가 (한 번만)
            if not st.session_state.chat_history or st.session_state.chat_history[-1]['role'] == 'user':
                with st.spinner("AI가 어떻게 질문할지 생각 중입니다..."):
                    patient_statement_summary = st.session_state.chat_history[0]['content']
                    ai_question = generate_grouped_follow_up(patient_statement_summary, remaining_qs)
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_question})
                    st.rerun()

            # 환자의 추가 답변 입력
            follow_up_input = st.text_area("AI의 질문에 답변해주세요.", key="follow_up_input", height=150)
            if st.button("답변 전달하기", use_container_width=True):
                if follow_up_input.strip():
                    st.session_state.chat_history.append({"role": "user", "content": follow_up_input})
                    with st.spinner("AI가 추가 답변을 분석 중입니다..."):
                        pro_json_str = json.dumps(st.session_state.pro_data, ensure_ascii=False)
                        result = process_patient_statement(pro_json_str, follow_up_input)
                        if isinstance(result, str):
                            st.error(result)
                        else:
                            st.session_state.pro_data = result
                            st.rerun() # 다시 follow-up 단계 실행하여 남은 질문 확인
                else:
                    st.warning("답변을 입력해주세요.")
        else: # 모든 질문 완료
            st.session_state.conversation_stage = "completed"
            st.rerun()

    elif st.session_state.conversation_stage == "completed":
        st.success("모든 문진이 완료되었습니다. 우측 결과를 확인해주세요.")
    
    # 리셋 버튼
    if st.button("처음부터 다시 시작"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# --- 오른쪽 컬럼: 분석 결과 ---
with col2:
    st.subheader("실시간 분석 결과")
    
    # 완료된 항목 표시
    completed_count = 0
    total_count = len(st.session_state.pro_data)
    
    for item in st.session_state.pro_data:
        if item.get("answer_score") is not None:
            completed_count += 1
            q_id = item["id"]
            question = item["question"].split("(")[0].strip()
            selected_option = next((opt["text"] for opt in item["options"] if opt["score"] == item["answer_score"]), "N/A")
            reasoning = item.get("reasoning", "")
            with st.container(border=True):
                st.markdown(f"**{q_id.split('_')[1]}. {question}**")
                st.success(f"✓ 선택: {selected_option}")
                if reasoning:
                    st.caption(f"💬 근거: \"{reasoning}\"")

    st.progress(completed_count / total_count, text=f"진행률: {completed_count}/{total_count}")

    if st.session_state.conversation_stage == "completed":
        st.divider()
        st.balloons()
        final_score = sum(
            item["answer_score"] for item in st.session_state.pro_data
            if item.get("answer_score") is not None and item["id"] != "phq9_10"
        )
        st.metric(label="PHQ-9 최종 점수 (1~9번 문항 합계)", value=f"{final_score} 점")
        with st.expander("최종 결과 JSON 보기"):
            st.json(st.session_state.pro_data)
