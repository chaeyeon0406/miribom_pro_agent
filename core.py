# core.py

import os
import json
from typing import Union, List
import google.generativeai as genai
from dotenv import load_dotenv
from prompts import MASTER_PROMPT, GROUPED_FOLLOW_UP_PROMPT

# =========================
# 환경설정
# =========================
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY not found in .env file")

genai.configure(api_key=GOOGLE_API_KEY)

# JSON 응답을 위한 모델
json_llm = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={"response_mime_type": "application/json"}
)

# 일반 텍스트 응답을 위한 모델
text_llm = genai.GenerativeModel(
    model_name="gemini-1.5-flash"
)

# =========================
# 핵심 함수
# =========================
def process_patient_statement(pro_json_string: str, patient_text: str) -> Union[dict, str]:
    """
    환자 발화와 PRO JSON을 받아 LLM으로 처리하고 결과 JSON(dict) 또는 에러 메시지(str)를 반환합니다.
    이 함수는 초기 분석과 후속 답변 분석 모두에 사용됩니다.
    """
    final_prompt = f"""
{MASTER_PROMPT}

# INPUT DATA
## PRO_QUESTIONNAIRE (JSON)
{pro_json_string}

## PATIENT_STATEMENT (TEXT)
{patient_text}
    """.strip()

    try:
        response = json_llm.generate_content(final_prompt)
        if not response or not hasattr(response, "text"):
            return "❌ API 응답이 비어있습니다."
        try:
            result_json = json.loads(response.text)
            return result_json
        except json.JSONDecodeError:
            return f"⚠️ JSON 파싱 실패. RAW RESPONSE: {response.text}"
    except Exception as e:
        return f"❌ An error occurred during API call: {e}"


def generate_grouped_follow_up(patient_statement: str, remaining_questions: List[str]) -> str:
    """
    남아있는 여러 질문들을 종합하여 하나의 자연스러운 대화형 질문으로 생성합니다.
    """
    remaining_questions_list = "\n".join(f"- {q}" for q in remaining_questions)
    
    try:
        prompt = GROUPED_FOLLOW_UP_PROMPT.format(
            patient_statement=patient_statement,
            remaining_questions_list=remaining_questions_list
        )
        response = text_llm.generate_content(prompt)
        if response and hasattr(response, "text"):
            return response.text.strip()
        else:
            return "혹시 다른 불편한 점은 없으신가요?" # AI 응답 실패 시 Fallback 질문
    except Exception as e:
        print(f"Error during grouped question generation: {e}")
        return "혹시 다른 불편한 점은 없으신가요?"
