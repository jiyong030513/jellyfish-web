"""상담봇 테스트: DB·Gemini 키 없이 돈다 (가짜 예보 + 가짜 대비수칙 자료 + 가짜 LLM).

실행: pytest -q   (04_웹_react/backend 폴더에서)
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAKE = {
    "B149": [{"beach_id": "B149", "beach_name": "해운대", "sido": "부산시", "horizon_weeks": k,
              "target_week": f"{k}주 뒤", "risk_index": v, "risk_level": lvl, "base_date": "평년 기준 전망"}
             for k, v, lvl in [(1, 0.41, "높음"), (2, 0.395, "보통"), (4, 0.65, "매우 높음")]],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    kb = tmp_path / "knowledge"
    kb.mkdir()
    (kb / "00_답변원칙.md").write_text("근거에 있는 내용만 답한다.", encoding="utf-8")
    (kb / "01_응급처치.md").write_text(
        "---\n문서: 응급처치\n기관: 보건복지부\n출처URL: https://example.go.kr/a\n우선순위: 1\n---\n"
        "## 경증 대처\n바닷물로 씻고 촉수는 카드로 뗀다.\n## 중증 대처\n호흡곤란·의식저하면 119.\n", encoding="utf-8")
    (kb / "02_예방.md").write_text(
        "---\n문서: 예방\n기관: 국립수산과학원\n출처URL: https://example.go.kr/b\n우선순위: 2\n---\n"
        "## 예방 수칙\n래시가드를 입는다.\n", encoding="utf-8")

    from fastapi.testclient import TestClient
    import main
    from jellycast import chat, forecast

    monkeypatch.setattr(chat, "KNOWLEDGE_DIR", kb)
    chat._kb.clear()
    monkeypatch.setattr(forecast, "beaches", lambda: [{"beach_id": "B149", "beach_name": "해운대", "sido": "부산시"}])
    monkeypatch.setattr(forecast, "beach_forecast", lambda bid: FAKE.get(bid, []))
    monkeypatch.setattr(forecast, "safer_beaches", lambda region, h, limit=3: [])
    calls = []
    monkeypatch.setattr(chat, "call_llm", lambda system, history, prompt: calls.append(prompt) or "가짜 답변")
    c = TestClient(main.app)          # with 없이 → 서버 시작(DB 읽기)을 하지 않음
    c.calls = calls
    return c


def test_예보와_출처가_붙는다(client):
    r = client.post("/api/chat", json={"message": "해운대 다음 주 가도 돼?"})
    assert r.status_code == 200
    j = r.json()
    assert j["answer"] == "가짜 답변" and j["emergency"] is False
    assert [x["horizon_weeks"] for x in j["forecast"]] == [1, 2, 4]
    assert j["forecast"][0]["risk_level"] == "높음"                 # 화면과 같은 4단계 등급
    assert "해운대" in client.calls[0] and "0.41" in client.calls[0]  # 예보 숫자가 프롬프트에 들어감
    assert j["sources"][0]["기관"].startswith("해파리 위험도 예측")


def test_화면에서_선택한_해수욕장ID(client):
    j = client.post("/api/chat", json={"message": "여기 괜찮아?", "beach_id": "B149", "horizon_weeks": 4}).json()
    assert j["forecast"][0]["beach_name"] == "해운대"


def test_응급이면_emergency_true(client):
    j = client.post("/api/chat", json={"message": "해파리에 쏘였는데 숨이 차요"}).json()
    assert j["emergency"] is True
    assert "중증" in client.calls[0]                                # 중증 대처 섹션을 꼭 넣음


def test_LLM_실패해도_응급은_119_안내(client, monkeypatch):
    from jellycast import chat

    def boom(*a):
        raise RuntimeError("down")
    monkeypatch.setattr(chat, "call_llm", boom)
    j = client.post("/api/chat", json={"message": "해파리 쏘이고 의식이 흐려요"}).json()
    assert j["emergency"] is True and "119" in j["answer"]
    assert client.post("/api/chat", json={"message": "예방법 알려줘"}).status_code == 502


def test_자료_없으면_상담봇만_503(client, monkeypatch, tmp_path):
    from jellycast import chat
    monkeypatch.setattr(chat, "KNOWLEDGE_DIR", tmp_path / "없음")
    chat._kb.clear()
    assert client.post("/api/chat", json={"message": "예방법"}).status_code == 503


def test_질문_검증(client):
    assert client.post("/api/chat", json={"message": ""}).status_code == 422
    assert client.post("/api/chat", json={"message": "a", "horizon_weeks": 3}).status_code == 422
