"""React 버전 실행: 백엔드(FastAPI) + 프론트엔드(Vite)를 같이 켜고 브라우저를 연다.

    python run.py           (04_웹_react 폴더에서, 또는 VS Code ▶ 버튼)

- 처음 한 번은 frontend 폴더에 npm install을 자동으로 함 (Node.js 필요)
- 끌 때는 Ctrl + C 한 번 → 둘 다 꺼짐
- 주소: http://localhost:5173   (API: http://127.0.0.1:8000/docs)
"""
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
BACK = os.path.join(HERE, "backend")
FRONT = os.path.join(HERE, "frontend")
API_PORT, WEB_PORT = 8000, 5173
WIN = os.name == "nt"
# 자식 프로세스는 Ctrl+C를 직접 받지 않게 따로 묶음 → 여기서 한 번에 정리 ("일괄 작업을 끝내시겠습니까?" 질문 없음)
FLAGS = subprocess.CREATE_NEW_PROCESS_GROUP if WIN else 0


def 열림(url):
    try:
        urllib.request.urlopen(url, timeout=1)
        return True
    except Exception:
        return False


def 끄기(p):
    if p and p.poll() is None:
        if WIN:
            subprocess.call(["taskkill", "/T", "/F", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            p.terminate()


def main():
    if not shutil.which("node"):
        print("Node.js가 없어요. https://nodejs.org 에서 LTS를 설치하고 VS Code를 다시 켜 주세요.")
        return 1
    for port, name in [(API_PORT, "백엔드"), (WEB_PORT, "프론트엔드")]:
        if 열림(f"http://127.0.0.1:{port}") or 열림(f"http://localhost:{port}"):
            print(f"[멈춤] {port}번 포트를 이미 다른 프로그램이 쓰고 있어요 ({name}). 이전에 켠 run.py 창을 먼저 끄세요.")
            return 1
    if not os.path.exists(os.path.join(FRONT, "node_modules", "vite")):
        print("처음 실행이라 프론트엔드 패키지를 설치해요 (1~2분)…")
        if subprocess.call("npm install --no-fund --no-audit", cwd=FRONT, shell=True) != 0:
            print("npm install 실패")
            return 1

    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", FRONT_PORT=str(WEB_PORT))
    print("백엔드 켜는 중 (DB를 한 번 읽어 와요)…")
    back = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(API_PORT)],
                            cwd=BACK, env=env, creationflags=FLAGS)
    front = None
    try:
        for _ in range(120):                                  # 최대 60초 기다림
            if back.poll() is not None:
                print("[실패] 백엔드가 꺼졌어요. 위 오류를 확인하세요 (MySQL이 켜져 있는지, db.py 비밀번호).")
                return 1
            if 열림(f"http://127.0.0.1:{API_PORT}/api/meta"):
                break
            time.sleep(0.5)
        print("프론트엔드 켜는 중…")
        vite = os.path.join(FRONT, "node_modules", "vite", "bin", "vite.js")
        front = subprocess.Popen(["node", vite, "--port", str(WEB_PORT), "--strictPort"], cwd=FRONT, env=env, creationflags=FLAGS)
        for _ in range(60):
            if front.poll() is not None:
                print("[실패] 프론트엔드가 꺼졌어요. 위 오류를 확인하세요.")
                return 1
            if 열림(f"http://localhost:{WEB_PORT}"):
                break
            time.sleep(0.5)
        url = f"http://localhost:{WEB_PORT}"
        print(f"\n  화면: {url}\n  API : http://127.0.0.1:{API_PORT}/docs\n  끄기: Ctrl + C\n")
        if not os.environ.get("NO_BROWSER"):
            webbrowser.open(url)
        while back.poll() is None and front.poll() is None:
            time.sleep(0.5)
        print("백엔드나 프론트엔드 하나가 꺼져서 모두 끕니다.")
        return 1
    except KeyboardInterrupt:
        print("\n끄는 중…")
        return 0
    finally:
        끄기(front)
        끄기(back)
        print("백엔드·프론트엔드를 모두 껐어요.")


if __name__ == "__main__":
    sys.exit(main())
