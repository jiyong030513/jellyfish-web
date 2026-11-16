"""POST /chat — 젤리캐스트 AI 해파리 상담봇 (RAG)

흐름
  1) Retrieval  : 예보 DB에서 위험 지수 조회 + 대비수칙 자료(knowledge/)에서 관련 섹션 검색
  2) Augmented  : 조회·검색 결과를 질문과 함께 프롬프트에 넣음
  3) Generation : Gemini가 그 근거로만 답변 생성 → 출처는 서버가 붙임
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import forecast
from .rag import KnowledgeBase

log = logging.getLogger(__name__)
router = APIRouter()

KNOWLEDGE_DIR = os.environ.get("KNOWLEDGE_DIR", Path(__file__).resolve().parent / "knowledge")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
_kb: dict = {}


def kb() -> KnowledgeBase:
    """대비수칙 자료는 처음 질문할 때 읽는다. 자료가 없으면 상담봇만 503 (웹의 다른 기능은 정상)."""
    if "kb" not in _kb:
        try:
            _kb["kb"] = KnowledgeBase(KNOWLEDGE_DIR)
        except Exception as e:
            log.error("대비수칙 자료를 읽지 못함: %s", e)
            raise HTTPException(status_code=503, detail="상담 자료를 준비 중이에요. 잠시 후 다시 시도해 주세요.")
    return _kb["kb"]

# 이런 말이 있으면 LLM 답과 상관없이 응급 플래그를 켠다 (화면에 119 배너 표시용)
EMERGENCY_WORDS = ["숨", "호흡", "의식", "기절", "쓰러", "실신", "구토", "토해", "토하", "어지러",
                   "온몸", "전신", "식은땀", "눈에", "눈을", "경련", "가슴", "심장"]
STUNG_WORDS = ["쏘였", "쏘임", "쏘인", "쏘이면", "물렸", "따끔", "따가", "부었", "부어"]

# 질문 의도 → 꼭 넣을 섹션 (섹션 제목에 들어 있는 말). 검색 점수와 상관없이 기준 자료를 넣는다.
INTENT_SECTIONS = [
    (("쏘였", "쏘이면", "쏘인", "쏘임", "대처", "응급", "씻", "촉수", "따끔"), "경증"),
    (("예방", "입고", "입어", "옷", "래시가드", "준비", "챙기", "챙겨"), "예방"),
    (("신고", "어디서 확인", "속보"), "정보 확인처"),
    (("종류", "생김새", "생겼", "무슨 해파리", "어떤 해파리", "구별", "알아보"), "[종류]"),
    (("찜질", "통증", "아파", "아프"), "경증"),
]

FIXED_EMERGENCY_ANSWER = (
    "지금 바로 119에 신고하세요. 구급대가 오기 전까지 쏘인 부위를 바닷물로 씻고, "
    "남은 촉수는 신용카드 같은 플라스틱 카드로 떼어내세요. 수돗물·생수·알코올로 씻거나 "
    "쏘인 곳을 문지르지 마세요.\n\n(출처: 보건복지부·중앙응급의료센터)"
)

SYSTEM_ROLE = """너는 '젤리캐스트'의 AI 해파리 상담봇이다.
해수욕장 이용객에게 해파리 위험 예보와 대비 수칙을 쉬운 한국어로 안내한다.
아래 [답변 원칙]을 반드시 지키고, 사용자 메시지에 들어 있는 [예보 데이터]와 [대비수칙 자료]에 있는 내용만 근거로 답한다.
예보 수치는 주어진 값(% 표기)을 그대로 쓰고 새로 만들지 않는다. 위험 지수는 확률이 아니라 해수욕장끼리 비교하는 상대 지수이며,
등급은 낮음·보통·높음·매우 높음 4단계다. 답변은 5~8문장 이내로 짧게 쓴다.
출처 URL은 쓰지 않는다 (서버가 붙인다)."""


class Turn(BaseModel):
    role: Literal["user", "model"]
    text: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    beach_id: str | None = Field(None, max_length=10)   # 화면에서 선택한 해수욕장ID (예: "B149")
    horizon_weeks: Literal[1, 2, 4] | None = None
    history: list[Turn] = Field(default_factory=list, max_length=10)


class Source(BaseModel):
    기관: str
    url: str


class ChatResponse(BaseModel):
    answer: str
    emergency: bool
    forecast: list[dict]
    sources: list[Source]


def is_emergency(msg: str) -> bool:
    return any(w in msg for w in EMERGENCY_WORDS) and (any(w in msg for w in STUNG_WORDS) or "해파리" in msg)


def collect_forecast(req: ChatRequest) -> list[dict]:
    """질문/화면 정보로 예보 데이터를 모은다. DB가 안 되면 빈 목록 (상담봇은 계속 동작)."""
    try:
        horizon = req.horizon_weeks or forecast.guess_horizon(req.message)
        rows: list[dict] = []
        ids = [req.beach_id] if req.beach_id else []
        ids += [b["beach_id"] for b in forecast.find_beaches(req.message) if b["beach_id"] not in ids]
        for bid in ids[:2]:
            rows += [r | {"kind": "요청 해수욕장"} for r in forecast.beach_forecast(bid)]
        region = forecast.find_region(req.message)
        if region is None and rows:
            region = rows[0].get("sido")
        if region:
            asked = {r["beach_name"] for r in rows}
            alts = [r for r in forecast.safer_beaches(region, horizon, limit=3 + len(asked))
                    if r["beach_name"] not in asked][:3]
            rows += [r | {"kind": f"{region} 위험 낮은 곳"} for r in alts]
        if not rows:  # "해변 추천해줘"처럼 지역·해수욕장이 없으면 전국에서 위험 낮은 곳
            rows = [r | {"kind": "전국 위험 낮은 곳"} for r in forecast.safer_beaches(None, horizon, limit=5)]
        return rows
    except Exception as e:  # DB 연결 실패 등
        log.warning("예보 조회 실패: %s", e)
        return []


def _num(x) -> str:
    return "?" if x is None else f"{float(x):.2f}"


def format_forecast(rows: list[dict]) -> str:
    if not rows:
        return "(조회된 예보 없음 — 예보 수치를 말하지 말 것)"
    lines = []
    for r in rows:
        lines.append(f"- [{r['kind']}] {r['beach_name']}({r.get('sido', '')}) {r['horizon_weeks']}주 뒤"
                     f"(대상 주: {r.get('target_week', '?')}): 위험 지수 {r.get('risk_text') or _num(r.get('risk_index'))} → {r['risk_level']}"
                     f" / 기준일 {r.get('base_date', '?')}")
    return "\n".join(lines)


def build_prompt(req: ChatRequest, rows: list[dict], chunks) -> str:
    docs = "\n\n".join(c.as_context() for c in chunks) or "(관련 자료 없음)"
    return (f"[예보 데이터]\n{format_forecast(rows)}\n\n"
            f"[대비수칙 자료]\n{docs}\n\n"
            f"[질문]\n{req.message}")


def call_llm(system: str, history: list[Turn], prompt: str) -> str:
    """Gemini 호출. 다른 LLM(OpenAI 호환 등)로 바꾸려면 이 함수만 고치면 된다."""
    from google import genai
    from google.genai import types

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY 환경변수가 없습니다.")
    client = genai.Client(api_key=key)
    contents = [{"role": t.role, "parts": [{"text": t.text}]} for t in history]
    contents.append({"role": "user", "parts": [{"text": prompt}]})
    resp = client.models.generate_content(
        model=MODEL,
        contents=contents,
        # Gemini 3.x는 답하기 전에 '생각'에 토큰을 쓰는데, 그게 출력 한도를 다 써서 답이 잘렸음 → 생각 끔 + 한도 여유
        config=types.GenerateContentConfig(system_instruction=system, temperature=0.3, max_output_tokens=1500,
                                           # flash: 생각에 토큰을 다 써 답이 잘리므로 끔 / flash-lite: 원래 생각 안 함(이 설정을 주면 400 오류)
                                           thinking_config=None if "lite" in MODEL else types.ThinkingConfig(thinking_budget=0)),
    )
    return (resp.text or "").strip()


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    emergency = is_emergency(req.message)
    KB = kb()

    # 1) Retrieval
    rows = collect_forecast(req)
    must = [sec for words, sec in INTENT_SECTIONS if any(w in req.message for w in words)]
    if emergency:
        must.insert(0, "중증")
    chunks = KB.search(req.message, k=4, must_include=tuple(must))

    # 2) Augmented + 3) Generation
    system = f"{SYSTEM_ROLE}\n\n[답변 원칙]\n{KB.rules}"
    try:
        answer = call_llm(system, req.history, build_prompt(req, rows, chunks))
        if not answer:
            raise RuntimeError("빈 응답")
    except Exception as e:
        log.error("LLM 호출 실패: %s", e)
        if emergency:  # 응급 상황이면 LLM이 죽어도 고정 안내는 나간다
            answer = FIXED_EMERGENCY_ANSWER
        else:
            raise HTTPException(status_code=502, detail="상담봇 응답을 만들지 못했습니다. 잠시 후 다시 시도해 주세요.")

    # 출처는 모델이 아니라 서버가 붙인다 (링크가 틀릴 일이 없게)
    seen, sources = set(), []
    for c in chunks:
        s = c.source
        if s["url"] and s["url"] not in seen:
            seen.add(s["url"])
            sources.append(Source(**s))
    if rows:
        sources.insert(0, Source(기관="해파리 위험도 예측 (국립수산과학원 주간보고·기상청 부이·설문 기반)", url=""))

    return ChatResponse(answer=answer, emergency=emergency, forecast=rows, sources=sources)
