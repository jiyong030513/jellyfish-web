-- 해파리 대량출현 조기경보 DB : 테이블 11개 (MySQL 8.0)
CREATE DATABASE IF NOT EXISTS jellyfish DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE jellyfish;

DROP TABLE IF EXISTS 권역예측, 설문응답, 설문지점, 출현기록, 어종, 주간보고, 관측자료, 해수욕장, 시군, 권역, 관측소;

CREATE TABLE 관측소 (
  관측소ID   INT          PRIMARY KEY,           -- 기상청 지점번호
  관측소명   VARCHAR(20)  NOT NULL,
  해역       VARCHAR(5)   NOT NULL,
  위도       DECIMAL(9,6) NOT NULL,
  경도       DECIMAL(9,6) NOT NULL
);

CREATE TABLE 권역 (
  권역명       VARCHAR(10) PRIMARY KEY,
  해역         VARCHAR(5)  NOT NULL,
  대표관측소ID INT         NOT NULL,
  FOREIGN KEY (대표관측소ID) REFERENCES 관측소(관측소ID)
);

CREATE TABLE 시군 (
  시군ID  INT         PRIMARY KEY,
  시도명  VARCHAR(20) NOT NULL,
  시군명  VARCHAR(20) NOT NULL,
  권역명  VARCHAR(10) NOT NULL,
  UNIQUE (시도명, 시군명),                         -- 강원 고성군 / 경남 고성군 구분
  FOREIGN KEY (권역명) REFERENCES 권역(권역명)
);

CREATE TABLE 해수욕장 (
  해수욕장ID    CHAR(4)      PRIMARY KEY,
  해수욕장명    VARCHAR(30)  NOT NULL,
  시군ID        INT          NOT NULL,
  위도          DECIMAL(9,6) NOT NULL,
  경도          DECIMAL(9,6) NOT NULL,
  길이          INT,
  너비          INT,
  관측소ID      INT          NOT NULL,
  관측소거리km  DECIMAL(6,1),                       -- 유도 속성 (좌표로 계산, 성능을 위해 저장)
  FOREIGN KEY (시군ID)   REFERENCES 시군(시군ID),
  FOREIGN KEY (관측소ID) REFERENCES 관측소(관측소ID)
);

CREATE TABLE 관측자료 (
  관측ID    CHAR(6) PRIMARY KEY,
  관측소ID  INT     NOT NULL,
  연도      SMALLINT NOT NULL,
  주차      TINYINT  NOT NULL,
  시작일    DATE     NOT NULL,
  -- 종료일은 시작일로 계산되는 유도 속성이라 저장하지 않음
  -- (그 주 일요일, 단 연말을 넘지 않음: LEAST(시작일 + (6 - WEEKDAY(시작일))일, 그해 12월 31일))
  풍속 DECIMAL(6,3), 풍향 DECIMAL(6,1), 최대돌풍 DECIMAL(6,3), 기압 DECIMAL(7,2), 습도 DECIMAL(6,2),
  기온 DECIMAL(6,3), 수온 DECIMAL(6,3), 최대파고 DECIMAL(6,3), 유의파고 DECIMAL(6,3), 평균파고 DECIMAL(6,3),
  파주기 DECIMAL(6,3), 파향 DECIMAL(6,1),
  -- 최대돌풍 60 m/s 초과 값은 측정 오류로 보고 NULL로 적재
  -- 포항(22106) 2018-12-10 주 수온 1.8℃는 앞뒤 주(15.5·16.2℃)와 동떨어진 측정 오류로 보고 NULL로 적재
  UNIQUE (관측소ID, 연도, 주차),
  UNIQUE (관측소ID, 시작일),
  FOREIGN KEY (관측소ID) REFERENCES 관측소(관측소ID)
);

CREATE TABLE 주간보고 (
  보고코드  VARCHAR(20) PRIMARY KEY,
  시작일    DATE NOT NULL,
  종료일    DATE NOT NULL,
  조사인원  INT,
  응답인원  INT
);

CREATE TABLE 어종 (
  어종명  VARCHAR(20) PRIMARY KEY,
  독성    VARCHAR(10)
);

CREATE TABLE 출현기록 (                              -- 3항 관계 "출현" 변환
  보고코드  VARCHAR(20)  NOT NULL,
  권역명    VARCHAR(10)  NOT NULL,
  어종명    VARCHAR(20)  NOT NULL,
  출현율    DECIMAL(5,2) NULL CHECK (출현율 BETWEEN 0 AND 100),  -- NULL = 응답 없음
  PRIMARY KEY (보고코드, 권역명, 어종명),
  FOREIGN KEY (보고코드) REFERENCES 주간보고(보고코드),
  FOREIGN KEY (권역명)   REFERENCES 권역(권역명),
  FOREIGN KEY (어종명)   REFERENCES 어종(어종명)
);

CREATE TABLE 설문지점 (
  지점ID    INT          PRIMARY KEY,
  지점명    VARCHAR(100) NOT NULL,                  -- 설문 원문 위치
  시군ID    INT          NULL,                      -- 분류 불가(해구 번호 등)는 NULL
  위도      DECIMAL(9,6) NULL,
  경도      DECIMAL(9,6) NULL,
  좌표방법  VARCHAR(30),
  FOREIGN KEY (시군ID) REFERENCES 시군(시군ID)
);

CREATE TABLE 설문응답 (
  응답ID    INT         PRIMARY KEY,
  지점ID    INT         NULL,                       -- 조업하지 않음 등 위치 미기재는 NULL
  응답일자  DATETIME    NOT NULL,
  조사연도  SMALLINT    NOT NULL,
  조사주차  TINYINT     NOT NULL,
  목격여부  VARCHAR(10) NOT NULL CHECK (목격여부 IN ('보았음', '보지 못했음', '조업하지 않았음')),
  FOREIGN KEY (지점ID) REFERENCES 설문지점(지점ID)
);

CREATE TABLE 권역예측 (                              -- 약한 개체 (권역에 종속)
  권역명    VARCHAR(10)  NOT NULL,
  기준일    DATE         NOT NULL,
  예측기간  TINYINT      NOT NULL CHECK (예측기간 IN (1, 2, 4)),   -- 몇 주 뒤
  모델명    VARCHAR(30)  NOT NULL,
  급증확률  DECIMAL(5,4) NOT NULL CHECK (급증확률 BETWEEN 0 AND 1),
  PRIMARY KEY (권역명, 기준일, 예측기간, 모델명),
  FOREIGN KEY (권역명) REFERENCES 권역(권역명) ON DELETE CASCADE
);
