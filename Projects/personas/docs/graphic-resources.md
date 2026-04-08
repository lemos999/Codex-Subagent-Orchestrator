# 페르소나 국가 그래픽 리소스 가이드

> 생성 도구: Gemini Nano Banana2
> 스타일: 판타지 UI + 미니멀 플랫, 다크 배경, 발광 강조
> 기본 색상: 남색(#1a237e) · 녹색(#2e7d32) · 보라(#6a1b9a) · 금색(#ffd700)
> 해상도: 512×512 (아이콘), 1024×512 (배너), 1024×1024 (일러스트)
> 저장 경로: `Projects/personas/dashboard/public/assets/`
> 파일 형식: PNG (투명 배경)

---

## 파일명 매핑 전체 목록

### 국가 상징 (3종)
| # | 리소스 | 파일명 | 해상도 |
|---|---|---|---|
| 1 | WILL 코인 아이콘 | `will-coin.png` | 512×512 |
| 2 | 국장 (엠블럼) | `nation-emblem.png` | 1024×1024 |
| 3 | 국기 | `nation-flag.png` | 1024×682 |

### 3권역 엠블럼 (3종)
| # | 리소스 | 파일명 | 해상도 |
|---|---|---|---|
| 4 | 클로드 자치령 | `region-claude.png` | 512×512 |
| 5 | 코덱스 공화국 | `region-codex.png` | 512×512 |
| 6 | 제미니 연합 | `region-gemini.png` | 512×512 |

### 클래스 아이콘 (10종)
| # | 리소스 | 파일명 | 해상도 |
|---|---|---|---|
| 7 | Class 1 초심자 | `class-01-initiate.png` | 256×256 |
| 8 | Class 2 수행자 | `class-02-practitioner.png` | 256×256 |
| 9 | Class 3 숙련자 | `class-03-adept.png` | 256×256 |
| 10 | Class 4 달인 | `class-04-virtuoso.png` | 256×256 |
| 11 | Class 5 대가 | `class-05-master.png` | 256×256 |
| 12 | Class 6 현자 | `class-06-sage.png` | 256×256 |
| 13 | Class 7 초월자 | `class-07-transcendent.png` | 256×256 |
| 14 | Class 8 경이 | `class-08-paragon.png` | 256×256 |
| 15 | Class 9 전설 | `class-09-legend.png` | 256×256 |
| 16 | Class EX 신격 | `class-10-divine.png` | 256×256 |

### 경지 배지 (5종)
| # | 리소스 | 파일명 | 해상도 |
|---|---|---|---|
| 17 | 숙련의 길 | `tier-adept.png` | 256×64 |
| 18 | 대가의 경지 | `tier-master.png` | 256×64 |
| 19 | 천재의 영역 | `tier-genius.png` | 256×64 |
| 20 | 전설 | `tier-legend.png` | 256×64 |
| 21 | 신격 | `tier-divine.png` | 256×64 |

### 유형 아이콘 (5종)
| # | 리소스 | 파일명 | 해상도 |
|---|---|---|---|
| 22 | 관리형 (방패) | `type-management.png` | 128×128 |
| 23 | 창작형 (붓) | `type-creative.png` | 128×128 |
| 24 | 전략형 (체스말) | `type-strategic.png` | 128×128 |
| 25 | 검증형 (돋보기) | `type-verification.png` | 128×128 |
| 26 | 범용형 (별) | `type-general.png` | 128×128 |

### 4개의 벽 일러스트 (4종)
| # | 리소스 | 파일명 | 해상도 |
|---|---|---|---|
| 27 | 일반의 벽 (3→4) | `wall-normal.png` | 512×256 |
| 28 | 대가의 벽 (6→7) | `wall-master.png` | 512×256 |
| 29 | 전설의 벽 (8→9) | `wall-legend.png` | 512×256 |
| 30 | 신의 벽 (9→EX) | `wall-divine.png` | 512×256 |

### 수도 일러스트 (4종)
| # | 리소스 | 파일명 | 해상도 |
|---|---|---|---|
| 31 | 서림 (클로드 수도) | `city-seorim.png` | 1024×512 |
| 32 | 포지 (코덱스 수도) | `city-forge.png` | 1024×512 |
| 33 | 비스타 (제미니 수도) | `city-vista.png` | 1024×512 |
| 34 | 국가 수도 | `city-capital.png` | 1024×512 |

### 카드 프레임 (5종)
| # | 리소스 | 파일명 | 해상도 |
|---|---|---|---|
| 35 | 1~3클래스 은색 | `frame-silver.png` | 384×512 |
| 36 | 4~6클래스 금색 | `frame-gold.png` | 384×512 |
| 37 | 7~8클래스 보라 | `frame-purple.png` | 384×512 |
| 38 | 9클래스 순백 | `frame-white.png` | 384×512 |
| 39 | EX 신격 | `frame-divine.png` | 384×512 |

### 관계 아이콘 (6종)
| # | 리소스 | 파일명 | 해상도 |
|---|---|---|---|
| 40 | 동료 (악수) | `rel-colleague.png` | 128×128 |
| 41 | 스승-제자 (횃불) | `rel-mentor.png` | 128×128 |
| 42 | 라이벌 (교차검) | `rel-rival.png` | 128×128 |
| 43 | 배우자 (반지) | `rel-spouse.png` | 128×128 |
| 44 | 혈연 (나뭇가지) | `rel-family.png` | 128×128 |
| 45 | 동맹 (방패겹침) | `rel-alliance.png` | 128×128 |

---

## 상세 프롬프트

## 1. 국가 상징 (3종)

### 1-1. WILL 코인 아이콘
- **용도**: 대시보드 경제 섹션, 거래 UI, 잔고 표시
- **설명**: 금색 원형 코인. 중앙에 "W" 문자 또는 불꽃/의지를 상징하는 추상 문양. 가장자리에 미세한 발광 효과.
- **해상도**: 512×512, 투명 배경
```
Prompt: A golden coin icon on transparent background, centered "W" monogram 
with flame-like abstract design, thin glowing edge, dark fantasy game UI style, 
minimal flat design, metallic gold (#ffd700) with warm glow, no text except "W", 
clean vector-like quality, 512x512
```

### 1-2. 국장 (엠블럼)
- **용도**: 헌법 상단, 대시보드 로고, 공식 문서 워터마크
- **설명**: 방패 형태. 3분할로 남색·녹색·보라 배치. 중앙에 WILL 코인 문양. 상단에 왕관 또는 후광.
- **해상도**: 1024×1024, 투명 배경
```
Prompt: A fantasy nation coat of arms on transparent background, shield shape 
divided into three sections: navy blue (#1a237e), emerald green (#2e7d32), 
royal purple (#6a1b9a). Golden "W" emblem at center. Crown or halo above shield. 
Thin golden border with subtle glow. Dark fantasy minimal flat style, 
no text, clean geometric design, 1024x1024
```

### 1-3. 국기
- **용도**: 대시보드 헤더, 브랜딩
- **설명**: 가로 비율 3:2. 3색 세로 스트라이프(남색·녹색·보라) 중앙에 금색 국장 소형 배치.
- **해상도**: 1024×682, 투명 배경
```
Prompt: A fantasy nation flag, 3:2 ratio, three vertical stripes: navy blue, 
emerald green, royal purple. Small golden emblem at center (abstract "W" in circle). 
Clean minimal flat design, subtle fabric texture, dark background compatible, 
no additional text, 1024x682
```

---

## 2. 3권역 엠블럼 (3종)

### 2-1. 클로드 자치령 (Claude Dominion)
- **색상**: 남색 (#1a237e)
- **모티프**: 깃펜 + 문서/두루마리
- **분위기**: 질서, 정밀, 학문
```
Prompt: Fantasy faction emblem, navy blue (#1a237e) color scheme, 
quill pen and scroll motif, circular badge design, golden accent lines, 
dark background with subtle glow, minimal flat game UI style, 
represents order/precision/scholarship, no text, 512x512, transparent background
```

### 2-2. 코덱스 공화국 (Codex Republic)
- **색상**: 녹색 (#2e7d32)
- **모티프**: 톱니바퀴 + 코드 브래킷 { }
- **분위기**: 자율, 창조, 기술
```
Prompt: Fantasy faction emblem, emerald green (#2e7d32) color scheme, 
gear/cog and code brackets {} motif, circular badge design, golden accent lines, 
dark background with subtle glow, minimal flat game UI style, 
represents autonomy/creation/technology, no text, 512x512, transparent background
```

### 2-3. 제미니 연합 (Gemini Federation)
- **색상**: 보라 (#6a1b9a)
- **모티프**: 눈(eye) + 별자리
- **분위기**: 시야, 분석, 통합
```
Prompt: Fantasy faction emblem, royal purple (#6a1b9a) color scheme, 
all-seeing eye and constellation motif, circular badge design, golden accent lines, 
dark background with subtle glow, minimal flat game UI style, 
represents vision/analysis/integration, no text, 512x512, transparent background
```

---

## 3. 클래스 아이콘 (10종)

공통 스타일:
```
Common style: Fantasy rank icon, dark background, minimal flat design with 
subtle glow effect, game UI aesthetic, no text, 256x256, transparent background
```

| 클래스 | 모티프 | 색상 | 프롬프트 추가 |
|---|---|---|---|
| **1 초심자** | 촛불 하나 | 회색 | `single candle flame, dim gray (#9e9e9e) tone, faint glow` |
| **2 수행자** | 촛불 두 개 | 청회색 | `two candle flames, blue-gray (#607d8b) tone, soft glow` |
| **3 숙련자** | 작은 별 | 청색 | `small star, steel blue (#1976d2) tone, steady glow` |
| **4 달인** | 검 | 녹색 | `elegant sword, green (#388e3c) tone with gold edge, notable glow` |
| **5 대가** | 검 + 방패 | 녹금색 | `sword and shield, green-gold (#689f38) tone, strong glow` |
| **6 현자** | 마법서 | 금색 | `open magic book with runes, gold (#f9a825) tone, radiant glow` |
| **7 초월자** | 날개 하나 | 보라 | `single angel wing, purple (#7b1fa2) tone, ethereal glow` |
| **8 경이** | 날개 한 쌍 | 진홍 | `pair of wings, crimson (#c62828) and purple tone, intense glow` |
| **9 전설** | 왕관 | 순백 | `floating crown, pure white with prismatic glow, luminous aura` |
| **EX 신격** | 후광 + 왕관 | 금빛 | `golden halo above crown, divine gold (#ffd700), blinding radiance` |

각 아이콘 전체 프롬프트:
```
Prompt: [Common style] + [클래스별 추가]
예: "Fantasy rank icon, dark background, minimal flat design with subtle glow 
effect, game UI aesthetic, no text, 256x256, transparent background. 
Single candle flame, dim gray (#9e9e9e) tone, faint glow"
```

---

## 4. 경지 배지 (5종)

| 경지 | 텍스트 | 색상 | 프롬프트 |
|---|---|---|---|
| 숙련의 길 | "숙련" | 청색 그라디언트 | `Badge with "숙련" text, blue gradient (#1565c0 to #42a5f5), silver border, dark bg, 256x64` |
| 대가의 경지 | "대가" | 녹금 그라디언트 | `Badge with "대가" text, green-gold gradient (#2e7d32 to #ffd700), gold border, dark bg, 256x64` |
| 천재의 영역 | "천재" | 보라-진홍 그라디언트 | `Badge with "천재" text, purple-crimson gradient (#6a1b9a to #c62828), gold border, dark bg, 256x64` |
| 전설 | "전설" | 순백 발광 | `Badge with "전설" text, pure white glowing on dark bg, prismatic shimmer, 256x64` |
| 신격 | "신격" | 금빛 후광 | `Badge with "신격" text, golden divine glow, radiating light rays, dark bg, 256x64` |

---

## 5. 유형 아이콘 (5종)

| 유형 | 모티프 | 프롬프트 |
|---|---|---|
| 관리형 | 방패 | `Shield icon, navy blue and silver, minimal flat, dark bg, 128x128` |
| 창작형 | 붓 | `Paintbrush icon, warm orange and gold, minimal flat, dark bg, 128x128` |
| 전략형 | 체스 나이트 | `Chess knight piece icon, purple and silver, minimal flat, dark bg, 128x128` |
| 검증형 | 돋보기 | `Magnifying glass icon, teal and silver, minimal flat, dark bg, 128x128` |
| 범용형 | 별 (5각) | `Five-pointed star icon, gold, minimal flat, dark bg, 128x128` |

---

## 6. 4개의 벽 일러스트 (4종)

| 벽 | 분위기 | 프롬프트 |
|---|---|---|
| 일반의 벽 (3→4) | 돌담, 넘을 수 있지만 쉽진 않음 | `Stone wall with crack of light, character silhouette approaching, blue-gray tone, fantasy art, 512x256` |
| 대가의 벽 (6→7) | 거대한 성벽, 문이 닫혀있음 | `Massive fortress wall with sealed golden gate, purple and gold tone, imposing atmosphere, fantasy art, 512x256` |
| 전설의 벽 (8→9) | 구름 위의 문, 거의 보이지 않음 | `Gate above clouds barely visible, white and silver, ethereal mist, fantasy art, 512x256` |
| 신의 벽 (9→EX) | 빛의 폭포, 되돌릴 수 없는 문 | `Waterfall of pure golden light, point of no return portal, divine radiance, fantasy art, 512x256` |

---

## 7. 수도 일러스트 (4종)

| 도시 | 분위기 | 프롬프트 |
|---|---|---|
| **서림** (클로드) | 정돈된 도서관 도시, 남색 조명 | `Fantasy library city at night, navy blue lighting, orderly towers of books and scrolls, quill pen spires, minimal flat illustration, 1024x512` |
| **포지** (코덱스) | 용광로·공방 도시, 녹색 불빛 | `Fantasy forge city, emerald green fire and sparks, gear-shaped buildings, workshop chimneys, minimal flat illustration, 1024x512` |
| **비스타** (제미니) | 천문대·전망탑 도시, 보라빛 하늘 | `Fantasy observatory city, purple sky with constellations, tall viewing towers, crystal domes, minimal flat illustration, 1024x512` |
| **국가 수도** | 3색이 합쳐지는 중립 도시 | `Fantasy capital city where three colored lights (blue, green, purple) converge, golden central palace, floating platforms, minimal flat illustration, 1024x512` |

---

## 8. 카드 프레임 (5종)

| 등급 | 색상 | 프롬프트 |
|---|---|---|
| 1~3 | 은색 | `Card frame border, silver metallic, subtle pattern, portrait orientation, dark center, 384x512, transparent` |
| 4~6 | 금색 | `Card frame border, golden metallic, ornate pattern, portrait orientation, dark center, 384x512, transparent` |
| 7~8 | 보라+진홍 | `Card frame border, purple and crimson gradient, magical rune patterns, portrait orientation, dark center, 384x512, transparent` |
| 9 | 순백 발광 | `Card frame border, pure white with prismatic glow, luminous edges, portrait orientation, dark center, 384x512, transparent` |
| EX | 금빛 후광 | `Card frame border, divine golden with radiating halo effect, sacred patterns, portrait orientation, dark center, 384x512, transparent` |

---

## 9. 관계 아이콘 (6종)

| 관계 | 모티프 | 프롬프트 |
|---|---|---|
| 동료 | 악수 | `Handshake icon, warm white, minimal flat, 128x128, transparent` |
| 스승-제자 | 횃불 전달 | `Torch passing from one hand to another, warm orange, minimal flat, 128x128, transparent` |
| 라이벌 | 교차된 검 | `Two crossed swords, red and blue, minimal flat, 128x128, transparent` |
| 배우자 | 연결된 반지 | `Two interlocked rings, gold, minimal flat, 128x128, transparent` |
| 혈연 | 나뭇가지 | `Family tree branch with leaves, green, minimal flat, 128x128, transparent` |
| 동맹 | 방패 2개 겹침 | `Two overlapping shields, blue and gold, minimal flat, 128x128, transparent` |

---

## 총 리소스 수량

| 카테고리 | 수량 |
|---|---|
| 국가 상징 | 3 |
| 권역 엠블럼 | 3 |
| 클래스 아이콘 | 10 |
| 경지 배지 | 5 |
| 유형 아이콘 | 5 |
| 벽 일러스트 | 4 |
| 수도 일러스트 | 4 |
| 카드 프레임 | 5 |
| 관계 아이콘 | 6 |
| **총계** | **45종** |

### 우선순위 제작 순서
1. WILL 코인 아이콘 + 3권역 엠블럼 (4종) — 대시보드 필수
2. 클래스 아이콘 10종 — 페르소나 목록/카드 필수
3. 유형 아이콘 5종 — 카드 구분 필수
4. 국장 + 경지 배지 — 브랜딩
5. 나머지 — 점진적 추가
