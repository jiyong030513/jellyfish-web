-- 계산으로 만드는 값은 저장하지 않고 뷰로 도출한다 (MySQL 8.0)
-- 관측자료의 종료일은 저장하지 않고 다음 식으로 계산한다 (그 주 일요일, 단 연말을 넘지 않음)
--   LEAST(DATE_ADD(시작일, INTERVAL 6 - WEEKDAY(시작일) DAY), DATE(CONCAT(YEAR(시작일), '-12-31')))
USE jellyfish;

-- [빈칸 규칙] 2017년 이후 원자료는 미목격(0%)을 빈칸으로 기록한다.
--   ① 같은 보고·권역에 값이 하나라도 있으면 빈칸 = 0%
--   ② 세 어종이 모두 빈칸이어도, 같은 해 같은 권역에 그보다 앞과 뒤에 모두 값이 있는 보고가 있으면(시즌 중간) 0%
--   ③ 그 외(시즌 시작·끝 주, 보고가 중단된 권역)는 미조사와 구분할 수 없어 결측
--   v_권역기준곡선과 v_학습데이터에 같은 규칙을 쓴다

-- 1) 권역 기준곡선: 권역 x 어종 x 월 x 주차(1~7일=1주 … 22일~말일=4주)의 10년 평균 출현율
--    관측 연수 2년 미만 칸은 같은 권역·어종·월 평균, 그것도 없으면 전국 같은 어종·월 평균으로 보간
CREATE OR REPLACE VIEW v_권역기준곡선 AS
WITH RECURSIVE
  m AS (SELECT 5 AS 월 UNION ALL SELECT 월 + 1 FROM m WHERE 월 < 12),
  w AS (SELECT 1 AS 주차 UNION ALL SELECT 주차 + 1 FROM w WHERE 주차 < 4),
  보고권역 AS (   -- 보고·권역마다 세 어종 중 값이 하나라도 있는지
    SELECT o.보고코드, o.권역명, b.시작일, MAX(o.출현율 IS NOT NULL) AS 값있음
    FROM 출현기록 o JOIN 주간보고 b ON o.보고코드 = b.보고코드
    GROUP BY o.보고코드, o.권역명, b.시작일),
  유효 AS (       -- 빈칸 = 0%로 볼 수 있는 보고·권역
    SELECT r.보고코드, r.권역명
    FROM 보고권역 r
    WHERE r.값있음 = 1
       OR (EXISTS (SELECT 1 FROM 보고권역 e WHERE e.권역명 = r.권역명 AND YEAR(e.시작일) = YEAR(r.시작일)
                    AND e.시작일 < r.시작일 AND e.값있음 = 1)
           AND EXISTS (SELECT 1 FROM 보고권역 e WHERE e.권역명 = r.권역명 AND YEAR(e.시작일) = YEAR(r.시작일)
                    AND e.시작일 > r.시작일 AND e.값있음 = 1))),
  obs AS (
    SELECT o.권역명, o.어종명,
           MONTH(DATE_ADD(b.시작일, INTERVAL 3 DAY)) AS 월,
           LEAST(4, FLOOR((DAY(DATE_ADD(b.시작일, INTERVAL 3 DAY)) - 1) / 7) + 1) AS 주차,
           COALESCE(o.출현율, 0) AS 출현율
    FROM 출현기록 o JOIN 주간보고 b ON o.보고코드 = b.보고코드
    JOIN 유효 v ON v.보고코드 = o.보고코드 AND v.권역명 = o.권역명),   -- 빈칸 규칙 ①②
  칸 AS (SELECT 권역명, 어종명, 월, 주차, AVG(출현율) AS 평균, COUNT(*) AS n
         FROM obs WHERE 월 BETWEEN 5 AND 12 GROUP BY 권역명, 어종명, 월, 주차),
  월평균 AS (SELECT 권역명, 어종명, 월, AVG(출현율) AS 평균
             FROM obs WHERE 월 BETWEEN 5 AND 12 GROUP BY 권역명, 어종명, 월),
  전국 AS (SELECT 어종명, 월, AVG(출현율) AS 평균
           FROM obs WHERE 월 BETWEEN 5 AND 12 GROUP BY 어종명, 월)
SELECT r.권역명, s.어종명, m.월, w.주차,
       ROUND(COALESCE(CASE WHEN c.n >= 2 THEN c.평균 END, a.평균, t.평균) / 100, 4) AS 기준출현율,
       COALESCE(c.n, 0) AS 관측연수,
       CASE WHEN c.n >= 2 THEN '원자료' WHEN a.평균 IS NOT NULL THEN '월평균 보간' ELSE '전국 월평균 보간' END AS 보간
FROM 권역 r CROSS JOIN 어종 s CROSS JOIN m CROSS JOIN w
LEFT JOIN 칸 c     ON c.권역명 = r.권역명 AND c.어종명 = s.어종명 AND c.월 = m.월 AND c.주차 = w.주차
LEFT JOIN 월평균 a ON a.권역명 = r.권역명 AND a.어종명 = s.어종명 AND a.월 = m.월
LEFT JOIN 전국 t   ON t.어종명 = s.어종명 AND t.월 = m.월;

-- 2) 관측소 평년: 관측소 x 월 x 주차 평균 (주 중간일 기준, 화면 표시용 2014~2025 전체)
--    ※ 머신러닝의 수온 평년차는 v_학습데이터 안에서 학습기간(2014~2020)만으로 따로 계산한다
CREATE OR REPLACE VIEW v_관측소평년 AS
SELECT 관측소ID, 월, 주차, ROUND(AVG(수온), 3) AS 수온, ROUND(AVG(기온), 3) AS 기온,
       ROUND(AVG(풍속), 3) AS 풍속, ROUND(AVG(유의파고), 3) AS 유의파고, COUNT(수온) AS 자료수
FROM (SELECT 관측소ID, 수온, 기온, 풍속, 유의파고,
             MONTH(DATE_ADD(시작일, INTERVAL FLOOR(DATEDIFF(LEAST(DATE_ADD(시작일, INTERVAL 6 - WEEKDAY(시작일) DAY), DATE(CONCAT(YEAR(시작일), '-12-31'))), 시작일) / 2) DAY)) AS 월,
             LEAST(4, FLOOR((DAY(DATE_ADD(시작일, INTERVAL FLOOR(DATEDIFF(LEAST(DATE_ADD(시작일, INTERVAL 6 - WEEKDAY(시작일) DAY), DATE(CONCAT(YEAR(시작일), '-12-31'))), 시작일) / 2) DAY)) - 1) / 7) + 1) AS 주차
      FROM 관측자료) x
WHERE 월 BETWEEN 5 AND 12
GROUP BY 관측소ID, 월, 주차;

-- 3) 해수욕장 가중치 (유도 속성)
--    목격률 = 보았음 / (보았음 + 보지 못했음)   ※ '조업하지 않았음'은 제외
--    보정 주변 목격률 = (반경 30km 내 목격 수 + 30 x 권역 평균 목격률) / (반경 30km 내 응답 수 + 30)
--    해수욕장 가중치 = 보정 주변 목격률 / 해당 권역 전체 평균 목격률
--    (권역 평균 수준의 가상 응답 30건을 더해, 응답이 적을수록 가중치가 1에 가까워지도록 보정)
CREATE OR REPLACE VIEW v_해수욕장가중치 AS
WITH 응답 AS (   -- 좌표가 있는 설문 응답
    SELECT p.위도, p.경도, p.시군ID,
           CASE WHEN r.목격여부 = '보았음' THEN 1 ELSE 0 END AS 목격
    FROM 설문응답 r
    JOIN 설문지점 p ON r.지점ID = p.지점ID
    WHERE r.목격여부 IN ('보았음', '보지 못했음') AND p.위도 IS NOT NULL),
  권역평균 AS (  -- 해당 권역 전체 평균 목격률
    SELECT g.권역명, 1e0 * SUM(a.목격) / COUNT(*) AS 권역목격률   -- 1e0: 소수점 4자리 반올림 없이 실수로 계산
    FROM 응답 a JOIN 시군 g ON a.시군ID = g.시군ID
    GROUP BY g.권역명),
  주변 AS (      -- 해수욕장 반경 30km 내 응답 수와 목격 수
    SELECT h.해수욕장ID, COUNT(*) AS 주변응답수, SUM(a.목격) AS 주변목격수
    FROM 해수욕장 h JOIN 응답 a
      ON ST_Distance_Sphere(POINT(h.경도, h.위도), POINT(a.경도, a.위도)) <= 30000
    GROUP BY h.해수욕장ID)
SELECT h.해수욕장ID, g.권역명,
       COALESCE(s.주변응답수, 0) AS 주변응답수,
       COALESCE(s.주변목격수, 0) AS 주변목격수,
       ROUND(k.권역목격률, 4) AS 권역목격률,
       ROUND((COALESCE(s.주변목격수, 0) + 30 * k.권역목격률) / (COALESCE(s.주변응답수, 0) + 30), 4) AS 보정주변목격률,
       ROUND(CASE WHEN k.권역목격률 > 0
                  THEN ((COALESCE(s.주변목격수, 0) + 30 * k.권역목격률) / (COALESCE(s.주변응답수, 0) + 30)) / k.권역목격률
                  ELSE 1 END, 4) AS 가중치
FROM 해수욕장 h
JOIN 시군 g        ON h.시군ID = g.시군ID
LEFT JOIN 권역평균 k ON k.권역명 = g.권역명
LEFT JOIN 주변 s     ON s.해수욕장ID = h.해수욕장ID;

-- 4) 해수욕장 주간 위험도 (평년값): 권역 기준곡선 x 해수욕장 가중치 (최대 1), 연결 관측소의 평년 수온
CREATE OR REPLACE VIEW v_해수욕장주간위험도 AS
WITH 기준 AS (
    SELECT 권역명, 월, 주차,
           MAX(CASE WHEN 어종명 = '노무라입깃해파리' THEN 기준출현율 END) AS 노무라,
           MAX(CASE WHEN 어종명 = '보름달물해파리'   THEN 기준출현율 END) AS 보름달,
           MAX(CASE WHEN 어종명 = '기타해파리'       THEN 기준출현율 END) AS 기타,
           MIN(보간) AS 보간
    FROM v_권역기준곡선 GROUP BY 권역명, 월, 주차),
  최종 AS (
    SELECT h.해수욕장ID, h.해수욕장명, g.시도명, g.시군명, g.권역명, h.관측소ID, k.월, k.주차, wt.가중치,
           LEAST(1, k.노무라 * wt.가중치) AS p노무라,
           LEAST(1, k.보름달 * wt.가중치) AS p보름달,
           LEAST(1, k.기타   * wt.가중치) AS p기타
    FROM 해수욕장 h
    JOIN 시군 g             ON h.시군ID = g.시군ID
    JOIN v_해수욕장가중치 wt ON h.해수욕장ID = wt.해수욕장ID
    JOIN 기준 k             ON k.권역명 = g.권역명)
SELECT f.해수욕장ID, f.해수욕장명, f.시도명, f.시군명, f.권역명, f.월, f.주차,
       CONCAT(f.월, '월 ', f.주차, '주') AS 주차명, f.가중치,
       ROUND(f.p노무라, 4) AS 노무라, ROUND(f.p보름달, 4) AS 보름달, ROUND(f.p기타, 4) AS 기타,
       ROUND(1 - (1 - f.p노무라) * (1 - f.p보름달) * (1 - f.p기타), 4) AS 통합출현율,
       f.관측소ID, n.수온 AS 평년수온, n.유의파고 AS 평년유의파고
FROM 최종 f
LEFT JOIN v_관측소평년 n ON n.관측소ID = f.관측소ID AND n.월 = f.월 AND n.주차 = f.주차;

-- 5) 설문 권역 집계: 2024~2025 설문을 권역 x 조사주차 목격률로 (머신러닝 보조 검증용)
CREATE OR REPLACE VIEW v_설문권역집계 AS
SELECT g.권역명, r.조사연도, r.조사주차,
       DATE(MIN(r.응답일자)) AS 첫응답일, DATE(MAX(r.응답일자)) AS 마지막응답일,
       COUNT(*) AS 응답수, SUM(r.목격여부 = '보았음') AS 목격수,
       ROUND(100 * SUM(r.목격여부 = '보았음') / COUNT(*), 2) AS 출현율
FROM 설문응답 r
JOIN 설문지점 p ON r.지점ID = p.지점ID
JOIN 시군 g     ON p.시군ID = g.시군ID
WHERE r.목격여부 IN ('보았음', '보지 못했음')
GROUP BY g.권역명, r.조사연도, r.조사주차
HAVING COUNT(*) >= 5;

-- 6) 학습 데이터: 권역 x 주간보고, 어종을 피벗한 뒤 같은 권역에서 날짜로 k주 전·후 값을 연결
--    (LAG/LEAD는 보고가 빠진 주가 있으면 엉뚱한 주를 가져오므로, 날짜 차이 7k±3일 중 가장 가까운 보고를 찾음)
CREATE OR REPLACE VIEW v_학습데이터 AS
WITH
  보고권역 AS (   -- 보고·권역마다 세 어종 중 값이 하나라도 있는지
    SELECT o.보고코드, o.권역명, b.시작일, MAX(o.출현율 IS NOT NULL) AS 값있음
    FROM 출현기록 o JOIN 주간보고 b ON o.보고코드 = b.보고코드
    GROUP BY o.보고코드, o.권역명, b.시작일),
  유효 AS (       -- 빈칸 = 0%로 볼 수 있는 보고·권역
    SELECT r.보고코드, r.권역명
    FROM 보고권역 r
    WHERE r.값있음 = 1
       OR (EXISTS (SELECT 1 FROM 보고권역 e WHERE e.권역명 = r.권역명 AND YEAR(e.시작일) = YEAR(r.시작일)
                    AND e.시작일 < r.시작일 AND e.값있음 = 1)
           AND EXISTS (SELECT 1 FROM 보고권역 e WHERE e.권역명 = r.권역명 AND YEAR(e.시작일) = YEAR(r.시작일)
                    AND e.시작일 > r.시작일 AND e.값있음 = 1))),
  피벗 AS (
    SELECT o.보고코드, o.권역명, b.시작일,
           MAX(CASE WHEN o.어종명 = '노무라입깃해파리' THEN o.출현율 END) AS 노무라,
           MAX(CASE WHEN o.어종명 = '보름달물해파리'   THEN o.출현율 END) AS 보름달,
           MAX(CASE WHEN o.어종명 = '기타해파리'       THEN o.출현율 END) AS 기타
    FROM 출현기록 o JOIN 주간보고 b ON o.보고코드 = b.보고코드
    GROUP BY o.보고코드, o.권역명, b.시작일),
  통합 AS (   -- 빈칸 규칙 ①②에 해당하면 빈칸 = 0%, 아니면 결측
    SELECT p.보고코드, p.권역명, p.시작일,
           CASE WHEN v.보고코드 IS NULL THEN NULL ELSE COALESCE(p.노무라, 0) END AS 노무라,
           CASE WHEN v.보고코드 IS NULL THEN NULL ELSE COALESCE(p.보름달, 0) END AS 보름달,
           CASE WHEN v.보고코드 IS NULL THEN NULL ELSE COALESCE(p.기타, 0) END AS 기타,
           CASE WHEN v.보고코드 IS NULL THEN NULL
                ELSE ROUND(100 * (1 - (1 - COALESCE(p.노무라, 0) / 100) * (1 - COALESCE(p.보름달, 0) / 100)
                                    * (1 - COALESCE(p.기타, 0) / 100)), 2) END AS 통합
    FROM 피벗 p LEFT JOIN 유효 v ON v.보고코드 = p.보고코드 AND v.권역명 = p.권역명),
  평년 AS (   -- 수온 평년은 학습기간(2014~2020)만 사용 (검증·테스트 정보 누수 방지)
    SELECT 관측소ID,
           MONTH(DATE_ADD(시작일, INTERVAL FLOOR(DATEDIFF(LEAST(DATE_ADD(시작일, INTERVAL 6 - WEEKDAY(시작일) DAY), DATE(CONCAT(YEAR(시작일), '-12-31'))), 시작일) / 2) DAY)) AS 월,
           LEAST(4, FLOOR((DAY(DATE_ADD(시작일, INTERVAL FLOOR(DATEDIFF(LEAST(DATE_ADD(시작일, INTERVAL 6 - WEEKDAY(시작일) DAY), DATE(CONCAT(YEAR(시작일), '-12-31'))), 시작일) / 2) DAY)) - 1) / 7) + 1) AS 주차,
           AVG(수온) AS 수온평년
    FROM 관측자료 WHERE 연도 <= 2020 GROUP BY 1, 2, 3),
  기본 AS (
    SELECT s.보고코드, s.권역명, s.시작일, YEAR(s.시작일) AS 연도,
           MONTH(DATE_ADD(s.시작일, INTERVAL 3 DAY)) AS 월, WEEK(DATE_ADD(s.시작일, INTERVAL 3 DAY), 3) AS 연중주차,
           s.노무라, s.보름달, s.기타, s.통합,
           (SELECT n.통합 FROM 통합 n WHERE n.권역명 = s.권역명 AND DATEDIFF(s.시작일, n.시작일) BETWEEN 4 AND 10
             ORDER BY ABS(DATEDIFF(s.시작일, n.시작일) - 7), n.보고코드 DESC LIMIT 1) AS 통합_1주전,
           (SELECT n.통합 FROM 통합 n WHERE n.권역명 = s.권역명 AND DATEDIFF(s.시작일, n.시작일) BETWEEN 11 AND 17
             ORDER BY ABS(DATEDIFF(s.시작일, n.시작일) - 14), n.보고코드 DESC LIMIT 1) AS 통합_2주전,
           r.대표관측소ID AS 관측소ID, ob.수온 AS 수온_주평균, ob.수온 - pn.수온평년 AS 수온_평년차,
           ob.기온 AS 기온_주평균, ob.풍속 AS 풍속_주평균, ob.유의파고 AS 유의파고_주평균,
           (SELECT n.통합 FROM 통합 n WHERE n.권역명 = s.권역명 AND DATEDIFF(n.시작일, s.시작일) BETWEEN 4 AND 10
             ORDER BY ABS(DATEDIFF(n.시작일, s.시작일) - 7), n.보고코드 DESC LIMIT 1) AS 통합_1주후,
           (SELECT n.통합 FROM 통합 n WHERE n.권역명 = s.권역명 AND DATEDIFF(n.시작일, s.시작일) BETWEEN 11 AND 17
             ORDER BY ABS(DATEDIFF(n.시작일, s.시작일) - 14), n.보고코드 DESC LIMIT 1) AS 통합_2주후,
           (SELECT n.통합 FROM 통합 n WHERE n.권역명 = s.권역명 AND DATEDIFF(n.시작일, s.시작일) BETWEEN 25 AND 31
             ORDER BY ABS(DATEDIFF(n.시작일, s.시작일) - 28), n.보고코드 DESC LIMIT 1) AS 통합_4주후
    FROM 통합 s
    JOIN 권역 r ON s.권역명 = r.권역명
    LEFT JOIN 관측자료 ob ON ob.관측소ID = r.대표관측소ID
         AND DATE_ADD(s.시작일, INTERVAL 3 DAY) BETWEEN ob.시작일 AND LEAST(DATE_ADD(ob.시작일, INTERVAL 6 - WEEKDAY(ob.시작일) DAY), DATE(CONCAT(YEAR(ob.시작일), '-12-31')))
    LEFT JOIN 평년 pn ON pn.관측소ID = r.대표관측소ID
         AND pn.월 = MONTH(DATE_ADD(s.시작일, INTERVAL 3 DAY))
         AND pn.주차 = LEAST(4, FLOOR((DAY(DATE_ADD(s.시작일, INTERVAL 3 DAY)) - 1) / 7) + 1)
    WHERE s.통합 IS NOT NULL)
SELECT 기본.*,
       통합 - 통합_1주전 AS 통합_변화_1주,
       CASE WHEN 통합 >= 50 OR 통합_1주후 IS NULL THEN NULL WHEN 통합_1주후 >= 50 THEN 1 ELSE 0 END AS 타깃_급증_1주후,
       CASE WHEN 통합 >= 50 OR 통합_2주후 IS NULL THEN NULL WHEN 통합_2주후 >= 50 THEN 1 ELSE 0 END AS 타깃_급증_2주후,
       CASE WHEN 통합 >= 50 OR 통합_4주후 IS NULL THEN NULL WHEN 통합_4주후 >= 50 THEN 1 ELSE 0 END AS 타깃_급증_4주후,
       CASE WHEN 연도 <= 2020 THEN 'train' WHEN 연도 = 2021 THEN 'valid' WHEN 연도 <= 2023 THEN 'test' ELSE '추가(2024)' END AS 분할
FROM 기본;

-- 7) 해수욕장 예측 위험 지수: 권역예측(모델 결과) x 해수욕장 가중치
--    급증확률은 "권역이 k주 뒤 대량출현으로 바뀔 확률", 가중치는 "목격 빈도의 지역 배율"이므로
--    둘을 곱한 값은 확률이 아니라 해수욕장 간 상대 비교용 지수로만 사용한다
--    예측위험지수는 1을 넘으면 1로 제한(표시용), 정렬지수는 제한 전 값(순위 정렬용, 1.0 동점 방지)
CREATE OR REPLACE VIEW v_해수욕장예측위험도 AS
SELECT h.해수욕장ID, h.해수욕장명, g.시도명, g.시군명, p.권역명, p.기준일, p.예측기간, p.모델명,
       p.급증확률 AS 권역급증확률, w.가중치,
       ROUND(LEAST(1, p.급증확률 * w.가중치), 4) AS 예측위험지수,
       ROUND(p.급증확률 * w.가중치, 4) AS 정렬지수
FROM 권역예측 p
JOIN 시군 g             ON g.권역명 = p.권역명
JOIN 해수욕장 h         ON h.시군ID = g.시군ID
JOIN v_해수욕장가중치 w ON w.해수욕장ID = h.해수욕장ID;
