"""DB 접속 정보·인증키·공통 함수 (모든 스크립트가 여기서 읽음)

비밀번호·인증키는 이 파일이 아니라 같은 폴더의 .env 파일에 둔다 (.env는 GitHub에 올라가지 않음).
  - 내 PC: 02_웹_수집\\.env 를 읽음 (형식은 .env.example 참고)
  - 배포 서버(Render): 화면에서 넣은 환경변수를 읽음
  - .env의 MYSQL_HOST 등을 클라우드 DB로 바꾸면 수집·예측·웹이 모두 클라우드 DB를 씀
"""
import datetime as dt
import glob
import os
import shutil
import subprocess
from decimal import Decimal

import pandas as pd
import pymysql

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)                       # 엔지니어링DB_프로젝트 폴더
BACKUP_DIR = os.path.join(PROJECT, "백업")


def _env_읽기(path):
    """KEY=값 형식의 .env를 읽어 환경변수로 둔다 (이미 있는 환경변수가 우선)"""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_env_읽기(os.path.join(HERE, ".env"))

DB = dict(host=os.environ.get("MYSQL_HOST", "localhost"),
          port=int(os.environ.get("MYSQL_PORT", "3306")),
          user=os.environ.get("MYSQL_USER", "root"),
          password=os.environ.get("MYSQL_PWD", ""),
          database=os.environ.get("MYSQL_DB", "jellyfish"), charset="utf8mb4")

# 클라우드 DB는 암호화(SSL) 연결 필수 → CA 인증서 경로 (02_웹_수집 기준 상대경로 가능)
#   "system" = 공인 인증서 묶음 사용 (TiDB Cloud처럼 공인 인증서를 쓰는 DB)
def _ca_경로(v):
    if not v:
        return ""
    if v.lower() == "system":
        import certifi
        return certifi.where()
    return v if os.path.isabs(v) else os.path.join(HERE, v)


SSL_CA = _ca_경로(os.environ.get("MYSQL_SSL_CA", ""))
if SSL_CA:
    DB["ssl"] = {"ca": SSL_CA}

NIFS_KEY = os.environ.get("NIFS_KEY", "")   # 국립수산과학원 OpenAPI 인증키
KMA_KEY = os.environ.get("KMA_KEY", "")     # 기상청 API허브 인증키
WEB_RELOAD_URL = os.environ.get("WEB_RELOAD_URL", "")   # 배포한 웹의 "DB 다시 불러오기" 주소 (update_all.py가 마지막에 호출)

# 머신러닝(신효섭) 서비스 폴더: 서비스_예측.py가 있는 곳. 비워 두면 update_all.py가 예측 단계를 건너뜀
ML_DIR = os.environ.get("ML_DIR", os.path.join(PROJECT, "03_머신러닝", "서비스"))


def 조회(sql, params=None):
    """SELECT 결과를 DataFrame으로 돌려준다."""
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    finally:
        conn.close()
    df = pd.DataFrame(rows)
    for c in df.columns:                      # DECIMAL → float (계산·그래프용)
        if df[c].map(lambda v: isinstance(v, Decimal)).any():
            df[c] = df[c].astype(float)
    return df


def mysql_도구(name):
    """mysqldump / mysql 실행 파일 경로"""
    exe = shutil.which(name) or next(iter(sorted(glob.glob(
        rf"C:\Program Files\MySQL\MySQL Server *\bin\{name}.exe"), reverse=True)), None)
    if not exe:
        raise FileNotFoundError(f"{name}를 찾을 수 없어요 (MySQL Server bin 폴더 확인)")
    return exe


def 접속_옵션(db=None):
    """mysql·mysqldump 명령줄 공통 옵션 (비밀번호는 환경변수 MYSQL_PWD로 넘김)"""
    db = db or DB
    opt = ["-h", db["host"], "-P", str(db["port"]), "-u", db["user"], "--default-character-set=utf8mb4"]
    if db.get("ssl"):
        opt += ["--ssl-mode=VERIFY_CA", f"--ssl-ca={db['ssl']['ca']}"]
    return opt


def 백업():
    """mysqldump로 jellyfish 전체를 백업\\jellyfish_YYYYMMDD_HHMM.sql 에 저장하고 경로를 돌려준다."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    out = os.path.join(BACKUP_DIR, f"jellyfish_{dt.datetime.now():%Y%m%d_%H%M}.sql")
    env = dict(os.environ, MYSQL_PWD=DB["password"])   # 비밀번호를 명령줄에 쓰지 않음
    if DB["host"] in ("localhost", "127.0.0.1"):
        extra = ["--single-transaction", "--routines", "--triggers"]
    else:   # 클라우드 DB(TiDB): 지원하지 않는 기능은 끔 (SAVEPOINT·테이블 잠금 없음, 이 DB에는 프로시저·트리거도 없음)
        extra = ["--set-gtid-purged=OFF", "--no-tablespaces", "--column-statistics=0", "--skip-add-locks",
                 "--skip-lock-tables", "--skip-routines", "--skip-triggers"]
    try:
        subprocess.run([mysql_도구("mysqldump")] + 접속_옵션() + extra +
                       [f"--result-file={out}", DB["database"]], env=env, check=True)
    except Exception:
        if os.path.exists(out):
            os.remove(out)                            # 실패한 반쪽 백업은 남기지 않음
        raise
    return out
