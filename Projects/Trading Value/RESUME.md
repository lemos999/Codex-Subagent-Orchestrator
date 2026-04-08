# Trading Value - Session Resume Guide

> 새 세션에서 이 파일과 `limits-history.md`를 반드시 읽는다.

## 미션
**최고 수익률 달성 (상한 없음).** 한계를 두지 않는다.

## 현재 상태: 5,000 Variant Tournament (2026-04-08~)

5,000개 전략 변형이 실시간 시장에서 경쟁 중.
- 9종목 (ETH/BTC/SOL/XRP/NVDA/AMZN/TSLA/GOOGL/QQQ)
- 7전략 (trend_long/trend_both/mean_revert/breakout/grid/mom_rotation/pair)
- 6시간축 (1m/5m/15m/1h/4h/daily)
- 15차원 파라미터
- CTS 순위 (Calmar 35% + Sortino 25% + Consistency 20% + DSR 10% + Freq 10%)
- 대시보드: http://localhost:8895

## 데이터 쌓인 후 다음 단계

### 1. 현재 상태 확인
```bash
curl -s http://localhost:8895/api/state | py -3.12 -m json.tool
cat data/effectiveness.jsonl | tail -5
```

### 2. 결과 분석
- 대시보드에서 READY / APPROACHING 상태 확인
- 상위 10개 변형: 어떤 종목 x 전략 x 시간축이 가장 효과적인가
- 파라미터 히트맵: 어떤 파라미터가 수익과 상관 있는가
- 69초 틱 차트: 목표 근접도 추세

### 3. 성공 시 (상위 앙상블 수익 > 0%)
- 상위 20개 앙상블 구성 → inverse-variance 가중
- 페이퍼 → 실전 전환 논의
- 80/15/5 자본 배분 적용

### 4. 실패 시 (2개월 후 수익 0% 이하) — 다음 플랜
- **Plan B**: 외부 데이터 알파 (온체인, 센티먼트, 매크로, 옵션 IV)
- **Plan C**: 시장 변경 (한국 주식, FX, 원자재)
- **Plan D**: 전략 구조 전환 (차익거래, 마켓 메이킹, 옵션, 이벤트)
- **Plan E**: 토너먼트 데이터 자체가 자산 ("무엇이 안 되는지"의 증거)

## 정신
`limits-history.md` 참조. 8번의 한계를 돌파해왔다. 다음 한계도 넘는다.
`breakthrough-guide.md` 참조. 한계 돌파 5원칙 + 프로토콜.

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `scripts/tournament.py` | 메인 실행 (5,000 토너먼트 + 대시보드) |
| `scripts/start_paper.bat` | Windows 자동 시작 |
| `data/tournament_state.npz` | 상태 저장 (1시간마다) |
| `data/effectiveness.jsonl` | 69초 틱 로그 (영구) |
| `limits-history.md` | 한계 돌파 기록 |
| `breakthrough-guide.md` | 한계 돌파 지침서 |
| `html/strategy-overview.html` | 전략 시각화 |

## 실행

```bash
cd "Projects/Trading Value"
py -3.12 -u scripts/tournament.py
```
