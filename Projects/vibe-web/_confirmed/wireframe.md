# 와이어프레임 — 페이지 구조 + 화면 흐름도

> 최종 갱신: 2026-03-24
> 근거: DEVELOPMENT-BIBLE §15 (프론트엔드 설계), §2 (디렉토리 구조)

---

## 페이지 목록

| # | 페이지 | URL | 인증 | 핵심 컴포넌트 |
|---|--------|-----|------|-------------|
| 1 | 홈 | `/` | 불필요 | 갤러리 그리드 + 주간 베스트 위젯 + 월간 명예의 전당 위젯 |
| 2 | 작품 상세 | `/posts/[id]` | 불필요 (댓글은 인증 필요) | 원스크롤: 작품 → 제작과정 → 댓글 |
| 3 | 업로드 | `/upload` | 필수 | 이미지 업로드 + 제목 + 도구 태그 + 마크다운 에디터 |
| 4 | 게시판 목록 | `/board` | 불필요 | 카테고리 탭 (5개) + 글 목록 |
| 5 | 게시판 상세 | `/board/[id]` | 불필요 (댓글은 인증) | 글 본문 + 댓글 |
| 6 | 게시판 작성 | `/board/new` | 필수 | 카테고리 선택 + 제목 + 마크다운 에디터 |
| 7 | 프로필 | `/users/[id]` | 불필요 | 사용자 정보 + 등급 + 작품 그리드 + 활동 이력 |
| 8 | 내 프로필 편집 | `/settings` | 필수 | 닉네임 수정 + 아바타 변경 |
| 9 | 명예의 전당 | `/hall-of-fame` | 불필요 | 주간 Top 5 + 월간 Top 10 전체 보기 |
| 10 | 검색 결과 | `/search?q=` | 불필요 | 작품 + 게시글 + 사용자 탭별 결과 |
| 11 | 로그인 | `/login` | — | GitHub / Google OAuth 버튼 |

---

## 공통 레이아웃

```
┌────────────────────────────────────────────────────────┐
│ [Logo] vibe-web    [검색바]    [로그인/프로필+등급배지]  │  ← 헤더 (고정)
├────────────────────────────────────────────────────────┤
│ [홈] [게시판] [명예의전당] [업로드+]                    │  ← 네비게이션
├────────────────────────────────────────────────────────┤
│                                                        │
│                    메인 콘텐츠                          │
│                                                        │
├────────────────────────────────────────────────────────┤
│ [About] [이용약관] [개인정보처리방침]                   │  ← 푸터
└────────────────────────────────────────────────────────┘
```

모바일: 햄버거 메뉴, 하단 탭바 (홈/게시판/업로드/명예의전당/내 프로필)

---

## 페이지별 와이어프레임

### 1. 홈 (`/`)

```
┌─────────────────────────────────────────┐
│              [헤더 + 네비]               │
├─────────────────────────────────────────┤
│ ┌─ 주간 베스트 Top 5 ─────────────────┐ │
│ │ [1위 카드] [2위] [3위] [4위] [5위]  │ │  ← 가로 스크롤 캐러셀
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ [정렬: 최신순 | 좋아요순 | 조회순]      │
├─────────────────────────────────────────┤
│ ┌──────┐ ┌──────┐ ┌──────┐             │
│ │ 카드1 │ │ 카드2 │ │ 카드3 │            │  ← 메이슨리 그리드
│ │      │ └──────┘ │      │             │
│ │      │ ┌──────┐ └──────┘             │
│ └──────┘ │ 카드4 │ ┌──────┐             │
│ ┌──────┐ │      │ │ 카드5 │             │
│ │ 카드6 │ └──────┘ └──────┘             │
│ └──────┘                                │
│         [더 보기] (커서 페이지네이션)     │
└─────────────────────────────────────────┘
```

**리치 카드 구성:**
```
┌──────────────────┐
│   [썸네일 이미지]  │
│                   │
├──────────────────┤
│ 작품 제목          │
│ @작성자 · 등급배지  │
│ [도구태그1][태그2]  │
│ "제작과정 미리보기 1줄..." │
│ ♥ 42              │
└──────────────────┘
```

### 2. 작품 상세 (`/posts/[id]`)

```
┌─────────────────────────────────────────┐
│              [헤더 + 네비]               │
├─────────────────────────────────────────┤
│                                         │
│        [작품 이미지 / 결과물]            │  ← 전체 너비
│                                         │
├─────────────────────────────────────────┤
│ 작품 제목                    ♥ 42  👁 128│
│ @작성자 · 크리에이터 Lv.3 · 2024-03-24  │
│ [도구태그1] [도구태그2] [도구태그3]       │
├─────────────────────────────────────────┤
│ ── 제작 과정 ──                          │
│                                         │
│ (마크다운 렌더링 영역)                   │
│ 사용 도구, 프롬프트, 워크플로우 등       │
│                                         │
├─────────────────────────────────────────┤
│ ── 댓글 (12개) ──                        │
│ @유저A · 루키 Lv.2 · 1시간 전           │
│ 댓글 내용...                    [신고]   │
│ ─────────────                           │
│ @유저B · 프로 Lv.4 · 3시간 전           │
│ 댓글 내용...                    [신고]   │
│ ─────────────                           │
│ [댓글 입력칸]                  [작성]    │
└─────────────────────────────────────────┘
```

### 3. 업로드 (`/upload`)

```
┌─────────────────────────────────────────┐
│              [헤더 + 네비]               │
├─────────────────────────────────────────┤
│ 새 작품 올리기                           │
├─────────────────────────────────────────┤
│ [이미지 드래그&드롭 영역]                │
│  또는 [파일 선택] (최대 10MB, jpg/png/webp) │
├─────────────────────────────────────────┤
│ 제목: [___________________________]     │
│ 도구 태그: [+추가] [Midjourney] [Claude] │
├─────────────────────────────────────────┤
│ 제작 과정 (마크다운)                     │
│ ┌──────────────────────────────────┐    │
│ │ (마크다운 에디터)                 │    │
│ │ 미리보기 탭 지원                  │    │
│ └──────────────────────────────────┘    │
├─────────────────────────────────────────┤
│              [업로드] [취소]             │
└─────────────────────────────────────────┘
```

### 4. 게시판 (`/board`)

```
┌─────────────────────────────────────────┐
│              [헤더 + 네비]               │
├─────────────────────────────────────────┤
│ [자유] [질문] [팁 공유] [프로젝트 모집] [공지] │  ← 카테고리 탭
├─────────────────────────────────────────┤
│                                [글쓰기+]│
│ ┌─────────────────────────────────────┐ │
│ │ 제목                 @작성자  ♥ 12  │ │
│ │ 미리보기 1줄...      크리에이터 Lv.3│ │
│ ├─────────────────────────────────────┤ │
│ │ 제목                 @작성자  ♥ 5   │ │
│ │ 미리보기 1줄...      루키 Lv.2      │ │
│ └─────────────────────────────────────┘ │
│         [더 보기] (커서 페이지네이션)     │
└─────────────────────────────────────────┘
```

### 7. 프로필 (`/users/[id]`)

```
┌─────────────────────────────────────────┐
│              [헤더 + 네비]               │
├─────────────────────────────────────────┤
│ [아바타]  닉네임                         │
│          크리에이터 Lv.3                 │
│          ████████░░ 270/400 exp         │  ← 경험치 바
│          가입일: 2024-01-15             │
│          명예의 전당 선정: 3회            │
├─────────────────────────────────────────┤
│ [작품] [활동 이력] 탭                    │
├─────────────────────────────────────────┤
│ (작품 탭 선택 시)                        │
│ ┌──────┐ ┌──────┐ ┌──────┐             │
│ │ 작품1 │ │ 작품2 │ │ 작품3 │            │  ← 메이슨리
│ └──────┘ └──────┘ └──────┘             │
├─────────────────────────────────────────┤
│ (활동 이력 탭 선택 시)                   │
│ · 작품 "AI 풍경화" 업로드 — 2시간 전     │
│ · 댓글 작성 on "프롬프트 팁" — 5시간 전  │
│ · ♥ 좋아요 on "미드저니 결과" — 어제     │
└─────────────────────────────────────────┘
```

### 9. 명예의 전당 (`/hall-of-fame`)

```
┌─────────────────────────────────────────┐
│              [헤더 + 네비]               │
├─────────────────────────────────────────┤
│ ── 이번 주 베스트 Top 5 ──              │
│ (갱신: 매주 월요일 UTC 00:00)            │
│                                         │
│ 1. [카드] 작품제목 · @작성자 · ♥ 128    │
│ 2. [카드] 작품제목 · @작성자 · ♥ 95     │
│ 3. [카드] 작품제목 · @작성자 · ♥ 82     │
│ 4. [카드] 작품제목 · @작성자 · ♥ 71     │
│ 5. [카드] 작품제목 · @작성자 · ♥ 63     │
├─────────────────────────────────────────┤
│ ── 이번 달 명예의 전당 Top 10 ──         │
│ (갱신: 매월 1일 UTC 00:00)               │
│                                         │
│ 1~10위 카드 그리드                       │
│                                         │
│ (활성 유저 10명 미만 시)                 │
│ "데이터 집계 중" 또는 "지난 주/월 기준"  │
└─────────────────────────────────────────┘
```

---

## 화면 흐름도

```
[로그인] ──OAuth──> [홈]
                     │
         ┌───────────┼───────────┬──────────────┐
         ↓           ↓           ↓              ↓
    [갤러리 카드]  [게시판]   [명예의전당]     [검색]
         │           │           │              │
         ↓           ↓           ↓              ↓
   [작품 상세]   [게시글 상세]  [작품 상세]   [결과 → 상세]
    │    │          │
    │    ↓          ↓
    │  [댓글 작성]  [댓글 작성]
    │  (인증 필요)  (인증 필요)
    │
    ↓
 [좋아요] ──> activityScore 갱신 ──> 등급 업데이트
                                         │
                                         ↓
                                    [프로필 반영]

[업로드+] ──(인증 필요)──> [업로드 폼] ──> [작품 상세]
                                           │
                                           ↓
                                     uploadCount +10pt

[프로필] ──> [작품 탭 / 활동 이력 탭]
  │
  ↓ (본인)
[설정] ──> 닉네임/아바타 수정
```

---

## Next.js App Router 라우트 구조 (BIBLE §2)

```
src/app/
├── (auth)/
│   └── login/page.tsx              # 로그인
├── (main)/
│   ├── page.tsx                    # 홈 (갤러리 + HoF 위젯)
│   ├── posts/
│   │   └── [id]/page.tsx           # 작품 상세
│   ├── upload/page.tsx             # 업로드
│   ├── board/
│   │   ├── page.tsx                # 게시판 목록
│   │   ├── new/page.tsx            # 게시판 작성
│   │   └── [id]/page.tsx           # 게시판 상세
│   ├── users/
│   │   └── [id]/page.tsx           # 프로필
│   ├── settings/page.tsx           # 내 프로필 편집
│   ├── hall-of-fame/page.tsx       # 명예의 전당
│   └── search/page.tsx             # 검색 결과
├── api/
│   ├── auth/[...nextauth]/route.ts # NextAuth
│   ├── posts/route.ts              # 갤러리 CRUD
│   ├── posts/[id]/like/route.ts    # 좋아요
│   ├── posts/[id]/comments/route.ts# 댓글
│   ├── board/route.ts              # 게시판 CRUD
│   ├── board/[id]/like/route.ts    # 게시판 좋아요
│   ├── board/[id]/comments/route.ts# 게시판 댓글
│   ├── board/[id]/report/route.ts  # 신고
│   ├── users/[id]/route.ts         # 프로필
│   ├── search/route.ts             # 검색
│   └── hall-of-fame/route.ts       # HoF 데이터
└── layout.tsx                      # 공통 레이아웃
```

---

## DB 스키마 초안 (BIBLE §3 — Prisma)

```prisma
model User {
  id            String   @id @default(cuid())
  name          String
  email         String   @unique
  image         String?
  role          String   @default("user")   // user | admin
  status        String   @default("active") // active | warned | suspended | banned
  warningCount  Int      @default(0)
  expPoints     Int      @default(0)
  userLevel     String   @default("뉴비 Lv.1")
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt
  deletedAt     DateTime?

  posts         Post[]
  boardPosts    BoardPost[]
  comments      Comment[]
  likes         Like[]
  reports       Report[]
}

model Post {
  id            String   @id @default(cuid())
  title         String
  thumbnailUrl  String
  content       String   @db.Text    // 제작과정 마크다운
  toolTags      String[] // ["Midjourney", "Claude"]
  viewCount     Int      @default(0)
  likeCount     Int      @default(0)
  authorId      String
  author        User     @relation(fields: [authorId], references: [id])
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt
  deletedAt     DateTime?
  isHidden      Boolean  @default(false) // 신고 자동 숨김

  comments      Comment[]
  likes         Like[]
  reports       Report[]

  @@index([authorId])
  @@index([likeCount(sort: Desc)])
  @@index([createdAt(sort: Desc)])
}

model BoardPost {
  id            String   @id @default(cuid())
  title         String
  content       String   @db.Text
  categoryId    Int      // 1:자유 2:질문 3:팁공유 4:프로젝트모집 5:공지
  likeCount     Int      @default(0)
  authorId      String
  author        User     @relation(fields: [authorId], references: [id])
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt
  deletedAt     DateTime?
  isHidden      Boolean  @default(false)

  comments      Comment[]
  likes         Like[]
  reports       Report[]

  @@index([categoryId, createdAt(sort: Desc)])
  @@index([authorId])
}

model Comment {
  id            String   @id @default(cuid())
  content       String
  authorId      String
  author        User     @relation(fields: [authorId], references: [id])
  postId        String?
  post          Post?    @relation(fields: [postId], references: [id])
  boardPostId   String?
  boardPost     BoardPost? @relation(fields: [boardPostId], references: [id])
  createdAt     DateTime @default(now())
  deletedAt     DateTime?

  @@index([postId])
  @@index([boardPostId])
  @@index([authorId])
}

model Like {
  id            String   @id @default(cuid())
  userId        String
  user          User     @relation(fields: [userId], references: [id])
  postId        String?
  post          Post?    @relation(fields: [postId], references: [id])
  boardPostId   String?
  boardPost     BoardPost? @relation(fields: [boardPostId], references: [id])
  createdAt     DateTime @default(now())

  @@unique([userId, postId])       // 1인 1좋아요
  @@unique([userId, boardPostId])  // 1인 1좋아요
  @@index([postId])
  @@index([boardPostId])
}

model Report {
  id            String   @id @default(cuid())
  category      Int      // 1:스팸 2:욕설 3:저작권침해 4:기타
  reason        String?
  reporterId    String
  postId        String?
  post          Post?    @relation(fields: [postId], references: [id])
  boardPostId   String?
  boardPost     BoardPost? @relation(fields: [boardPostId], references: [id])
  createdAt     DateTime @default(now())

  @@index([postId])
  @@index([boardPostId])
}

model ScoreEvent {
  id            String   @id @default(cuid())
  userId        String
  actionType    String   // upload | like_received | comment_write | comment_received
  targetId      String   // postId or boardPostId or commentId
  points        Int
  createdAt     DateTime @default(now())

  @@index([userId, createdAt])
  @@index([userId, actionType, targetId]) // 멱등성 체크
}

model HallOfFame {
  id            String   @id @default(cuid())
  periodType    String   // weekly | monthly
  periodStart   DateTime
  postId        String?
  boardPostId   String?
  rank          Int
  likeCount     Int
  isFallback    Boolean  @default(false) // 이전 기간 데이터 유지 시
  createdAt     DateTime @default(now())

  @@unique([periodType, periodStart, rank])
  @@index([periodType, periodStart])
}
```
