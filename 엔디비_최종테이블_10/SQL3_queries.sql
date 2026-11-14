-- 질의 예시 (보고서 3.4절 / 시연용)
USE jellyfish;

-- Q1. 8월 2주에 위험도가 가장 높은 해수욕장 10곳
SELECT 해수욕장명, 시도명, 시군명, ROUND(통합출현율 * 100, 1) AS 출현율_퍼센트, 평년수온
FROM v_해수욕장주간위험도
WHERE 월 = 8 AND 주차 = 2
ORDER BY 통합출현율 DESC
LIMIT 10;

-- Q2. 특정 해수욕장의 32주 위험도와 연결 관측소 (사용자 조회, 삽입 SQL에서는 %s로 바인딩)
SELECT v.주차명, ROUND(v.통합출현율 * 100, 1) AS 출현율_퍼센트, v.평년수온, k.관측소명, h.관측소거리km
FROM v_해수욕장주간위험도 v
JOIN 해수욕장 h ON v.해수욕장ID = h.해수욕장ID
JOIN 관측소 k   ON h.관측소ID = k.관측소ID
WHERE v.해수욕장명 = '해운대'
ORDER BY v.월, v.주차;

-- Q3. 설문 기반 시군별 목격률 (2024~2025, 응답 30건 이상)
SELECT g.시도명, g.시군명, COUNT(*) AS 응답수,
       ROUND(100 * AVG(r.목격여부 = '보았음'), 1) AS 목격률
FROM 설문응답 r
JOIN 설문지점 p ON r.지점ID = p.지점ID
JOIN 시군 g     ON p.시군ID = g.시군ID
WHERE r.목격여부 IN ('보았음', '보지 못했음')
GROUP BY g.시도명, g.시군명
HAVING COUNT(*) >= 30
ORDER BY 목격률 DESC;

-- Q4. 권역별 연도별 대량출현(통합 50% 이상) 주 수
SELECT 권역명, 연도, SUM(통합 >= 50) AS 대량출현_주수, COUNT(*) AS 보고_주수
FROM v_학습데이터
GROUP BY 권역명, 연도
ORDER BY 권역명, 연도;

-- Q5. 관측소 연결 거리가 100km를 넘는 해수욕장 (수온 참고치 경고 대상)
SELECT g.시도명, COUNT(*) AS 해수욕장수, ROUND(AVG(h.관측소거리km), 1) AS 평균거리km
FROM 해수욕장 h JOIN 시군 g ON h.시군ID = g.시군ID
WHERE h.관측소거리km > 100
GROUP BY g.시도명;

-- Q6. 머신러닝 학습 데이터 추출 (4주 뒤 급증 예측)
SELECT 권역명, 시작일, 연중주차, 통합, 통합_1주전, 통합_변화_1주,
       수온_주평균, 수온_평년차, 기온_주평균, 풍속_주평균, 유의파고_주평균, 타깃_급증_4주후, 분할
FROM v_학습데이터
WHERE 타깃_급증_4주후 IS NOT NULL;

-- Q7. 해수욕장별 현재 상태와 4주 뒤 예측 위험 지수 (권역별 최신 "보고" 기준)
--     ① 권역마다 가장 최근 주간보고를 찾는다 (권역마다 날짜가 다를 수 있음)
--     ② 그 주 통합 출현율이 50% 이상이면 이미 대량출현 → 급증 예측 대상이 아님
--     ③ 최근 1년 안에 보고가 없는 권역은 '최근 보고 없음'
--     ④ 나머지는 그 주의 예측을 보여 주고, 정렬지수(상한 적용 전 값) 순으로 정렬
WITH 최신보고 AS (
    SELECT s.권역명, s.시작일 AS 최신보고일, s.통합 AS 최신통합출현율
    FROM v_학습데이터 s
    JOIN (SELECT 권역명, MAX(시작일) AS d FROM v_학습데이터 GROUP BY 권역명) m
      ON s.권역명 = m.권역명 AND s.시작일 = m.d),
  기준 AS (SELECT DATE_SUB(MAX(최신보고일), INTERVAL 1 YEAR) AS 일년전 FROM 최신보고)
SELECT h.해수욕장명, g.시도명, g.시군명, g.권역명, r.최신보고일, r.최신통합출현율,
       CASE WHEN r.최신보고일 < (SELECT 일년전 FROM 기준) THEN '최근 보고 없음'
            WHEN r.최신통합출현율 >= 50 THEN '이미 대량출현'
            ELSE '예측' END AS 상태,
       p.권역급증확률, p.가중치, p.예측위험지수, p.정렬지수
FROM 해수욕장 h
JOIN 시군 g          ON h.시군ID = g.시군ID
JOIN 최신보고 r      ON r.권역명 = g.권역명
LEFT JOIN v_해수욕장예측위험도 p
       ON p.해수욕장ID = h.해수욕장ID AND p.기준일 = r.최신보고일 AND p.예측기간 = 4
ORDER BY FIELD(상태, '이미 대량출현', '예측', '최근 보고 없음'), p.정렬지수 DESC, h.해수욕장명;

-- Q8. 2024~2025 설문 보조 검증 데이터 (권역 x 조사주차 목격률, 응답 5건 이상)
SELECT 권역명, 조사연도, 조사주차, 응답수, 목격수, 출현율
FROM v_설문권역집계
ORDER BY 권역명, 조사연도, 조사주차;
