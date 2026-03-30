# Telegram Digest 설치 완료

## 구성
- Python 3.12 + Telethon (메시지 수집) + Ollama qwen2.5:14b (요약)
- 봇으로 전송 (Digest-bot → 일반 채팅으로 도착)
- 20분 간격 자동 실행
- Windows 시작 시 자동 실행 (Startup 폴더)

## 파일 구조
- `main.py` — 메인 루프 (수집 → 요약 → 전송, 자동 재연결)
- `fetcher.py` — 텔레그램 메시지 수집 (그룹/채널/1:1)
- `summarizer.py` — Ollama 기반 주제별 요약 (팩트/의견 구분)
- `diagnose.py` — 자동 진단 및 복구 (3회 실패 시 실행)
- `start_digest.bat` — 실행 스크립트 (3회 재시작 + 진단)
- `config.yaml` — 설정 (API 키, 봇 토큰, 모델, 간격)
- `state.json` — 마지막 수집 시점 기록 (자동 생성)

## 수동 실행
```
py -3.12 "C:\Users\haj\projects\subagent-orchestrator\Projects\telegram-digest\main.py"
```
