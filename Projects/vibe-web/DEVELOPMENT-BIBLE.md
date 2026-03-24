# 웹 개발 제작 바이블

> **목적**: 프로젝트 유형에 관계없이 적용할 수 있는 웹 개발 원칙과 경험 기록.
> **기반**: ShortLive Shop Helper (라이브 커머스 SaaS) 개발에서 축적한 실전 경험.
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

---

## 1. 기술 스택 선정 기준

### 프로젝트 유형별 추천

| 유형 | 프레임워크 | DB | 인증 | 실시간 |
|------|-----------|-----|------|--------|
| MVP / 1인 개발 | Next.js (App Router) | SQLite → PostgreSQL | NextAuth | Socket.IO |
| 포털 / 대규모 | Next.js 또는 별도 FE+BE | PostgreSQL | NextAuth 또는 자체 | Socket.IO / SSE |
| 관리자 도구 | Next.js | PostgreSQL | NextAuth | 불필요 또는 SSE |
| API 서비스 | Fastify / Express | PostgreSQL | JWT 자체 구현 | WebSocket |

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

> **이 문서는 프로젝트를 거듭할수록 업데이트됩니다.**
> 새로운 프로젝트에서 얻은 교훈을 추가하고, 검증된 원칙은 강화합니다.
> 마지막 업데이트: 2026-03-24
