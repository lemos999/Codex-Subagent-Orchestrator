# 개발 제작 바이블

> **목적**: 프로젝트 유형에 관계없이 적용할 수 있는 소프트웨어 개발 원칙과 경험 기록.
> **적용 범위**: 서비스 앱, 커뮤니티 사이트, 관리 도구, 유틸리티 프로그램, CLI, 모바일 앱
> **기반**: ShortLive Shop Helper (라이브 커머스 SaaS) + 다수 프로젝트에서 축적한 실전 경험.
> **구조**: 각 섹션은 **[원칙]** (스택 무관) + **[레시피]** (특정 스택 예시)로 구성.
> **최초 작성**: 2026-03-24
> **최종 업데이트**: 2026-03-24

---

## 목차

1. [기술 스택 선정 기준](#1-기술-스택-선정-기준)
2. [프로젝트 초기 설정](#2-프로젝트-초기-설정)
3. [DB 설계 원칙](#3-db-설계-원칙)
4. [API 설계 원칙](#4-api-설계-원칙)
5. [인증 & 세션 설계](#5-인증--세션-설계)
6. [입력값 검증 — 모든 보안의 시작](#6-입력값-검증--모든-보안의-시작)
7. [보안 체크리스트](#7-보안-체크리스트)
8. [금전/결제 시스템](#8-금전결제-시스템)
9. [실시간 통신 (WebSocket)](#9-실시간-통신-websocket)
10. [테스트 전략](#10-테스트-전략)
11. [에러 처리 원칙](#11-에러-처리-원칙)
12. [개발 프로세스](#12-개발-프로세스)
13. [인프라 & 배포](#13-인프라--배포)
14. [보편적 실수와 교훈](#14-보편적-실수와-교훈)
15. [프론트엔드 설계](#15-프론트엔드-설계)
16. [캐싱 & 성능 최적화](#16-캐싱--성능-최적화)
17. [관측성 (Observability)](#17-관측성-observability)
18. [CI/CD 파이프라인](#18-cicd-파이프라인)
19. [백그라운드 작업 & 큐](#19-백그라운드-작업--큐)
20. [파일 업로드 & 스토리지](#20-파일-업로드--스토리지)
21. [권한 모델 (RBAC)](#21-권한-모델-rbac)
22. [API 버전관리 & 하위호환](#22-api-버전관리--하위호환)
23. [모바일 / 데스크톱 / CLI 확장](#23-모바일--데스크톱--cli-확장)
24. [12-Factor 원칙](#24-12-factor-원칙)
25. [코드 리뷰](#25-코드-리뷰)
26. [DB 성능 튜닝 (심화)](#26-db-성능-튜닝-심화)
27. [커뮤니티 & UGC 관리](#27-커뮤니티--ugc-관리)
28. [런칭 전 최종 체크리스트](#28-런칭-전-최종-체크리스트)
29. [참조 문서 & 출처](#29-참조-문서--출처)

---

## 1. 기술 스택 선정 기준

### 프로젝트 유형별 추천

| 유형 | 프레임워크 | DB | 인증 | 실시간 |
|------|-----------|-----|------|--------|
| MVP / 1인 개발 | Next.js (App Router) | SQLite → PostgreSQL | NextAuth | Socket.IO |
| 포털 / 대규모 | Next.js 또는 별도 FE+BE | PostgreSQL | NextAuth 또는 자체 | Socket.IO / SSE |
| 관리자 도구 | Next.js / Retool | PostgreSQL | NextAuth | 불필요 또는 SSE |
| API 서비스 | Fastify / Express / NestJS | PostgreSQL | JWT 자체 구현 | WebSocket |
| 커뮤니티 / 포럼 | Next.js / Django | PostgreSQL | OAuth + 자체 | SSE |
| 모바일 앱 (하이브리드) | React Native / Flutter | PostgreSQL (API 서버) | JWT + refresh token | WebSocket |
| CLI / 유틸리티 | Node.js / Python | SQLite / JSON | N/A | N/A |
| 데스크톱 앱 | Electron / Tauri | SQLite | 로컬 인증 | IPC |

> **[원칙]** 위 표는 참고용이다. 핵심 원칙은 아래이며 어떤 스택이든 적용된다.
> **[레시피]** 코드 예시는 주로 Next.js + TypeScript를 사용하지만, 원칙은 Django/Rails/Spring/Flask에도 동일하게 적용된다.

### 선택 시 고려 순서

```
1. 팀 규모 → 1인이면 풀스택 프레임워크 (Next.js)
2. 데이터 특성 → 금전/트랜잭션이면 PostgreSQL 필수
3. 실시간 필요 여부 → 있으면 Socket.IO, 단방향이면 SSE
4. 배포 환경 → 서버리스면 WebSocket 제한 고려
5. 확장 계획 → MVP 후 성장 예상이면 확장 가능한 스택
```

### 실전 교훈

> **"나중에 바꾸면 되지" 함정**
> SQLite로 시작해서 PostgreSQL로 전환하는 건 Prisma 덕에 가능했지만, 전환 과정에서 트랜잭션 타임아웃, 동시성 버그를 겪었다. **돈이 오가거나 동시 사용자가 10명 이상이면 처음부터 PostgreSQL.**

> **프레임워크는 익숙한 것이 최고**
> 새 프레임워크를 배우며 프로젝트를 시작하면 "프레임워크 학습"과 "기능 구현"이 섞여 속도가 절반으로 떨어진다.

---

## 2. 프로젝트 초기 설정

### 첫날 해야 할 것

```
□ Git 저장소 생성 + .gitignore
□ TypeScript strict mode 설정
□ ESLint + Prettier 설정
□ 환경변수 구조 (.env.example 작성)
□ DB 스키마 초안 (핵심 3~5 테이블)
□ 인증 기본 구조 (로그인/회원가입)
□ 테스트 프레임워크 설정 (Vitest)
□ 배포 파이프라인 초안
```

### 디렉토리 구조 (Next.js 기준)

```
project/
├── prisma/
│   ├── schema.prisma          # DB 스키마
│   └── migrations/
├── src/
│   ├── app/
│   │   ├── (auth)/            # 인증 페이지
│   │   ├── (dashboard)/       # 보호된 라우트
│   │   └── api/               # API 엔드포인트
│   ├── lib/                   # 비즈니스 로직
│   ├── services/              # 외부 서비스 연동
│   ├── components/            # UI 컴포넌트
│   └── __tests__/             # 테스트
├── docs/                      # 문서
└── server.ts                  # (커스텀 서버 필요 시)
```

### 환경변수 관리

```
# .env.example — 필요한 변수 목록 (값은 비움)
DATABASE_URL=
NEXTAUTH_SECRET=            # 32자 이상 필수
NEXTAUTH_URL=
NODE_ENV=
ENCRYPTION_KEY=             # PII 암호화 시
```

> **절대 `.env`를 커밋하지 말 것.** `.env.example`만 커밋.

---

## 3. DB 설계 원칙

### 스키마 설계

| 원칙 | 설명 |
|------|------|
| **ID는 CUID/UUID** | auto-increment는 리소스 개수 노출 (IDOR 공격 벡터) |
| **timestamps 필수** | 모든 테이블에 `createdAt`, `updatedAt` |
| **soft delete 고려** | 중요 데이터는 `deletedAt` 필드로 논리 삭제 |
| **인덱스 명시** | 자주 조회하는 컬럼에 `@@index` 추가 |
| **관계 명시** | `onDelete: Cascade` vs `SetNull` 명확히 결정 |

### Prisma 사용 팁

```typescript
// ✅ 좋은 예: 트랜잭션 내 fresh-read 후 상태 변경
await prisma.$transaction(async (tx) => {
  const fresh = await tx.order.findUnique({ where: { id } });
  if (fresh.status !== "대기") throw new Error("이미 처리됨");
  await tx.order.update({ where: { id }, data: { status: "완료" } });
});

// ❌ 나쁜 예: 트랜잭션 밖에서 읽고 안에서 쓰기 (TOCTOU)
const order = await prisma.order.findUnique({ where: { id } });
if (order.status === "대기") {
  await prisma.order.update({ where: { id }, data: { status: "완료" } });
}
```

### 마이그레이션 규칙

```
1. 운영 DB에 직접 SQL 실행 금지 — 항상 Prisma migrate 사용
2. 마이그레이션은 되돌릴 수 있도록 설계
3. 컬럼 삭제는 2단계: (1) 코드에서 사용 중단 → (2) 다음 배포에서 컬럼 삭제
4. NOT NULL 컬럼 추가 시 default 값 필수
```

---

## 4. API 설계 원칙

### 엔드포인트 구조

```
GET    /api/resources          # 목록 조회 (페이지네이션)
GET    /api/resources/:id      # 단건 조회
POST   /api/resources          # 생성
PATCH  /api/resources/:id      # 부분 수정
DELETE /api/resources/:id      # 삭제
```

### 필수 적용 사항

```typescript
// 모든 API 핸들러의 기본 구조
export async function POST(req: NextRequest) {
  // 1. 인증 확인
  const { error, sellerId } = await getAuthenticatedUser();
  if (error) return error;

  // 2. 요청 크기 제한
  const { data, error: bodyError } = await parseBodyWithLimit(req, 1_000_000);
  if (bodyError) return bodyError;

  // 3. 입력값 검증
  const { name, amount } = data;
  if (typeof name !== "string" || name.length > 100) {
    return NextResponse.json({ error: "잘못된 입력" }, { status: 400 });
  }

  // 4. 비즈니스 로직 (트랜잭션)
  const result = await prisma.$transaction(async (tx) => {
    // ...
  });

  // 5. 응답 (필요한 데이터만)
  return NextResponse.json({ id: result.id });
}
```

### 응답 설계

```typescript
// ✅ 좋은 응답: 필요한 것만
{ "id": "cuid123", "status": "created" }

// ❌ 나쁜 응답: 내부 정보 노출
{ "id": 42, "query": "SELECT * FROM ...", "stack": "Error at..." }
```

### 페이지네이션

```typescript
// 커서 기반 (대량 데이터에 적합)
GET /api/items?cursor=abc&limit=20

// 오프셋 기반 (간단한 경우)
GET /api/items?page=1&limit=20

// limit 상한 강제
const limit = Math.min(Math.max(parseInt(rawLimit) || 20, 1), 100);
```

---

## 5. 인증 & 세션 설계

### NextAuth 설정 핵심

```typescript
// JWT callback에서 매번 계정 상태 확인
async jwt({ token, user }) {
  if (user) {
    token.id = user.id;
    token.role = user.role;
  }

  // 매 요청마다 DB에서 계정 상태 확인
  const seller = await prisma.user.findUnique({
    where: { id: token.id },
    select: { status: true, passwordChangedAt: true }
  });

  if (!seller) return { ...token, error: "account_deleted" };
  if (seller.status === "blocked") return { ...token, error: "account_blocked" };
  if (seller.passwordChangedAt > token.iat * 1000) {
    return { ...token, error: "password_changed" };
  }

  return token;
}
```

### 세션 보안 원칙

| 원칙 | 이유 |
|------|------|
| **토큰은 SHA-256 해시 후 DB 저장** | DB 유출 시 세션 탈취 방지 |
| **비밀번호 변경 시 기존 세션 무효화** | 계정 탈취 후 비밀번호 변경해도 공격자 세션 유지 방지 |
| **동시 세션 수 제한** | 계정 공유 방지, 보안 강화 |
| **JWT secret 32자 이상** | 브루트포스 방지 |
| **계정 차단/삭제 시 즉시 반영** | JWT callback에서 매번 확인 |

### 인증 유틸리티 패턴

```typescript
// 모든 API에서 사용하는 통합 인증 함수
async function getAuthenticatedUser() {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return { error: unauthorized(), userId: null };
  }

  const { error: userError } = session.user;
  if (userError === "account_blocked") {
    return { error: forbidden("계정이 차단되었습니다."), userId: null };
  }
  if (userError === "account_deleted") {
    return { error: unauthorized("계정이 삭제되었습니다."), userId: null };
  }
  if (userError === "password_changed") {
    return { error: unauthorized("비밀번호가 변경되었습니다. 다시 로그인하세요."), userId: null };
  }

  return { error: null, userId: session.user.id };
}
```

---

## 6. 입력값 검증 — 모든 보안의 시작

### 검증 체크리스트

모든 사용자 입력에 아래를 적용:

```typescript
// 문자열
if (typeof value !== "string") → 400
if (value.length === 0) → 400 (필수 필드)
if (value.length > MAX_LENGTH) → 400

// 숫자
if (typeof value !== "number" || !Number.isFinite(value)) → 400
if (value < MIN || value > MAX) → 400
if (!Number.isInteger(value)) → 400 (정수 필요 시)

// 배열
if (!Array.isArray(value)) → 400
if (value.length > MAX_ITEMS) → 400
if (!value.every(item => typeof item === "string")) → 400 (요소 타입)

// 불리언
if (typeof value !== "boolean") → 400
// ⚠️ !!"false" === true → typeof 체크 필수

// 열거형
if (!["A", "B", "C"].includes(value)) → 400

// JSON 객체
if (typeof value !== "object" || value === null || Array.isArray(value)) → 400
// + 허용된 키만 추출 (mass assignment 방지)
```

### 요청 크기 제한

```typescript
// 모든 POST/PUT/PATCH 엔드포인트에 적용
async function parseBodyWithLimit(req: Request, maxBytes = 1_000_000) {
  const contentLength = parseInt(req.headers.get("content-length") || "0");
  if (contentLength > maxBytes) {
    return { data: null, error: tooLarge() };
  }

  // Content-Length 없는 경우도 실제 body 크기 확인
  const body = await req.text();
  if (body.length > maxBytes) {
    return { data: null, error: tooLarge() };
  }

  try {
    return { data: JSON.parse(body), error: null };
  } catch {
    return { data: null, error: badRequest("잘못된 JSON") };
  }
}
```

### 실전 교훈

> **Prisma가 타입을 거르니까 검증 안 해도 되지 않나?**
> 아니다. Prisma는 런타임 에러를 던질 뿐, 공격자에게 유용한 에러 메시지를 노출할 수 있다. API 레이어에서 먼저 검증하고, Prisma는 최후 방어선으로 남겨라.

> **`!value` 검증의 함정**
> `!0`은 `true`, `!""` 은 `true`, `!false`도 `true`. 의도와 다르게 유효한 값을 거를 수 있다. `typeof` + 명시적 비교가 안전하다.

---

## 7. 보안 체크리스트

### 7.1 OWASP TOP 10 대응

| 위협 | 대응 | 적용 위치 |
|------|------|----------|
| **Injection** | Prisma ORM 사용 (파라미터 바인딩) | 모든 DB 쿼리 |
| **Broken Auth** | NextAuth + 계정 상태 매 요청 확인 | JWT callback |
| **Sensitive Data** | PII 암호화, 에러에 내부정보 제외 | 응답 전체 |
| **XXE** | JSON만 사용 (XML 파서 없음) | API 전체 |
| **Broken Access** | 모든 리소스에 소유권(userId) 확인 | 모든 CRUD |
| **Misconfiguration** | 보안 헤더, NODE_ENV 가드 | 미들웨어 |
| **XSS** | React 자동 이스케이프, CSP nonce | 프론트엔드 |
| **Insecure Deserialization** | JSON.parse + 스키마 검증 | API 입력 |
| **Known Vulnerabilities** | npm audit, 의존성 업데이트 | CI/CD |
| **Insufficient Logging** | AuditLog 테이블, IP 기록 | 상태 변경 시 |
| **Supply Chain (2025 신규)** | npm audit, 의존성 잠금, lockfile 커밋 | CI/CD |
| **Exceptional Conditions (2025 신규)** | 예외 상황 안전 처리, fail-open 방지 | 에러 핸들링 |

### 7.2 API 보안 체크리스트

```
□ 모든 엔드포인트에 인증 확인
□ 모든 리소스 접근에 소유권 확인 (IDOR 방지)
□ 모든 POST/PUT/PATCH에 요청 크기 제한
□ 모든 입력 필드에 타입 + 길이 + 범위 검증
□ 에러 응답에 스택트레이스, SQL 쿼리 등 내부 정보 제외
□ 디버그/테스트 엔드포인트에 환경 가드
□ rate limiting 적용 (로그인, 회원가입, API 전체)
□ CORS origin 명시적 설정
```

### 7.3 Race Condition 방지

```
□ 상태 변경은 반드시 $transaction 내에서 수행
□ 트랜잭션 내에서 fresh-read 후 상태 확인
□ decrement/increment 시 음수/오버플로우 방지
□ 유니크 값 생성은 트랜잭션 클라이언트로 수행
```

### 7.4 보안 헤더 (프로덕션)

```
Content-Security-Policy: default-src 'self'; script-src 'nonce-{random}' 'strict-dynamic'
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### 7.5 보안 감사 프로세스

```
1. 기능 개발 완료 후 일괄 감사 (개발 중 감사는 비효율)
2. 영역별 병렬 감사 (API / 서비스 로직 / 인프라 분담)
3. 발견 항목을 기획서에 기록 (심각도 분류)
4. 기획서 검증 (파일 경로, 취약점 존재 여부 확인)
5. 구현 + 관련 테스트 동시 수정
6. 전체 테스트 통과 확인 후 커밋
7. 다음 라운드 반복 (수확 체감 시 종료 — 보통 5~6차)
```

**감사 라운드별 특성**:

| 라운드 | 발견 성격 | 가치 |
|--------|----------|:----:|
| 1~3차 | 실제 해킹 가능 취약점 (인증 우회, 주입 등) | 높음 |
| 4~5차 | 동시성, 레이스 컨디션, 로직 결함 | 높음 |
| 6차 | 입력 검증 누락, 방어적 코딩 | 중간 |
| 7차~ | typeof 체크, 코딩 스타일 일관성 | 낮음 |

---

## 8. 금전/결제 시스템

> **돈이 오가는 시스템은 다른 모든 시스템보다 엄격한 기준이 필요하다.**

### 필수 원칙

```
1. DB는 처음부터 PostgreSQL (동시성 + ACID 보장)
2. 모든 금액은 정수 (원 단위). 절대 float/double 사용 금지
3. 모든 상태 변경은 $transaction + fresh-read
4. 잔액 차감 시 음수 방지: Math.max(0, balance - amount)
5. 수량에 상한 설정 (정수 오버플로우 방지)
6. 결제 관련 모든 경로에 블랙리스트 체크
7. 감사 로그 필수 (누가, 언제, 얼마를, 왜 변경했는지)
8. 재고 차감과 주문 생성은 하나의 트랜잭션
9. 자동 취소 시 stale 상태 체크 (이미 결제된 건 취소 방지)
10. 모든 금전 API에 rate limiting
```

### 금액 계산 패턴

```typescript
// ✅ 정수 연산
const total = price * quantity; // price: 15000, quantity: 3 → 45000

// ❌ 부동소수점 연산
const total = 0.1 + 0.2; // 0.30000000000000004

// 할인 계산도 정수로
const discount = Math.floor(total * discountRate); // 내림 처리
const finalPrice = total - discount;
```

### 잔액 관리 패턴

```typescript
await prisma.$transaction(async (tx) => {
  const customer = await tx.customer.findUnique({ where: { id } });

  // 음수 방지
  const newBalance = Math.max(0, customer.balance - amount);
  const actualDeduction = customer.balance - newBalance;

  if (actualDeduction < amount) {
    throw new Error("잔액 부족");
  }

  await tx.customer.update({
    where: { id },
    data: { balance: newBalance }
  });

  // 감사 로그
  await tx.balanceLog.create({
    data: {
      customerId: id,
      type: "차감",
      amount: -actualDeduction,
      reason: "주문 결제",
      balanceAfter: newBalance,
    }
  });
});
```

---

## 9. 실시간 통신 (WebSocket)

### Socket.IO 보안 설정

```typescript
const io = new Server(httpServer, {
  cors: { origin: process.env.NEXTAUTH_URL },
  maxHttpBufferSize: 1e6, // 1MB 메시지 크기 제한
  connectTimeout: 10000,  // 10초 연결 타임아웃
});

io.on("connection", (socket) => {
  // 인증 필수
  socket.on("join-room", async (data) => {
    const { token, roomId } = data;

    // 토큰 검증
    const session = await validateToken(token);
    if (!session) {
      socket.disconnect();
      return;
    }

    // 권한 확인
    if (session.userId !== roomId) {
      socket.disconnect();
      return;
    }

    socket.join(`room:${roomId}`);
  });
});
```

### 원칙

```
1. WebSocket도 HTTP와 동일한 인증 수준
2. 룸 가입 시 토큰 검증 + 소유권 확인
3. 메시지 크기 제한 (1MB)
4. 커넥션당 이벤트 rate limiting
5. 인증 실패 시 즉시 disconnect
6. 민감 데이터는 룸 단위로 격리
```

### SSE vs WebSocket 선택 기준

| 기준 | SSE | WebSocket |
|------|-----|-----------|
| 통신 방향 | 서버 → 클라이언트 (단방향) | 양방향 |
| 프로토콜 | HTTP | WS |
| 자동 재연결 | 브라우저 내장 | 직접 구현 (Socket.IO가 해결) |
| 서버리스 호환 | 가능 | 불가 (지속 연결 필요) |
| 용도 | 알림, 실시간 피드 | 채팅, 협업, 게임 |

---

## 10. 테스트 전략

### 테스트 피라미드

```
         ╱╲
        ╱ E2E ╲          # 핵심 플로우만 (인증→주문→결제)
       ╱────────╲
      ╱ 통합 테스트 ╲      # API 핸들러 + DB 연동
     ╱──────────────╲
    ╱   단위 테스트     ╲    # 순수 함수, 파서, 유틸리티
   ╱────────────────────╲
```

### 테스트 작성 원칙

| 원칙 | 설명 |
|------|------|
| **기능과 테스트 동시 작성** | 나중에 작성하면 로직을 까먹음 |
| **에러 케이스 우선** | 해피 패스보다 실패 케이스가 보안에 중요 |
| **Mock은 최소한** | DB만 mock, 비즈니스 로직은 실제 실행 |
| **동시성 테스트 필수** | 금전 로직은 반드시 병렬 호출 테스트 |
| **테스트 독립성** | 테스트 간 상태 공유 금지, 각자 setup/teardown |

### 테스트 구조 예시

```typescript
describe("주문 생성", () => {
  // 성공 케이스
  it("정상 주문을 생성한다", async () => { ... });

  // 인증/인가
  it("미인증 시 401을 반환한다", async () => { ... });
  it("다른 판매자의 상품으로 주문 시 404를 반환한다", async () => { ... });

  // 입력 검증
  it("수량이 0 이하이면 400을 반환한다", async () => { ... });
  it("수량이 상한을 초과하면 400을 반환한다", async () => { ... });
  it("존재하지 않는 상품이면 404를 반환한다", async () => { ... });

  // 비즈니스 로직
  it("재고 부족 시 주문을 거부한다", async () => { ... });
  it("블랙리스트 고객의 주문을 거부한다", async () => { ... });

  // 동시성
  it("동시 주문 시 재고를 초과 차감하지 않는다", async () => { ... });
});
```

### 실전 교훈

> **구현 에이전트에 반드시 "관련 테스트도 함께 수정하라"고 지시하라.**
> 이 지시 없이 코드만 수정하면, 에러 메시지 변경, mock 구조 변경 등으로 4~6건씩 테스트 실패가 발생한다. 함께 수정하면 실패 0건 달성 가능.

---

## 11. 에러 처리 원칙

### 응답 코드 사용 기준

| 코드 | 의미 | 사용 시점 |
|------|------|----------|
| 200 | 성공 | 정상 처리 |
| 201 | 생성됨 | POST로 리소스 생성 |
| 400 | 잘못된 요청 | 입력값 검증 실패 |
| 401 | 미인증 | 로그인 필요, 세션 만료 |
| 403 | 권한 없음 | 인증됐지만 권한 부족 |
| 404 | 없음 | 리소스 미존재 또는 소유권 없음 |
| 409 | 충돌 | 이미 존재 (중복 생성 시도) |
| 429 | 요청 과다 | rate limit 초과 |
| 500 | 서버 에러 | 예상 못한 에러 (로깅 필수) |

### 에러 응답 패턴

```typescript
// ✅ 사용자에게 보여줄 에러
return NextResponse.json(
  { error: "주문을 찾을 수 없습니다." },
  { status: 404 }
);

// ❌ 절대 하지 말 것
return NextResponse.json(
  { error: err.message, stack: err.stack, query: "SELECT..." },
  { status: 500 }
);

// 서버 에러 처리 패턴
try {
  // 비즈니스 로직
} catch (err) {
  console.error("[API] 주문 생성 실패:", err); // 서버 로그에만 기록
  return NextResponse.json(
    { error: "처리 중 오류가 발생했습니다." },
    { status: 500 }
  );
}
```

### 404 vs 403 결정

```
IDOR 방지를 위해, 소유권이 없는 리소스는 403이 아닌 404를 반환한다.
403은 "리소스가 존재하지만 접근 불가"를 의미 → 존재 여부 노출.
404는 "없는 것처럼 보임" → 정보 유출 방지.
```

---

## 12. 개발 프로세스

### 기획서 주도 개발

```
1. 기획서 작성 (무엇을, 왜, 어떻게)
2. 기획서 검증 (파일 경로, 현재 코드 상태 확인)
3. 구현 (기획서 기반, 병렬 에이전트 가능)
4. 테스트 (기능 + 보안 + 동시성)
5. 커밋 (변경 건수 + 테스트 결과 기록)
```

> **기획서 없이 구현하면 "구현 → 발견 → 수정 → 발견" 무한 루프에 빠진다.**
> 기획서를 먼저 쓰면 "검증 → 수정 → 구현" 한 번에 끝난다.

### 커밋 메시지 규칙

```
feat: 새 기능 추가
fix: 버그 수정
docs: 문서 작성/수정
refactor: 기능 변경 없는 코드 개선
test: 테스트 추가/수정
chore: 빌드, 설정 등 잡무
```

### 브랜치 전략

```
main          ← 운영 배포
├── develop   ← 개발 통합
│   ├── feat/기능명
│   └── fix/버그명
```

### 코드 리뷰 체크리스트

```
□ 인증/인가 확인했는가?
□ 입력값 검증이 있는가?
□ 에러 응답에 내부 정보가 없는가?
□ 트랜잭션이 필요한 곳에 적용했는가?
□ 관련 테스트를 함께 수정했는가?
□ 하드코딩된 값이 없는가? (환경변수 또는 상수)
```

---

## 13. 인프라 & 배포

### 운영 체크리스트

```
□ NODE_ENV=production
□ NEXTAUTH_SECRET 32자 이상 (랜덤 생성)
□ HTTPS 강제 (HSTS 헤더)
□ 보안 헤더 설정 (CSP, X-Frame-Options 등)
□ DB 백업 스케줄 설정
□ 로그 보존 기간 설정
□ 모니터링/알림 설정 (에러율, 응답 시간)
□ 환경변수가 .env.example과 일치하는지 확인
```

### 환경 분리

| 환경 | NODE_ENV | DB | 용도 |
|------|----------|-----|------|
| 로컬 | development | SQLite | 개발 |
| 스테이징 | production | PostgreSQL | 테스트 |
| 운영 | production | PostgreSQL | 실서비스 |

> **스테이징도 `NODE_ENV=production`으로 설정한다.** `development`로 두면 디버그 엔드포인트가 노출된다.

### 디버그 엔드포인트 가드

```typescript
// ✅ 올바른 패턴
if (process.env.NODE_ENV !== "development") {
  return NextResponse.json({ error: "Not available" }, { status: 404 });
}

// ❌ 잘못된 패턴 (스테이징에서 노출됨)
if (process.env.NODE_ENV === "production") { ... }
```

---

## 14. 보편적 실수와 교훈

### 실수 모음

| # | 실수 | 교훈 |
|---|------|------|
| 1 | SQLite로 시작해서 트랜잭션 타임아웃 | 동시성 필요하면 처음부터 PostgreSQL |
| 2 | 세션 토큰을 DB에 평문 저장 | SHA-256 해시 후 저장 |
| 3 | 해시된 값을 다시 해시 (이중 해시) | 해시 레이어 경계를 명확히 문서화 |
| 4 | WebSocket에 인증 없이 사용 | HTTP와 동일한 인증 수준 적용 |
| 5 | `err.message`를 응답에 포함 | 일반 에러 메시지로 대체 |
| 6 | 트랜잭션 밖에서 읽고 안에서 쓰기 | 항상 트랜잭션 내 fresh-read |
| 7 | `!value` 로 검증 | `typeof` + 명시적 비교 |
| 8 | `!!"false"` === `true` | boolean은 `typeof` 체크 |
| 9 | 소유권 없는 리소스에 403 반환 | 404 반환 (존재 여부 숨김) |
| 10 | 테스트 없이 코드 수정 | 기능과 테스트 동시 수정 |
| 11 | 에러 발생해도 테스트 통과 | catch 블록 안에서 assertion |
| 12 | 외부 API 할당량 초과 미대비 | 폴백 메커니즘 항상 준비 |
| 13 | 개발 중 보안 수정 반복 | 기능 완성 후 일괄 감사가 효율적 |
| 14 | 구현만 하고 테스트 안 고침 | 매번 4~6건 실패 → "테스트도 함께 수정" 지시 |
| 15 | 기획서 없이 바로 구현 | 기획서→검증→구현 순서가 재작업 방지 |

### 기억할 격언

> **"나중에 고치겠다"는 "안 고치겠다"와 같다.**
> 특히 보안 관련은 발견 즉시 수정. 기술 부채로 남기면 잊혀진다.

> **"Prisma가 알아서 해주겠지"는 위험하다.**
> ORM은 SQL 인젝션은 막아주지만, 비즈니스 로직 검증은 해주지 않는다.

> **"테스트 통과 = 안전"이 아니다.**
> 테스트는 작성한 케이스만 검증한다. 보안 감사는 "작성하지 않은 케이스"를 찾는 것이다.

> **구매자의 행동을 바꾸려 하지 마라.**
> 더 편한 수단을 제공해도 기존 습관을 바꾸기 어렵다. 구매자는 그대로 두고, 판매자 측 처리를 자동화하라. (웹 주문서 실패 경험)

---

---

## 15. 프론트엔드 설계

### 컴포넌트 구조 원칙

```
1. 컴포넌트는 하나의 책임만 (SRP)
2. 비즈니스 로직은 hooks로 분리, 컴포넌트는 렌더링만
3. 공유 컴포넌트는 props로만 통신 (전역 상태 직접 참조 금지)
4. 폼 처리는 react-hook-form 또는 server action 사용
5. 에러 바운더리를 라우트 단위로 배치
```

### 상태 관리 선택 기준

| 범위 | 도구 | 예시 |
|------|------|------|
| 서버 상태 | React Query / SWR | API 데이터 캐싱, 낙관적 업데이트 |
| 로컬 UI 상태 | useState / useReducer | 모달, 탭, 폼 입력 |
| 전역 클라이언트 상태 | Zustand / Jotai | 테마, 사용자 설정 |
| URL 상태 | searchParams / nuqs | 필터, 페이지네이션 |

> **"Redux가 필요한 경우는 거의 없다."** 서버 상태는 React Query가, 클라이언트 상태는 Zustand가 더 간결하게 처리한다.

### 접근성 (a11y) 체크리스트

```
□ 모든 이미지에 alt 텍스트
□ 폼 요소에 label 연결 (htmlFor)
□ 키보드만으로 모든 기능 사용 가능
□ 색상 대비 4.5:1 이상 (WCAG AA)
□ aria-live로 동적 콘텐츠 변경 알림
□ 포커스 관리 (모달 열면 모달 내부로 포커스 이동)
```

### SEO 기본

```
□ 페이지별 고유 title + meta description
□ Open Graph 태그 (og:title, og:image, og:description)
□ 시맨틱 HTML (header, main, nav, article, section)
□ sitemap.xml + robots.txt
□ Next.js metadata API 활용
```

### 실전 교훈

> **클라이언트 상태를 서버와 동기화하려 하지 마라.**
> 서버 상태는 React Query에 위임하고, 클라이언트는 UI 상태만 관리하라. 두 영역을 섞으면 일관성 버그의 늪에 빠진다.

---

## 16. 캐싱 & 성능 최적화

### 캐싱 전략 선택

| 계층 | 도구 | 용도 | TTL |
|------|------|------|-----|
| 브라우저 | Cache-Control 헤더 | 정적 자산 (JS, CSS, 이미지) | 1년 (immutable) |
| CDN | Vercel Edge / CloudFront | HTML, API 응답 | 10초~5분 |
| 앱 서버 | Redis / in-memory LRU | 세션, 자주 읽는 DB 결과 | 30초~10분 |
| DB | 쿼리 캐시 / 커넥션 풀 | 중복 쿼리 방지 | 자동 |

### N+1 쿼리 방지

```typescript
// ❌ N+1: 주문마다 고객을 별도 조회
const orders = await prisma.order.findMany();
for (const order of orders) {
  const customer = await prisma.customer.findUnique({ where: { id: order.customerId } });
}

// ✅ include로 한 번에 조회
const orders = await prisma.order.findMany({
  include: { customer: true },
});
```

### Core Web Vitals 기준

| 지표 | 목표 | 방법 |
|------|------|------|
| LCP (Largest Contentful Paint) | < 2.5초 | 이미지 최적화, 서버 응답 속도 |
| INP (Interaction to Next Paint) | < 200ms | 무거운 연산은 Web Worker로 |
| CLS (Cumulative Layout Shift) | < 0.1 | 이미지에 width/height 명시, 폰트 preload |

### 이미지 최적화

```
1. Next.js Image 컴포넌트 사용 (자동 리사이즈, WebP 변환)
2. 외부 이미지는 remotePatterns에 도메인 등록
3. 히어로 이미지는 priority 속성 추가
4. 아이콘은 SVG 인라인 (HTTP 요청 절감)
```

### 실전 교훈

> **"성능 최적화는 측정 후에 하라."**
> Lighthouse로 병목을 찾고 그 지점만 개선하라. 추측으로 최적화하면 복잡성만 늘고 효과는 미미하다.

---

## 17. 관측성 (Observability)

### 3대 축

| 축 | 도구 | 목적 |
|---|------|------|
| **로그** | Pino + Loki / CloudWatch | 구조화된 JSON 로그, 레벨별 필터링 |
| **메트릭** | Prometheus + Grafana | 응답 시간, 에러율, DB 커넥션 수 |
| **트레이싱** | OpenTelemetry + Jaeger | 요청 흐름 추적, 병목 식별 |

### 구조화된 로깅

```typescript
// ❌ 나쁜 예
console.log("주문 생성 실패");

// ✅ 좋은 예: 구조화된 JSON 로그
logger.error({
  event: "order_create_failed",
  orderId,
  userId,
  reason: "insufficient_balance",
  balance: currentBalance,
  requestedAmount: amount,
});
```

### 로그 레벨 기준

| 레벨 | 사용 시점 |
|------|----------|
| **error** | 시스템이 요청을 처리하지 못함 (알림 트리거) |
| **warn** | 처리는 됐지만 비정상 (rate limit 근접, 재시도 발생) |
| **info** | 정상적인 비즈니스 이벤트 (주문 생성, 결제 완료) |
| **debug** | 개발 시만 사용 (운영에서는 off) |

### 알림 규칙

```
□ 5xx 에러율 > 1% → 즉시 알림
□ 응답 시간 p95 > 3초 → 경고
□ DB 커넥션 사용률 > 80% → 경고
□ 디스크 사용량 > 90% → 즉시 알림
□ 인증 실패 10회/분 → 보안 알림
```

### 에러 추적 (Sentry)

```typescript
// Next.js + Sentry 기본 설정
Sentry.init({
  dsn: process.env.SENTRY_DSN,
  tracesSampleRate: 0.1,        // 운영: 10% 샘플링
  environment: process.env.NODE_ENV,
});

// API 핸들러에서
try {
  // 비즈니스 로직
} catch (err) {
  Sentry.captureException(err, {
    extra: { userId, endpoint: req.url },
  });
  return NextResponse.json({ error: "처리 중 오류" }, { status: 500 });
}
```

### 실전 교훈

> **"로그가 없으면 운영 사고는 미스터리로 남는다."**
> 최소한 error + info 레벨 로그는 프로덕션에서 반드시 수집하라. 1주일 보존만으로도 대부분의 사고 원인을 추적할 수 있다.

---

## 18. CI/CD 파이프라인

### 파이프라인 단계

```
Push → Lint → Type Check → Unit Test → Build → Deploy Staging → Smoke Test → Deploy Production
```

### GitHub Actions 기본 구조

```yaml
name: CI
on: [push, pull_request]
jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test
      - run: npm run build
```

### 배포 전 체크리스트

```
□ 모든 테스트 통과
□ TypeScript 컴파일 에러 0
□ ESLint 경고 0 (또는 허용 범위 내)
□ 환경변수 .env.example과 일치
□ DB 마이그레이션 준비 완료
□ 롤백 절차 확인
```

### 롤백 전략

| 상황 | 대응 |
|------|------|
| 배포 직후 5xx 급증 | 이전 버전으로 즉시 롤백 |
| DB 마이그레이션 실패 | 마이그레이션 되돌리기 (backward-compatible 설계 필수) |
| 기능 버그 발견 | feature flag로 비활성화 후 hotfix |

### Feature Flag 패턴

```typescript
// 환경변수 기반 간단한 feature flag
const FEATURES = {
  newCheckout: process.env.FEATURE_NEW_CHECKOUT === "true",
  betaDashboard: process.env.FEATURE_BETA_DASHBOARD === "true",
};

// 사용
if (FEATURES.newCheckout) {
  return <NewCheckoutFlow />;
}
return <LegacyCheckout />;
```

### 실전 교훈

> **"CI가 통과하지 않으면 머지하지 마라."**
> 예외를 한 번 허용하면 습관이 된다. CI 실패 = 머지 차단을 자동화하라.

---

---

## 19. 백그라운드 작업 & 큐

### [원칙] 언제 백그라운드로 보내는가

```
1. 응답 시간에 포함하면 안 되는 작업 (이메일 발송, PDF 생성, 알림 전송)
2. 재시도가 필요한 작업 (외부 API 호출, 결제 확인)
3. 스케줄링이 필요한 작업 (일일 정산, 만료 처리, 리포트 생성)
4. 무거운 연산 (이미지 리사이즈, 데이터 집계)
```

### [원칙] 큐 설계 규칙

| 원칙 | 이유 |
|------|------|
| **멱등성(idempotency) 필수** | 같은 작업이 2번 실행돼도 결과가 동일해야 한다 |
| **재시도 횟수 제한** | 무한 재시도는 시스템을 죽인다 (3~5회 + exponential backoff) |
| **dead letter queue** | 최종 실패한 작업을 별도 큐에 보관하여 수동 처리 |
| **작업 상태 추적** | pending → processing → completed / failed |
| **타임아웃 설정** | 한 작업이 큐를 점유하는 시간 제한 |

### [레시피] 도구 선택

| 규모 | 도구 | 비고 |
|------|------|------|
| 소규모 | `node-cron` + DB 상태 관리 | 별도 인프라 불필요 |
| 중규모 | BullMQ (Redis 기반) | Node.js 생태계 표준 |
| 대규모 | RabbitMQ / SQS / Kafka | 분산 시스템, 멀티 컨슈머 |
| Python | Celery + Redis/RabbitMQ | Django/Flask 표준 |

### 멱등성 패턴

```typescript
// [원칙] idempotency key로 중복 실행 방지
async function processPayment(idempotencyKey: string, amount: number) {
  const existing = await db.payment.findUnique({ where: { idempotencyKey } });
  if (existing) return existing; // 이미 처리됨 — 결과만 반환

  return await db.$transaction(async (tx) => {
    const payment = await tx.payment.create({
      data: { idempotencyKey, amount, status: "completed" },
    });
    return payment;
  });
}
```

---

## 20. 파일 업로드 & 스토리지

### [원칙] 파일 처리 규칙

```
1. 파일을 DB에 저장하지 마라 — 파일은 스토리지, 메타데이터만 DB
2. 업로드 전 검증: 파일 크기 상한, MIME 타입 화이트리스트, 파일명 정제
3. 사용자가 올린 파일명을 그대로 쓰지 마라 — UUID로 변환
4. 이미지는 업로드 시 리사이즈 (원본 + 썸네일)
5. 민감 파일은 서명된 URL(presigned URL)로만 접근 가능하게
6. 업로드 용량 제한: API 단위 (10MB), 사용자 단위 (1GB) 등 이중 제한
```

### [원칙] 스토리지 선택

| 규모 | 저장소 | 비고 |
|------|--------|------|
| 로컬 개발 | 파일 시스템 (`uploads/`) | gitignore에 추가 |
| 프로덕션 | S3 / R2 / GCS | CDN 연동 필수 |
| 데스크톱 앱 | 로컬 파일 시스템 | OS별 경로 분기 |

### [레시피] 안전한 업로드 핸들러

```typescript
// [원칙] MIME 타입 화이트리스트 + 크기 제한
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "application/pdf"];
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

function validateUpload(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type)) return "허용되지 않는 파일 형식";
  if (file.size > MAX_SIZE) return "파일 크기 초과 (최대 10MB)";
  return null; // 유효
}
```

---

## 21. 권한 모델 (RBAC)

### [원칙] 권한 설계

```
1. 인증(Authentication) ≠ 인가(Authorization) — 분리해서 다루라
2. 역할(Role)은 최소화 — admin, editor, viewer 3개면 대부분 충분
3. 리소스 소유권 확인은 역할과 별개로 항상 적용
4. 관리자라도 다른 사용자의 민감 데이터를 무분별하게 접근하면 안 됨
5. 권한 변경은 감사 로그 필수
```

### [원칙] 역할 설계 패턴

| 패턴 | 적합한 경우 | 예시 |
|------|-----------|------|
| **단순 역할** | 소규모 SaaS | admin, member |
| **계층 역할** | 조직 구조가 있는 서비스 | owner > admin > editor > viewer |
| **RBAC (역할 기반)** | 세밀한 권한 제어 | role → permissions 매핑 |
| **ABAC (속성 기반)** | 복잡한 규칙 | 부서 + 직급 + 시간대로 판단 |

### [레시피] 미들웨어 패턴

```typescript
// [원칙] 역할 확인을 미들웨어로 중앙화
function requireRole(allowedRoles: string[]) {
  return async (req, res, next) => {
    const user = req.user; // 인증 미들웨어에서 주입
    if (!user) return res.status(401).json({ error: "미인증" });
    if (!allowedRoles.includes(user.role)) {
      return res.status(404).json({ error: "Not found" }); // 403 대신 404 (IDOR 방지)
    }
    next();
  };
}

// 사용
app.delete("/api/users/:id", requireRole(["admin"]), deleteUserHandler);
```

### [원칙] 멀티테넌시

```
1. 모든 쿼리에 tenantId 필터 — ORM 미들웨어로 자동화
2. 테넌트 간 데이터 절대 교차 금지
3. URL에 테넌트 식별자 포함 (/org/:orgId/...) 또는 서브도메인
4. 관리자 API도 테넌트 스코프 내에서만 동작
```

---

## 22. API 버전관리 & 하위호환

### [원칙] 버전관리 규칙

```
1. 내부 API (자체 프론트엔드)는 버전관리 불필요 — 동시 배포하면 됨
2. 외부 API (제3자 사용)는 반드시 버전관리
3. 삭제보다 추가가 안전 — 필드 추가는 하위호환, 필드 삭제는 파괴적 변경
4. 폐기(deprecation)는 최소 3개월 전 공지
```

### [원칙] 하위호환 변경 vs 파괴적 변경

| 안전 (하위호환) | 위험 (파괴적) |
|----------------|--------------|
| 응답에 새 필드 추가 | 응답에서 기존 필드 제거 |
| 새 엔드포인트 추가 | 기존 엔드포인트 URL 변경 |
| 선택적 요청 파라미터 추가 | 필수 요청 파라미터 추가 |
| 에러 코드 추가 | 기존 에러 코드 의미 변경 |

### [레시피] URL 기반 버전관리

```
/api/v1/users     ← 현재 버전
/api/v2/users     ← 새 버전 (구조 변경 시)
```

### 실전 교훈

> **"내부 API도 버전관리 하자"는 함정.**
> 자체 프론트엔드만 쓰는 API에 v1/v2를 붙이면 유지보수 비용만 늘고, 어차피 프론트와 동시 배포한다. 외부 사용자가 있을 때만 버전관리하라.

---

## 23. 모바일 / 데스크톱 / CLI 확장

### [원칙] 플랫폼별 고려사항

| 플랫폼 | 핵심 차이 | 추가 고려 |
|--------|----------|----------|
| **모바일 (React Native / Flutter)** | 오프라인 지원, 푸시 알림, 앱스토어 심사 | 토큰 저장은 SecureStore, 네트워크 상태 체크 |
| **데스크톱 (Electron / Tauri)** | 파일 시스템 접근, 로컬 DB, 자동 업데이트 | OS별 경로 분기, 코드 서명 |
| **CLI** | stdin/stdout, 종료 코드, 인수 파싱 | --help 필수, JSON 출력 옵션, 파이프 지원 |
| **PWA** | 서비스 워커, 캐시 전략, 설치 프롬프트 | 오프라인 폴백 페이지 |

### [원칙] 공유 가능한 것 vs 분리해야 하는 것

```
공유 가능:
  ✓ 비즈니스 로직 (유틸리티 함수, 검증 로직)
  ✓ API 클라이언트 (타입 정의, 엔드포인트)
  ✓ 데이터 모델 (TypeScript 타입, 스키마)

분리 필수:
  ✗ UI 컴포넌트 (웹 ≠ 모바일 ≠ 데스크톱)
  ✗ 저장소 접근 (localStorage ≠ AsyncStorage ≠ fs)
  ✗ 인증 흐름 (쿠키 ≠ 토큰 ≠ OS keychain)
  ✗ 알림 (웹 푸시 ≠ FCM/APNs ≠ OS 알림)
```

### [원칙] 모바일 인증 패턴

```
1. JWT access token (15분 만료) + refresh token (30일)
2. Access token은 메모리에, refresh token은 SecureStore에
3. 401 응답 시 자동 refresh → 실패하면 로그인 화면으로
4. 생체 인증(Face ID / 지문)은 앱 잠금에만, 서버 인증과 분리
```

### [원칙] CLI 프로그램 규칙

```
1. --help, --version 필수
2. 성공 시 exit code 0, 실패 시 1
3. 에러 메시지는 stderr, 결과 데이터는 stdout
4. --json 옵션으로 파싱 가능한 출력 지원
5. 긴 작업은 프로그레스 바 또는 상태 메시지
6. 설정은 ~/.config/<app>/ 또는 환경변수
```

### 실전 교훈

> **"한 코드베이스로 모든 플랫폼"은 환상이다.**
> 비즈니스 로직은 공유하되, UI와 플랫폼 접근은 분리하라. 무리하게 통합하면 모든 플랫폼에서 2류가 된다.

---

---

## 24. 12-Factor 원칙

> 출처: [12factor.net](https://12factor.net/)

### [원칙] 핵심 12가지 (서비스 앱 필수)

| # | 원칙 | 요약 | 우리 바이블 연결 |
|---|------|------|----------------|
| 1 | Codebase | 하나의 코드베이스, 여러 배포 | §13 인프라 |
| 2 | Dependencies | 명시적 선언, 격리 | package.json, requirements.txt |
| 3 | Config | 환경변수로 관리, 코드에 넣지 않기 | §2 초기 설정 |
| 4 | Backing Services | DB, 캐시, 큐를 교체 가능한 리소스로 | §3 DB, §16 캐싱 |
| 5 | Build/Release/Run | 빌드→릴리스→실행 엄격 분리 | §18 CI/CD |
| 6 | Processes | **상태 없는 프로세스** — 세션은 외부 저장소에 | §5 인증 |
| 7 | Port Binding | 자체 포트로 서비스 노출 | §9 WebSocket |
| 8 | Concurrency | 수평 확장 (프로세스 복제) | §19 백그라운드 |
| 9 | Disposability | 빠른 시작, 우아한 종료 | §18 롤백 |
| 10 | Dev/Prod Parity | 개발=스테이징=운영 최대한 동일 | §13 인프라 |
| 11 | Logs | 로그는 stdout 이벤트 스트림 | §17 관측성 |
| 12 | Admin Processes | 마이그레이션, 일회성 스크립트도 동일 환경 | §3 DB |

### 실전 교훈

> **"12개 전부 지키려 하지 마라."**
> MVP에서는 3(Config), 5(Build/Run), 6(Stateless), 10(Dev/Prod Parity)만 지켜도 80%의 가치를 얻는다. 나머지는 서비스가 성장하면서 점진적으로 적용하라.

---

## 25. 코드 리뷰

> 출처: [Google Engineering Practices](https://google.github.io/eng-practices/review/)

### [원칙] 코드 리뷰의 목적

```
코드 리뷰는 "완벽한 코드"를 만드는 것이 아니라 "더 나은 코드"를 만드는 것이다.
리뷰어는 작성자가 모든 것을 완벽하게 다듬을 때까지 블로킹하면 안 된다.
— Google Engineering Practices
```

### [원칙] 리뷰어 체크리스트

```
□ 기능: 의도대로 동작하는가?
□ 복잡성: 더 단순하게 만들 수 있는가?
□ 테스트: 올바르고 잘 설계된 테스트가 있는가?
□ 네이밍: 변수, 함수, 클래스 이름이 명확한가?
□ 주석: 왜(why)를 설명하는가? (무엇(what)은 코드가 말해야 한다)
□ 스타일: 프로젝트 컨벤션을 따르는가?
□ 보안: 입력 검증, 인증/인가, 에러 노출이 안전한가?
```

### [원칙] 리뷰 요청자 규칙

```
1. PR은 작게 — 200줄 이하가 이상적, 400줄 초과는 분할
2. 자체 리뷰를 먼저 — 제출 전에 diff를 한 번 읽어라
3. 설명을 써라 — "왜" 이 변경이 필요한지 PR 설명에 기록
4. 리뷰어 피드백에 방어적이지 마라 — 코드는 소유물이 아니다
```

### AI 에이전트 코드 리뷰 시

```
□ 에이전트 출력물도 동일한 리뷰 기준 적용
□ "구현만 하고 테스트 안 고침" 패턴 주의 (§14 실수 #14)
□ 에이전트가 만든 코드에 주석이 과도하면 제거
□ 에이전트는 반론을 못 하므로 리뷰어가 더 꼼꼼해야 한다
```

---

## 26. DB 성능 튜닝 (심화)

> 출처: [PostgreSQL Best Practices](https://dev.to/_d7eb1c1703182e3ce1782/postgresql-performance-tuning-checklist-2026-complete-guide-65a)

### [원칙] 인덱스 전략

| 인덱스 타입 | 용도 | 언제 |
|-----------|------|------|
| B-tree (기본) | 등호, 범위 검색 | WHERE, ORDER BY 대상 컬럼 |
| GIN | 배열, JSONB, 전문 검색 | JSONB 필드 조회 시 |
| BRIN | 대용량 시계열 데이터 | createdAt 순서가 보장된 테이블 |
| Partial | 조건부 인덱스 | `WHERE status = 'active'`만 인덱싱 |

### [원칙] 쿼리 최적화 규칙

```
1. SELECT * 금지 — 필요한 컬럼만 명시
2. N+1 쿼리 감지 — ORM의 include/join 활용
3. EXPLAIN ANALYZE로 실행 계획 확인
4. 100만 행 이상이면 파티셔닝 고려
5. 느린 쿼리 로그 활성화 (1초 이상)
```

### [원칙] 커넥션 관리

```
1. 커넥션 풀 사용 필수 (PgBouncer 또는 ORM 내장 풀)
2. 풀 크기 = CPU 코어 수 × 2 + 디스크 수 (기본 가이드)
3. 트랜잭션은 가능한 짧게 — 장시간 트랜잭션은 lock 경합 유발
4. IDLE 커넥션 타임아웃 설정
```

### [레시피] PostgreSQL 설정 (프로덕션)

```
shared_buffers = 총 RAM의 25~40%
work_mem = 64MB (복잡한 쿼리용)
maintenance_work_mem = 512MB (VACUUM, CREATE INDEX용)
log_min_duration_statement = 1000 (1초 이상 쿼리 로깅)
```

---

## 27. 커뮤니티 & UGC 관리

### [원칙] 사용자 생성 콘텐츠(UGC) 처리

```
1. 모든 UGC는 XSS 정제 후 저장/표시
2. 이미지/파일 업로드는 §20 규칙 적용
3. HTML 허용 시 화이트리스트 기반 정제 (sanitize-html 등)
4. Markdown은 서버에서 렌더링 후 HTML로 저장 (클라이언트 렌더링 XSS 주의)
```

### [원칙] 콘텐츠 모더레이션

| 방식 | 설명 | 적합한 경우 |
|------|------|-----------|
| **사전 검수** | 게시 전 관리자 승인 | 민감한 커뮤니티, 초기 단계 |
| **사후 검수** | 게시 즉시, 신고 시 검토 | 대규모 커뮤니티 |
| **자동 필터** | 금칙어, 스팸 패턴 자동 차단 | 모든 규모 |
| **AI 필터** | 유해 콘텐츠 자동 감지 | 대규모 + 예산 있을 때 |

### [원칙] 신고/차단 시스템

```
1. 신고 버튼은 모든 콘텐츠에 — 사유 선택식 (스팸/욕설/사기/기타)
2. 신고 3건 이상 누적 → 자동 숨김 + 관리자 큐
3. 차단된 사용자의 기존 콘텐츠 처리 정책 사전 결정 (숨김 vs 삭제 vs 유지)
4. 차단 이력은 감사 로그에 기록
```

### [원칙] 커뮤니티 스케일링

```
1. 게시글/댓글은 커서 기반 페이지네이션 (오프셋은 대량 데이터에서 느림)
2. 인기글 정렬은 캐시 (Redis) — 매 요청마다 계산하지 않기
3. 알림은 비동기 큐로 (§19) — 동기 처리하면 게시 응답이 느려짐
4. 검색은 DB LIKE가 아닌 전문 검색 엔진 (Meilisearch, Elasticsearch)
```

---

## 28. 런칭 전 최종 체크리스트

> 출처: [Vercel Production Checklist](https://vercel.com/docs/production-checklist), [OWASP Top 10 2025](https://owasp.org/Top10/2025/)

### 보안

```
□ OWASP Top 10 2025 대응 확인 (특히 A01:접근제어, A03:공급망)
□ 모든 API에 인증 + 소유권 확인
□ 입력값 검증 누락 없음
□ 에러 응답에 내부 정보 없음
□ HTTPS 강제 + 보안 헤더 설정
□ 의존성 취약점 스캔 (npm audit / pip audit)
□ 환경변수에 시크릿 하드코딩 없음
□ rate limiting 적용
```

### 성능

```
□ Core Web Vitals 기준 충족 (LCP < 2.5s, INP < 200ms, CLS < 0.1)
□ 이미지 최적화 + lazy loading
□ DB 인덱스 확인 (느린 쿼리 로그 활성화)
□ 캐시 전략 적용 (CDN, Redis)
□ 번들 사이즈 확인 (코드 스플리팅)
```

### 운영

```
□ 에러 추적 설정 (Sentry 등)
□ 로그 수집 설정 (구조화된 JSON)
□ 알림 규칙 설정 (5xx > 1%, p95 > 3초)
□ 백업 스케줄 확인
□ 롤백 절차 문서화
□ 도메인 + SSL 인증서 설정
□ 개인정보처리방침 / 이용약관 페이지
```

### 접근성

```
□ 키보드 네비게이션 동작
□ 스크린 리더 테스트
□ 색상 대비 4.5:1 이상
□ 폼에 label 연결
```

---

## 29. 참조 문서 & 출처

이 바이블은 아래 문서들의 원칙을 참조하여 작성되었습니다.

| 문서 | URL | 핵심 |
|------|-----|------|
| 12-Factor App | https://12factor.net/ | SaaS 12원칙 |
| Google Engineering Practices | https://google.github.io/eng-practices/review/ | 코드 리뷰 표준 |
| Microsoft REST API Guidelines | https://github.com/microsoft/api-guidelines | API 설계 |
| OWASP Top 10 (2025) | https://owasp.org/Top10/2025/ | 보안 위협 |
| Node.js Best Practices | https://github.com/goldbergyoni/nodebestpractices | Node.js 체크리스트 |
| Vercel Production Checklist | https://vercel.com/docs/production-checklist | 런칭 체크 |
| PostgreSQL Tuning Guide | https://dev.to/_d7eb1c1703182e3ce1782 | DB 성능 |
| Tauri Security | https://v2.tauri.app/security/ | 데스크톱 보안 |
| Express Security Best Practices | https://expressjs.com/en/advanced/best-practice-security.html | Express 보안 |

---

> **이 문서는 프로젝트를 거듭할수록 업데이트됩니다.**
> 새로운 프로젝트에서 얻은 교훈을 추가하고, 검증된 원칙은 강화합니다.
> 마지막 업데이트: 2026-03-24
