"""매주 한 번에 갱신: 백업 → ① 해파리 주간보고 → ② 기상청 부이 → ③ 머신러닝 예측 → ④ 결과 요약

사용법 (02_웹_수집 폴더에서, 입력 없이 실행됨):
    python update_all.py

- 비밀번호·인증키·머신러닝 폴더(ML_DIR)는 db.py에서 읽음
- 시작할 때 mysqldump 백업을 한 번 만듦 (백업 폴더). 백업이나 DB 접속이 실패하면 아무것도 쓰지 않고 멈춤
- ① 해파리 수집이 실패해도 ② 부이, ③ 예측은 진행
- ③ 예측은 저장된 모델로 예측만 함 (재학습 없음). ML_DIR이 비어 있으면 건너뜀
- 화면 출력은 추가수집/갱신로그/update_YYYYMMDD_HHMM.log 에도 저장
- 끝날 때 실패한 단계가 있으면 종료 코드 1 (작업 스케줄러 "마지막 실행 결과"에서 확인 가능)
"""
import datetime as dt
import os
import subprocess
import sys
import traceback

import pymysql

from db import DB, ML_DIR, WEB_RELOAD_URL, 백업

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(HERE, "추가수집", "갱신로그")
ML_SCRIPT = "서비스_예측.py"                  # 03_머신러닝/서비스: 저장된 모델로 예측만 하고 권역예측 테이블에 저장
ML_ARGS = []                                  # 재학습 없음 (재학습은 직접 "python 서비스_예측.py --학습")


class Tee:
    """화면과 로그 파일에 동시에 출력"""
    def __init__(self, path):
        self.f = open(path, "w", encoding="utf-8")
        self.out = sys.stdout

    def write(self, s):
        self.out.write(s)
        self.f.write(s)
        self.flush()

    def flush(self):
        self.out.flush()
        self.f.flush()


def 값(sql):
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as c:
            c.execute(sql)
            return c.fetchone()[0]
    finally:
        conn.close()


def 실행(cmd, cwd):
    """하위 스크립트를 실행하고 출력을 그대로 보여 준다. 종료 코드를 돌려줌"""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout:
        print("    " + line.decode("utf-8", errors="replace").rstrip())
    return p.wait()


def 제목(t):
    print(f"\n{'=' * 60}\n{t}  ({dt.datetime.now():%H:%M:%S})\n{'=' * 60}")


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    sys.stdout = Tee(os.path.join(LOG_DIR, f"update_{dt.datetime.now():%Y%m%d_%H%M}.log"))
    결과 = {}

    # ---------------------------------------------------------- 0. 준비: DB 접속 확인 + 백업
    제목("0. 준비: DB 접속 확인 · 백업")
    try:
        보고_전 = 값("SELECT COUNT(*) FROM 주간보고")
        print(f"  DB 접속 성공 (주간보고 {보고_전}건)")
        print(f"  백업: {백업()}")
    except Exception as ex:
        print(f"  [멈춤] DB 접속 또는 백업 실패 → 아무것도 하지 않고 끝냅니다.\n  이유: {ex}")
        print("  확인: MySQL 서비스가 켜져 있는지, db.py의 비밀번호가 맞는지")
        return 1

    # ---------------------------------------------------------- 1. 해파리 주간보고
    제목("1. 해파리 주간보고 수집 (collect_reports.py)")
    try:
        code = 실행([sys.executable, os.path.join(HERE, "collect_reports.py")], HERE)
        보고_후 = 값("SELECT COUNT(*) FROM 주간보고")
        결과["해파리"] = "성공" if code == 0 else f"실패 (종료 코드 {code})"
    except Exception as ex:
        보고_후 = 값("SELECT COUNT(*) FROM 주간보고")
        결과["해파리"] = f"실패 ({ex})"
    if 결과["해파리"] != "성공":
        print(f"  [실패] {결과['해파리']} → 부이 수집과 예측은 계속 진행합니다 (위 출력에서 이유 확인)")

    # ---------------------------------------------------------- 2. 기상청 부이
    제목("2. 기상청 부이 수집 (collect_buoy.py)")
    부이 = {"새로": 0, "갱신": 0}
    try:
        import collect_buoy
        부이 = collect_buoy.run(backup=False)            # 백업은 0단계에서 이미 함
        결과["부이"] = "성공" if 부이.get("실패지점", 0) == 0 else f"일부 실패 (지점 {부이['실패지점']}곳)"
    except Exception as ex:
        traceback.print_exc(file=sys.stdout)
        결과["부이"] = f"실패 ({ex}) → DB는 rollback되어 그대로"
        print(f"  [실패] {결과['부이']} → 예측은 기존 관측자료로 계속 진행합니다")

    # ---------------------------------------------------------- 3. 머신러닝 예측
    제목(f"3. 머신러닝 예측 ({ML_SCRIPT})")
    ml_path = os.path.join(ML_DIR, ML_SCRIPT) if ML_DIR else ""
    if not ML_DIR:
        결과["예측"] = "건너뜀 (db.py의 ML_DIR이 비어 있음)"
    elif not os.path.exists(ml_path):
        결과["예측"] = f"건너뜀 ({ml_path} 없음)"
    else:
        try:
            code = 실행([sys.executable, ml_path] + ML_ARGS, ML_DIR)
            결과["예측"] = "성공" if code == 0 else f"실패 (종료 코드 {code})"
        except Exception as ex:
            결과["예측"] = f"실패 ({ex})"
    if 결과["예측"] != "성공":
        print(f"  {결과['예측']}")

    # ---------------------------------------------------------- 4. 요약
    제목("4. 결과 요약")
    try:
        최신예측 = 값("SELECT MAX(기준일) FROM 권역예측")
        최신보고 = 값("SELECT MAX(시작일) FROM 주간보고")
        최신관측 = 값("SELECT MAX(시작일) FROM 관측자료")
    except Exception as ex:
        최신예측 = 최신보고 = 최신관측 = f"(조회 실패: {ex})"
    print(f"  추가된 주간보고    : {보고_후 - 보고_전}건  (최신 보고 시작일 {최신보고})")
    print(f"  갱신된 관측 주     : {부이['새로'] + 부이['갱신']}주  (새로 {부이['새로']}, 다시 계산 {부이['갱신']}, 최신 주 {최신관측})")
    print(f"  최신 예측 기준일   : {최신예측}")
    print("  단계별 결과:")
    for k, v in 결과.items():
        print(f"    - {k}: {v}")
    print("  웹 화면에서 'DB 다시 불러오기'를 누르면 반영됩니다.")

    # 배포한 웹(Render)이 있으면 새 자료를 다시 읽게 함 (서버가 자고 있으면 깨우느라 1분쯤 걸림)
    if WEB_RELOAD_URL:
        try:
            import urllib.request
            urllib.request.urlopen(urllib.request.Request(WEB_RELOAD_URL, method="POST"), timeout=180).read()
            print(f"  배포한 웹 갱신 완료: {WEB_RELOAD_URL}")
        except Exception as ex:
            print(f"  배포한 웹 갱신 실패 (웹 화면에서 직접 'DB 다시 불러오기'를 누르세요): {ex}")
    return 0 if all(v == "성공" or v.startswith("건너뜀") for v in 결과.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
