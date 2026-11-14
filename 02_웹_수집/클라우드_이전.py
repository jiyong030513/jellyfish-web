"""내 PC의 jellyfish DB를 클라우드 DB(TiDB Cloud, MySQL 호환)로 그대로 옮긴다 (처음 배포할 때 한 번).

준비: .env에 아래 값을 채움 (TiDB Cloud 클러스터 화면의 Connect)
    CLOUD_MYSQL_HOST=gateway01.ap-southeast-1.prod.aws.tidbcloud.com
    CLOUD_MYSQL_PORT=4000
    CLOUD_MYSQL_USER=xxxxxxxx.root
    CLOUD_MYSQL_PWD=...
    CLOUD_MYSQL_SSL_CA=system        (공인 인증서 사용. 인증서 파일이면 경로)
실행:  python 클라우드_이전.py
  1) 내 PC DB를 mysqldump (백업 폴더에 저장)
  2) 뷰의 DEFINER(root@localhost) 제거 → 클라우드 계정으로 만들 수 있게
  3) 클라우드에 jellyfish DB를 만들고 그대로 적재 (테이블 구조·뷰·데이터 동일)
  4) 양쪽 테이블·뷰 행 수 비교
클라우드에 이미 jellyfish가 있으면 테이블을 지우고 다시 만든다 (덤프에 DROP TABLE IF EXISTS 포함).
"""
import datetime as dt
import os
import re
import subprocess
import sys

import pymysql

from db import BACKUP_DIR, DB, _ca_경로, mysql_도구, 접속_옵션

LOCAL = dict(DB, host="localhost", port=int(os.environ.get("LOCAL_MYSQL_PORT", "3306")),
             user=os.environ.get("LOCAL_MYSQL_USER", "root"),
             password=os.environ.get("LOCAL_MYSQL_PWD", DB["password"] if DB["host"] == "localhost" else ""))
LOCAL.pop("ssl", None)


def 클라우드_정보():
    need = ["CLOUD_MYSQL_HOST", "CLOUD_MYSQL_PORT", "CLOUD_MYSQL_USER", "CLOUD_MYSQL_PWD", "CLOUD_MYSQL_SSL_CA"]
    miss = [k for k in need if not os.environ.get(k)]
    if miss:
        sys.exit(f"[멈춤] .env에 {', '.join(miss)} 값을 채워 주세요.")
    ca = _ca_경로(os.environ["CLOUD_MYSQL_SSL_CA"])
    if not os.path.exists(ca):
        sys.exit(f"[멈춤] CA 인증서 파일이 없어요: {ca}")
    return dict(host=os.environ["CLOUD_MYSQL_HOST"], port=int(os.environ["CLOUD_MYSQL_PORT"]),
                user=os.environ["CLOUD_MYSQL_USER"], password=os.environ["CLOUD_MYSQL_PWD"],
                database="jellyfish", charset="utf8mb4", ssl={"ca": ca})


def 행수(info, db_exists=True):
    conn = pymysql.connect(**info)
    try:
        with conn.cursor() as c:
            c.execute("SELECT TABLE_NAME, TABLE_TYPE FROM information_schema.TABLES "
                      "WHERE TABLE_SCHEMA = %s ORDER BY TABLE_TYPE, TABLE_NAME", (info["database"],))
            out = {}
            for name, kind in c.fetchall():
                c.execute(f"SELECT COUNT(*) FROM `{name}`")
                out[name] = (kind, c.fetchone()[0])
            return out
    finally:
        conn.close()


def main():
    cloud = 클라우드_정보()

    print("1) 내 PC DB 내보내기 (mysqldump, 테이블과 데이터만)")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dump = os.path.join(BACKUP_DIR, f"jellyfish_클라우드이전_{dt.datetime.now():%Y%m%d_%H%M}.sql")
    conn = pymysql.connect(**LOCAL)
    with conn.cursor() as c:
        c.execute("SELECT TABLE_NAME FROM information_schema.VIEWS WHERE TABLE_SCHEMA = 'jellyfish'")
        views = [r[0] for r in c.fetchall()]
    conn.close()
    subprocess.run([mysql_도구("mysqldump")] + 접속_옵션(LOCAL) +
                   ["--single-transaction", "--skip-triggers", "--set-gtid-purged=OFF", "--no-tablespaces",
                    "--skip-add-locks", f"--result-file={dump}", "jellyfish"],
                   env=dict(os.environ, MYSQL_PWD=LOCAL["password"]), check=True)
    # 뷰 부분은 덤프에서 뺌 (MySQL이 다시 적은 뷰 SQL을 TiDB가 못 읽음 → 원본 SQL2로 다시 만듦)
    # (윈도우에서는 한글 뷰 이름이 --ignore-table로 전달되지 않아 파일에서 직접 지움)
    sql = open(dump, encoding="utf-8").read()
    parts = re.split(r"(?=\n--\n-- )", sql)
    sql = "".join(p for p in parts if not re.match(r"\n--\n-- (Temporary view structure|Final view structure)", p))
    open(dump, "w", encoding="utf-8").write(sql)

    print(f"2) 클라우드에 테이블·데이터 적재: {cloud['host']}")
    boot = dict(cloud, database=None)
    conn = pymysql.connect(**{k: v for k, v in boot.items() if v is not None})
    with conn.cursor() as c:
        c.execute("CREATE DATABASE IF NOT EXISTS jellyfish DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        for v in views:                                   # 이전 시도에서 남은 뷰 정리
            c.execute(f"DROP VIEW IF EXISTS jellyfish.`{v}`")
    conn.close()
    env = dict(os.environ, MYSQL_PWD=cloud["password"])
    with open(dump, "rb") as f:
        subprocess.run([mysql_도구("mysql")] + 접속_옵션(cloud) + ["jellyfish"], stdin=f, env=env, check=True)

    print("3) 뷰 7개는 원본 SQL2_views.sql을 그대로 실행해 만듦")
    sql2 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "엔디비_최종테이블_10", "SQL2_views.sql")
    # TiDB에는 공간 함수(ST_Distance_Sphere, POINT)가 없음 → MySQL과 같은 하버사인 공식(지구 반지름 6,370,986m)으로 바꿔 실행
    #  (원본 SQL2 파일은 그대로 두고 클라우드에 보낼 때만 바꿈)
    거리식 = ("(2 * 6370986 * ASIN(SQRT(POW(SIN(RADIANS(a.위도 - h.위도) / 2), 2) + "
             "COS(RADIANS(h.위도)) * COS(RADIANS(a.위도)) * POW(SIN(RADIANS(a.경도 - h.경도) / 2), 2))))")
    원본 = "ST_Distance_Sphere(POINT(h.경도, h.위도), POINT(a.경도, a.위도))"
    s2 = open(sql2, encoding="utf-8").read()
    if 원본 not in s2:
        sys.exit("[멈춤] SQL2의 거리 계산식이 예상과 달라요")
    s2 = s2.replace(원본, 거리식)
    subprocess.run([mysql_도구("mysql")] + 접속_옵션(cloud) + ["jellyfish"], input=s2.encode("utf-8"), env=env, check=True)

    print("4) 행 수 비교 (내 PC / 클라우드)")
    a, b = 행수(LOCAL), 행수(cloud)
    ok = True
    for name in a:
        same = name in b and a[name][1] == b[name][1]
        ok &= same
        print(f"   {'뷰  ' if a[name][0] == 'VIEW' else '테이블'} {name:<16} {a[name][1]:>7,} / {b.get(name, ('', '없음'))[1]:>7}  {'같음' if same else '다름!'}")
    print("\n완료: 모두 같아요." if ok else "\n[확인 필요] 다른 항목이 있어요.")
    print("이제 .env의 MYSQL_HOST·PORT·USER·PWD·SSL_CA를 CLOUD_ 값으로 바꾸면 수집·예측·웹이 클라우드 DB를 써요.")


if __name__ == "__main__":
    main()
