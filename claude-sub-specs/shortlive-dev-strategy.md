# ShortLive Shop Helper — Phase 1 MVP 개발 전략

> Claude Code에게 순차적으로 전달하여 프로젝트를 처음부터 빌드하기 위한 마스터 가이드.
> 각 Step의 프롬프트는 자급자족(self-contained)이며, 외부 문서 참조 없이 실행 가능하다.

---

## 1. 개요

### 프로젝트 한 줄 요약
유튜브/틱톡 라이브 방송에서 채팅 명령어(`!주문 사과 3`)로 자동 주문을 생성하고, 입금 확인 및 미입금 자동 취소까지 관리하는 웹 애플리케이션.

### 기술 스택 요약
| 레이어 | 기술 |
|--------|------|
| 프레임워크 | Next.js 15 (App Router) + TypeScript |
| DB | SQLite + Prisma ORM |
| 실시간 | Socket.IO |
| YouTube 채팅 | `youtube-chat` npm |
| UI | Tailwind CSS + shadcn/ui |
| 인증 | NextAuth.js v5 (Auth.js) |
| 상태 관리 | Zustand |
| 스케줄러 | `node-cron` |

### MVP 범위

**포함:**
- 프로젝트 스캐폴딩 및 DB 스키마
- 커스텀 서버 (Socket.IO)
- 이메일/비밀번호 인증
- 상품 CRUD + 별칭 관리
- YouTube 채팅 커넥터 + 명령어 파서 + 메시지 dedup
- 주문 생성 (트랜잭션, reservedStock, 주문번호, 쿨다운/한도)
- Socket.IO 실시간 대시보드
- 수동 입금 확인 (Tier 3) + CustomerMapping 생성 제안
- 미입금 자동취소 스케줄러

**제외:**
- TikTok 채팅 커넥터 (Phase 3)
- 은행 엑셀 업로드 / 오픈뱅킹 연동 (Phase 2, 4)
- 이름 퍼지 매칭 알고리즘 (Phase 2)
- 배송 상태 관리 (Phase 3)
- 멀티 인스턴스 / 수평 확장
- 모바일 반응형 최적화 (Phase 3)

### 운영 전제
- **단일 self-hosted 인스턴스** (멀티 인스턴스 범위 밖)
- **SQLite** (단일 프로세스 쓰기)
- **`node-cron`** 스케줄러 (단일 실행자)
- **`global` 객체**에 Socket.IO, ChatManager 저장 (단일 프로세스 전제)
- **동시 접속**: 판매자 1~5명, 동시 방송 1~2개
- 서버 재시작 시 활성 방송 연결 유실 허용

---

## 2. 사전 준비 (Step 0)

### 프로젝트 생성

```bash
npx create-next-app@latest shortlive-shop-helper \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --no-turbopack
```

### npm 패키지 설치

```bash
# Core
npm install prisma @prisma/client
npm install next-auth@beta @auth/prisma-adapter
npm install socket.io socket.io-client
npm install youtube-chat
npm install zustand
npm install node-cron
npm install bcryptjs

# UI
npx shadcn@latest init
# shadcn 컴포넌트는 필요할 때 개별 설치

# Dev
npm install -D @types/node @types/bcryptjs @types/node-cron
npm install -D tsx
```

### `.env.local` 초기 내용

```env
DATABASE_URL="file:./dev.db"
NEXTAUTH_SECRET="dev-secret-change-in-production"
NEXTAUTH_URL="http://localhost:3000"
```

### 초기 디렉토리 구조 생성

```bash
mkdir -p prisma
mkdir -p src/lib/chat
mkdir -p src/lib/payment
mkdir -p src/lib/order
mkdir -p src/lib/utils
mkdir -p src/components/ui
mkdir -p src/components/layout
mkdir -p src/components/live
mkdir -p src/components/orders
mkdir -p src/components/payments
mkdir -p src/components/products
mkdir -p src/hooks
mkdir -p src/stores
mkdir -p src/types
```

---

## 3. Phase 1 단계별 실행 계획

---

## Step 1: 프로젝트 스캐폴딩

### 의존성
- 선행 단계: Step 0 (프로젝트 생성, 패키지 설치 완료)
- 필요 파일: 없음 (초기 설정)

### 목표
Next.js 15 프로젝트가 `npm run dev`로 정상 실행되고, Prisma 클라이언트 싱글턴이 설정되며, 기본 레이아웃과 타입 정의가 준비된다.

### Claude Code 프롬프트

```
프로젝트 shortlive-shop-helper의 기본 설정을 완료하라.

1. `src/lib/db.ts` — Prisma 클라이언트 싱글턴:
```typescript
import { PrismaClient } from "@prisma/client";

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

export const prisma = globalForPrisma.prisma ?? new PrismaClient();

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;
```

2. `src/types/order.ts`:
```typescript
export type OrderStatus = "입금대기" | "입금확인" | "취소";

export interface OrderWithItems {
  id: string;
  orderNumber: string;
  chatDisplayName: string;
  status: OrderStatus;
  totalAmount: number;
  cancelDeadline: Date | null;
  paidAt: Date | null;
  createdAt: Date;
  items: {
    id: string;
    productName: string;
    quantity: number;
    unitPrice: number;
    option: string | null;
  }[];
}
```

3. `src/types/product.ts`:
```typescript
export interface ProductOption {
  name: string;
  values: string[];
}

export interface ProductWithStock {
  id: string;
  name: string;
  aliases: string[];
  price: number;
  stock: number;
  reservedStock: number;
  availableStock: number; // computed: stock - reservedStock
  category: string | null;
  options: ProductOption[];
  isActive: boolean;
}
```

4. `src/types/chat.ts`:
```typescript
export interface ChatMessage {
  platform: "youtube" | "tiktok";
  platformMessageId: string | null;
  userId: string;
  displayName: string;
  message: string;
  timestamp: Date;
}

export interface ParsedOrder {
  productName: string;
  quantity: number;
  rawMessage: string;
}
```

5. `src/types/payment.ts`:
```typescript
export interface ManualPaymentInput {
  orderId: string;
  depositorName: string;
  amount: number;
}
```

6. `next.config.ts` — 커스텀 서버 사용을 위한 설정 (output standalone은 불필요, 개발 시 tsx로 server.ts 실행):
기본 설정 유지. 특별한 변경 불필요.

7. `package.json`의 scripts 수정:
```json
{
  "scripts": {
    "dev": "tsx server.ts",
    "build": "next build",
    "start": "NODE_ENV=production tsx server.ts"
  }
}
```

8. `tsconfig.json`에서 paths 확인:
```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

모든 파일을 생성하고, `npx tsc --noEmit`으로 타입 에러가 없는지 확인하라.
```

### 생성/수정 파일
- `src/lib/db.ts`
- `src/types/order.ts`
- `src/types/product.ts`
- `src/types/chat.ts`
- `src/types/payment.ts`
- `package.json` (scripts 수정)

### 검증 방법
- `npx tsc --noEmit` 통과
- `npm run dev` 실행 시 서버가 시작되지 않아도 됨 (server.ts 미작성 상태이므로)
- 각 타입 파일이 올바르게 import 가능

---

## Step 2: DB 스키마 작성 + 마이그레이션

### 의존성
- 선행 단계: Step 1 (Prisma 클라이언트 싱글턴)
- 필요 파일: `src/lib/db.ts`

### 목표
Prisma 스키마에 모든 MVP 테이블이 정의되고, SQLite 마이그레이션이 성공하며, `npx prisma studio`로 테이블 구조를 확인할 수 있다.

### Claude Code 프롬프트

```
Prisma 스키마를 작성하고 마이그레이션을 실행하라.

`prisma/schema.prisma` 파일을 다음과 같이 작성하라:

```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "sqlite"
  url      = env("DATABASE_URL")
}

model Seller {
  id                 String   @id @default(cuid())
  email              String   @unique
  passwordHash       String
  shopName           String
  bankName           String?
  bankAccount        String?
  accountHolder      String?
  autoCancel         Int      @default(30)    // 자동취소 시간 (분)
  maxPendingPerUser  Int      @default(3)     // 사용자별 동시 입금대기 한도
  orderCooldown      Int      @default(10)    // 동일 사용자 주문 간격 (초)
  createdAt          DateTime @default(now())
  updatedAt          DateTime @updatedAt

  products           Product[]
  liveSessions       LiveSession[]
  orders             Order[]
  customerMappings   CustomerMapping[]
  bankTransactions   BankTransaction[]
}

model Product {
  id             String   @id @default(cuid())
  sellerId       String
  name           String
  aliases        String?  // JSON 배열: ["빨간사과","홍옥"]
  price          Int
  stock          Int
  reservedStock  Int      @default(0)
  category       String?
  options        String?  // JSON: [{"name":"사이즈","values":["소","중","대"]}]
  isActive       Boolean  @default(true)
  createdAt      DateTime @default(now())
  updatedAt      DateTime @updatedAt

  seller         Seller     @relation(fields: [sellerId], references: [id])
  orderItems     OrderItem[]

  @@index([sellerId])
}

model LiveSession {
  id            String    @id @default(cuid())
  sellerId      String
  platform      String    // "youtube" | "tiktok"
  channelId     String
  status        String    @default("active") // "active" | "ended"
  startedAt     DateTime  @default(now())
  endedAt       DateTime?
  totalOrders   Int       @default(0)
  totalRevenue  Int       @default(0)
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt

  seller        Seller        @relation(fields: [sellerId], references: [id])
  orders        Order[]
  chatMessages  ChatMessage[]

  @@index([sellerId])
}

model Order {
  id               String    @id @default(cuid())
  orderNumber      String    @unique
  sellerId         String
  liveSessionId    String?
  chatPlatform     String
  chatUserId       String
  chatDisplayName  String
  status           String    @default("입금대기") // "입금대기" | "입금확인" | "취소"
  totalAmount      Int
  cancelDeadline   DateTime?
  paidAt           DateTime?
  recipientName    String?
  recipientPhone   String?
  shippingAddress  String?
  note             String?
  createdAt        DateTime  @default(now())
  updatedAt        DateTime  @updatedAt

  seller           Seller       @relation(fields: [sellerId], references: [id])
  liveSession      LiveSession? @relation(fields: [liveSessionId], references: [id])
  items            OrderItem[]
  payment          Payment?
  bankTransactions BankTransaction[]

  @@index([sellerId])
  @@index([status])
  @@index([liveSessionId])
  @@index([chatUserId])
}

model OrderItem {
  id          String @id @default(cuid())
  orderId     String
  productId   String
  productName String
  quantity    Int
  unitPrice   Int
  option      String?
  createdAt   DateTime @default(now())

  order       Order   @relation(fields: [orderId], references: [id])
  product     Product @relation(fields: [productId], references: [id])

  @@index([orderId])
}

model BankTransaction {
  id              String    @id @default(cuid())
  sellerId        String
  source          String    // "excel" | "openbanking"
  bankName        String?
  depositorName   String
  amount          Int
  transactedAt    DateTime
  referenceId     String?
  status          String    @default("unmatched") // "unmatched" | "matched" | "ignored"
  matchedOrderId  String?
  uploadBatchId   String?
  createdAt       DateTime  @default(now())
  updatedAt       DateTime  @updatedAt

  seller          Seller   @relation(fields: [sellerId], references: [id])
  matchedOrder    Order?   @relation(fields: [matchedOrderId], references: [id])
  payment         Payment?

  @@unique([sellerId, referenceId])
  @@index([sellerId])
  @@index([status])
}

model Payment {
  id                 String    @id @default(cuid())
  orderId            String    @unique
  bankTransactionId  String?   @unique
  method             String    // "openbanking" | "excel" | "manual"
  depositorName      String
  amount             Int
  matchConfidence    Float?
  verifiedAt         DateTime  @default(now())
  verifiedBy         String    // "auto" | "manual"
  createdAt          DateTime  @default(now())

  order              Order           @relation(fields: [orderId], references: [id])
  bankTransaction    BankTransaction? @relation(fields: [bankTransactionId], references: [id])
}

model CustomerMapping {
  id               String @id @default(cuid())
  sellerId         String
  chatPlatform     String
  chatUserId       String
  chatDisplayName  String
  realName         String
  phone            String?
  address          String?
  createdAt        DateTime @default(now())
  updatedAt        DateTime @updatedAt

  seller           Seller @relation(fields: [sellerId], references: [id])

  @@unique([sellerId, chatPlatform, chatUserId])
  @@index([sellerId])
}

model ChatMessage {
  id                  String  @id @default(cuid())
  liveSessionId       String
  platform            String
  platformMessageId   String?
  userId              String
  displayName         String
  message             String
  isOrder             Boolean @default(false)
  processedOrderId    String?
  createdAt           DateTime @default(now())

  liveSession         LiveSession @relation(fields: [liveSessionId], references: [id])

  @@unique([liveSessionId, platform, platformMessageId])
  @@index([liveSessionId])
  @@index([userId])
}
```

마이그레이션 실행:
```bash
npx prisma migrate dev --name init
npx prisma generate
```

시드 파일 `prisma/seed.ts` 작성:
```typescript
import { PrismaClient } from "@prisma/client";
import { hash } from "bcryptjs";

const prisma = new PrismaClient();

async function main() {
  const passwordHash = await hash("test1234", 12);

  const seller = await prisma.seller.create({
    data: {
      email: "test@example.com",
      passwordHash,
      shopName: "테스트 상점",
      bankName: "국민은행",
      bankAccount: "123-456-789",
      accountHolder: "홍길동",
    },
  });

  await prisma.product.createMany({
    data: [
      { sellerId: seller.id, name: "사과", aliases: JSON.stringify(["빨간사과", "홍옥"]), price: 3000, stock: 100 },
      { sellerId: seller.id, name: "딸기", aliases: JSON.stringify(["생딸기"]), price: 5000, stock: 50 },
      { sellerId: seller.id, name: "포도", aliases: null, price: 8000, stock: 30 },
    ],
  });

  console.log("Seed 완료:", seller.email);
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
```

`package.json`에 prisma seed 설정 추가:
```json
{
  "prisma": {
    "seed": "tsx prisma/seed.ts"
  }
}
```

시드 실행:
```bash
npx prisma db seed
```
```

### 생성/수정 파일
- `prisma/schema.prisma`
- `prisma/seed.ts`
- `package.json` (prisma seed 설정 추가)
- `prisma/migrations/` (자동 생성)

### 검증 방법
- `npx prisma migrate dev --name init` 성공
- `npx prisma generate` 성공
- `npx prisma db seed` 성공
- `npx prisma studio`로 테이블 구조 및 시드 데이터 확인

---

## Step 3: 커스텀 서버 설정

### 의존성
- 선행 단계: Step 2 (DB 마이그레이션, Prisma 클라이언트)
- 필요 파일: `src/lib/db.ts`, `prisma/schema.prisma`

### 목표
`npm run dev`로 커스텀 서버가 시작되고, Socket.IO가 연결 가능하며, Next.js 페이지가 정상 렌더링된다.

### Claude Code 프롬프트

```
커스텀 서버를 설정하라. Next.js API Route는 stateless이므로, Socket.IO와 채팅 커넥터를 위해 커스텀 서버가 필요하다.

1. `server.ts` (프로젝트 루트):
```typescript
import { createServer } from "http";
import next from "next";
import { Server as SocketIOServer } from "socket.io";

const dev = process.env.NODE_ENV !== "production";
const app = next({ dev });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const httpServer = createServer((req, res) => {
    handle(req, res);
  });

  const io = new SocketIOServer(httpServer, {
    cors: {
      origin: process.env.NEXTAUTH_URL || "http://localhost:3000",
      methods: ["GET", "POST"],
    },
  });

  // 전역 접근 (단일 인스턴스 MVP 전제)
  (global as any).__socketIO = io;

  io.on("connection", (socket) => {
    console.log("Socket connected:", socket.id);

    socket.on("join-seller", (sellerId: string) => {
      socket.join(`seller:${sellerId}`);
      console.log(`Socket ${socket.id} joined seller:${sellerId}`);
    });

    socket.on("disconnect", () => {
      console.log("Socket disconnected:", socket.id);
    });
  });

  const port = parseInt(process.env.PORT || "3000", 10);
  httpServer.listen(port, () => {
    console.log(`> Server ready on http://localhost:${port}`);
  });
});
```

2. `src/lib/socket.ts` — Socket.IO 서버 유틸리티:
```typescript
import { Server as SocketIOServer } from "socket.io";

export function getIO(): SocketIOServer {
  const io = (global as any).__socketIO;
  if (!io) {
    throw new Error("Socket.IO not initialized. Is the custom server running?");
  }
  return io;
}

// 판매자 방으로 이벤트 전송
export function emitToSeller(sellerId: string, event: string, data: any) {
  const io = getIO();
  io.to(`seller:${sellerId}`).emit(event, data);
}
```

3. `src/hooks/use-socket.ts` — 클라이언트 측 Socket.IO 훅:
```typescript
"use client";

import { useEffect, useRef, useState } from "react";
import { io, Socket } from "socket.io-client";

export function useSocket(sellerId: string | null) {
  const socketRef = useRef<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!sellerId) return;

    const socket = io({
      path: "/socket.io",
    });

    socket.on("connect", () => {
      setIsConnected(true);
      socket.emit("join-seller", sellerId);
    });

    socket.on("disconnect", () => {
      setIsConnected(false);
    });

    socketRef.current = socket;

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [sellerId]);

  return { socket: socketRef.current, isConnected };
}
```

`npm run dev`를 실행하여 서버가 정상 시작되는지 확인하라. 브라우저에서 `http://localhost:3000`에 접속하여 Next.js 기본 페이지가 렌더링되는지 확인하라.
```

### 생성/수정 파일
- `server.ts`
- `src/lib/socket.ts`
- `src/hooks/use-socket.ts`

### 검증 방법
- `npm run dev` 실행 시 `> Server ready on http://localhost:3000` 메시지 출력
- 브라우저에서 `http://localhost:3000` 접속 시 Next.js 페이지 렌더링
- 브라우저 개발자 도구 Network 탭에서 WebSocket 연결 확인

---

## Step 4: 인증 시스템

### 의존성
- 선행 단계: Step 2 (Seller 테이블), Step 3 (서버)
- 필요 파일: `prisma/schema.prisma`, `src/lib/db.ts`, `server.ts`

### 목표
이메일/비밀번호로 회원가입, 로그인, 로그아웃이 가능하고, 인증되지 않은 사용자는 대시보드에 접근할 수 없다.

### Claude Code 프롬프트

```
NextAuth.js v5(Auth.js)를 사용하여 이메일/비밀번호 인증 시스템을 구현하라.

DB의 Seller 모델을 사용자 테이블로 사용한다 (별도의 User 테이블은 만들지 않는다).

1. `src/lib/auth.ts` — NextAuth 설정:
```typescript
import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { compare } from "bcryptjs";
import { prisma } from "@/lib/db";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "이메일", type: "email" },
        password: { label: "비밀번호", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const seller = await prisma.seller.findUnique({
          where: { email: credentials.email as string },
        });

        if (!seller) return null;

        const isValid = await compare(
          credentials.password as string,
          seller.passwordHash
        );

        if (!isValid) return null;

        return {
          id: seller.id,
          email: seller.email,
          name: seller.shopName,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.sellerId = user.id;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).sellerId = token.sellerId;
      }
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
  },
});
```

2. `src/app/api/auth/[...nextauth]/route.ts`:
```typescript
import { handlers } from "@/lib/auth";
export const { GET, POST } = handlers;
```

3. `src/app/api/auth/register/route.ts` — 회원가입 API:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { hash } from "bcryptjs";
import { prisma } from "@/lib/db";

export async function POST(req: NextRequest) {
  const { email, password, shopName } = await req.json();

  if (!email || !password || !shopName) {
    return NextResponse.json({ error: "필수 정보를 입력하세요." }, { status: 400 });
  }

  const exists = await prisma.seller.findUnique({ where: { email } });
  if (exists) {
    return NextResponse.json({ error: "이미 등록된 이메일입니다." }, { status: 409 });
  }

  const passwordHash = await hash(password, 12);
  const seller = await prisma.seller.create({
    data: { email, passwordHash, shopName },
  });

  return NextResponse.json({ id: seller.id, email: seller.email }, { status: 201 });
}
```

4. `src/app/(auth)/login/page.tsx` — 로그인 페이지:
이메일, 비밀번호 입력 폼. 로그인 성공 시 `/` (대시보드)로 리다이렉트.
`signIn("credentials", { email, password, redirect: false })`로 로그인 처리.
에러 시 "이메일 또는 비밀번호가 올바르지 않습니다." 메시지 표시.
회원가입 링크 포함.

5. `src/app/(auth)/register/page.tsx` — 회원가입 페이지:
이메일, 비밀번호, 상점명 입력 폼. `/api/auth/register`로 POST.
성공 시 로그인 페이지로 리다이렉트.

6. `src/middleware.ts` — 인증 미들웨어:
```typescript
import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

export default auth((req) => {
  const isLoggedIn = !!req.auth;
  const isAuthPage = req.nextUrl.pathname.startsWith("/login") ||
                     req.nextUrl.pathname.startsWith("/register");

  if (isAuthPage) {
    if (isLoggedIn) {
      return NextResponse.redirect(new URL("/", req.url));
    }
    return NextResponse.next();
  }

  if (!isLoggedIn) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
```

7. 타입 확장 `src/types/next-auth.d.ts`:
```typescript
import "next-auth";

declare module "next-auth" {
  interface Session {
    user: {
      sellerId: string;
      email: string;
      name: string;
    };
  }
}
```

로그인/회원가입 페이지에는 최소한의 Tailwind 스타일을 적용하라. shadcn/ui의 Button, Input, Card 컴포넌트를 사용하라 (`npx shadcn@latest add button input card label`).
```

### 생성/수정 파일
- `src/lib/auth.ts`
- `src/app/api/auth/[...nextauth]/route.ts`
- `src/app/api/auth/register/route.ts`
- `src/app/(auth)/login/page.tsx`
- `src/app/(auth)/register/page.tsx`
- `src/middleware.ts`
- `src/types/next-auth.d.ts`

### 검증 방법
- `/register`에서 새 계정 생성 성공
- `/login`에서 생성한 계정으로 로그인 성공
- 로그인 후 `/`로 리다이렉트 확인
- 로그아웃 후 `/`에 접근 시 `/login`으로 리다이렉트 확인
- 시드 계정(`test@example.com` / `test1234`)으로 로그인 가능

---

## Step 5: 상품 CRUD

### 의존성
- 선행 단계: Step 4 (인증 시스템)
- 필요 파일: `src/lib/auth.ts`, `src/lib/db.ts`, `prisma/schema.prisma`

### 목표
판매자가 상품을 등록/수정/삭제/조회할 수 있고, 별칭(aliases) 관리가 가능하다. 재고 표시에서 `availableStock = stock - reservedStock`이 반영된다.

### Claude Code 프롬프트

```
상품 CRUD API와 UI를 구현하라. 인증된 판매자만 자신의 상품에 접근할 수 있다.

**인증 헬퍼** — 각 API에서 사용할 세션 확인 함수:
```typescript
// src/lib/api-utils.ts
import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

export async function getAuthenticatedSeller() {
  const session = await auth();
  if (!session?.user?.sellerId) {
    return { error: NextResponse.json({ error: "인증 필요" }, { status: 401 }), sellerId: null };
  }
  return { error: null, sellerId: session.user.sellerId };
}
```

**API 엔드포인트:**

1. `GET /api/products` — 상품 목록
   - 쿼리: `?search=사과&category=과일&page=1&limit=20`
   - 응답: `{ products: [...], total: number, page: number }`
   - 판매자의 `isActive=true`인 상품만 기본 조회 (쿼리에 `includeInactive=true` 시 전체)
   - 각 상품에 `availableStock: stock - reservedStock` 계산 필드 포함

2. `POST /api/products` — 상품 등록
   - 바디: `{ name, price, stock, category?, aliases?: string[], options?: {name: string, values: string[]}[] }`
   - `aliases`는 JSON 문자열로 변환하여 저장: `JSON.stringify(aliases)`
   - `options`도 JSON 문자열로 저장: `JSON.stringify(options)`

3. `GET /api/products/[id]` — 상품 상세
   - 판매자 소유 확인 필수

4. `PUT /api/products/[id]` — 상품 수정
   - 판매자 소유 확인 필수
   - name, price, stock, category, aliases, options, isActive 수정 가능

5. `DELETE /api/products/[id]` — 상품 소프트 삭제
   - `isActive = false`로 설정 (물리 삭제 아님)
   - 판매자 소유 확인 필수

**UI 페이지:**

6. `src/app/(dashboard)/products/page.tsx` — 상품 목록 페이지
   - 테이블 뷰: 상품명, 가격, 가용재고/전체재고 (예: "7/10 (3 홀드)"), 별칭, 카테고리, 상태
   - "상품 등록" 버튼 → 모달 또는 별도 페이지
   - 재고 부족(가용재고 ≤ 5) 시 빨간색 강조

7. `src/components/products/product-form.tsx` — 상품 등록/수정 폼
   - 필수: 상품명, 가격, 재고
   - 선택: 카테고리, 별칭 (태그 입력 방식), 옵션
   - 별칭은 쉼표 또는 엔터로 구분하여 태그로 표시

8. `src/app/(dashboard)/layout.tsx` — 대시보드 레이아웃
   - 좌측 사이드바: 대시보드, 라이브, 주문, 상품, 입금, 고객, 설정
   - 상단 헤더: 상점명, 로그아웃 버튼
   - 모바일: 햄버거 메뉴

shadcn/ui 컴포넌트 필요 시 설치하라: `npx shadcn@latest add table dialog badge toast sheet`.
```

### 생성/수정 파일
- `src/lib/api-utils.ts`
- `src/app/api/products/route.ts`
- `src/app/api/products/[id]/route.ts`
- `src/app/(dashboard)/layout.tsx`
- `src/app/(dashboard)/products/page.tsx`
- `src/components/products/product-form.tsx`
- `src/components/layout/sidebar.tsx`
- `src/components/layout/header.tsx`

### 검증 방법
- 로그인 후 `/products`에서 시드 상품 3개 표시 확인
- 새 상품 등록 → 목록에 반영 확인
- 상품 수정 (가격, 재고, 별칭 변경) → 반영 확인
- 상품 삭제 → `isActive=false`로 변경 확인
- 미로그인 상태에서 API 호출 시 401 응답 확인

---

## Step 6: YouTube 채팅 커넥터 + 명령어 파서 + 메시지 dedup

### 의존성
- 선행 단계: Step 3 (커스텀 서버 + Socket.IO), Step 5 (상품 데이터)
- 필요 파일: `server.ts`, `src/lib/socket.ts`, `src/lib/db.ts`

### 목표
YouTube 라이브 방송의 채팅을 실시간으로 수신하고, `!주문` 명령어를 파싱하며, 중복 메시지를 방지한다. 대시보드에서 방송 시작/종료 제어가 가능하다.

### Claude Code 프롬프트

```
YouTube 채팅 커넥터, 명령어 파서, 메시지 중복 방지를 구현하라.

1. `src/lib/chat/command-parser.ts` — 주문 명령어 파서:
```typescript
import { prisma } from "@/lib/db";

interface ParseResult {
  success: boolean;
  productId?: string;
  productName?: string;
  quantity?: number;
  error?: string;
}

// 한글 숫자 매핑
const koreanNumbers: Record<string, number> = {
  하나: 1, 둘: 2, 셋: 3, 넷: 4, 다섯: 5,
  여섯: 6, 일곱: 7, 여덟: 8, 아홉: 9, 열: 10,
  한: 1, 두: 2, 세: 3, 네: 4,
};

export async function parseOrderCommand(
  message: string,
  sellerId: string
): Promise<ParseResult> {
  // "!주문"으로 시작하는지 확인
  const trimmed = message.trim();
  if (!trimmed.startsWith("!주문")) {
    return { success: false, error: "not_order_command" };
  }

  const parts = trimmed.replace("!주문", "").trim().split(/\s+/);
  if (parts.length === 0 || parts[0] === "") {
    return { success: false, error: "no_product_name" };
  }

  const productNameInput = parts[0];
  let quantity = 1;

  if (parts.length > 1) {
    const qtyStr = parts[1].replace(/개$/, ""); // "3개" → "3"
    const parsed = parseInt(qtyStr, 10);
    if (!isNaN(parsed) && parsed > 0) {
      quantity = parsed;
    } else if (koreanNumbers[qtyStr]) {
      quantity = koreanNumbers[qtyStr];
    }
  }

  // 상품 매칭: 정확 일치 → aliases 일치 → 부분 일치
  const products = await prisma.product.findMany({
    where: { sellerId, isActive: true },
  });

  // 1) 정확 일치
  let matched = products.find((p) => p.name === productNameInput);

  // 2) aliases 일치
  if (!matched) {
    matched = products.find((p) => {
      if (!p.aliases) return false;
      const aliases: string[] = JSON.parse(p.aliases);
      return aliases.includes(productNameInput);
    });
  }

  // 3) 부분 일치 (상품명이 입력에 포함되거나, 입력이 상품명에 포함)
  if (!matched) {
    matched = products.find(
      (p) => p.name.includes(productNameInput) || productNameInput.includes(p.name)
    );
  }

  if (!matched) {
    return { success: false, error: "product_not_found" };
  }

  return {
    success: true,
    productId: matched.id,
    productName: matched.name,
    quantity,
  };
}
```

2. `src/lib/chat/dedup.ts` — 메시지 중복 방지:
```typescript
import { prisma } from "@/lib/db";

/**
 * platformMessageId 기반으로 이미 처리된 메시지인지 확인.
 * true 반환 시 → 이미 처리됨 (무시해야 함)
 */
export async function isDuplicateMessage(
  liveSessionId: string,
  platform: string,
  platformMessageId: string | null
): Promise<boolean> {
  if (!platformMessageId) return false; // ID 없으면 dedupe 불가, 통과

  const existing = await prisma.chatMessage.findUnique({
    where: {
      liveSessionId_platform_platformMessageId: {
        liveSessionId,
        platform,
        platformMessageId,
      },
    },
  });

  return !!existing;
}
```

3. `src/lib/chat/youtube-connector.ts` — YouTube 채팅 커넥터:
```typescript
import { LiveChat } from "youtube-chat";
import { EventEmitter } from "events";

export interface ChatEvent {
  platform: "youtube";
  platformMessageId: string | null;
  userId: string;        // channel ID
  displayName: string;
  message: string;
  timestamp: Date;
}

export class YouTubeConnector extends EventEmitter {
  private liveChat: LiveChat | null = null;
  private channelId: string;

  constructor(channelId: string) {
    super();
    this.channelId = channelId;
  }

  async start(): Promise<void> {
    // youtube-chat은 영상 URL 또는 채널 ID를 받음
    // 채널 ID로 현재 라이브 스트림을 자동 감지
    this.liveChat = new LiveChat({ channelId: this.channelId });

    this.liveChat.on("chat", (chatItem) => {
      const event: ChatEvent = {
        platform: "youtube",
        platformMessageId: chatItem.id || null,
        userId: chatItem.author.channelId,
        displayName: chatItem.author.name,
        message: chatItem.message
          .map((m) => ("text" in m ? m.text : ""))
          .join(""),
        timestamp: new Date(chatItem.timestamp),
      };
      this.emit("chat", event);
    });

    this.liveChat.on("error", (err) => {
      this.emit("error", err);
    });

    const ok = await this.liveChat.start();
    if (!ok) {
      throw new Error("YouTube 라이브 채팅을 찾을 수 없습니다. 채널이 라이브 중인지 확인하세요.");
    }
  }

  stop(): void {
    this.liveChat?.stop();
    this.liveChat = null;
  }
}
```

4. `src/lib/chat/chat-manager.ts` — 채팅 커넥터 관리:
```typescript
import { Server as SocketIOServer } from "socket.io";
import { YouTubeConnector, ChatEvent } from "./youtube-connector";
import { isDuplicateMessage } from "./dedup";
import { prisma } from "@/lib/db";
import { emitToSeller } from "@/lib/socket";

interface ActiveSession {
  sessionId: string;
  sellerId: string;
  connector: YouTubeConnector;
}

export class ChatManager {
  private io: SocketIOServer;
  private activeSessions: Map<string, ActiveSession> = new Map();

  constructor(io: SocketIOServer) {
    this.io = io;
  }

  async startSession(
    sellerId: string,
    platform: "youtube",
    channelId: string
  ): Promise<string> {
    // LiveSession 생성
    const session = await prisma.liveSession.create({
      data: { sellerId, platform, channelId, status: "active" },
    });

    const connector = new YouTubeConnector(channelId);

    connector.on("chat", async (event: ChatEvent) => {
      await this.handleChatMessage(session.id, sellerId, event);
    });

    connector.on("error", (err: Error) => {
      console.error(`[ChatManager] Session ${session.id} error:`, err.message);
      emitToSeller(sellerId, "stream-error", { sessionId: session.id, error: err.message });
    });

    await connector.start();

    this.activeSessions.set(session.id, {
      sessionId: session.id,
      sellerId,
      connector,
    });

    return session.id;
  }

  async stopSession(sessionId: string): Promise<void> {
    const active = this.activeSessions.get(sessionId);
    if (!active) return;

    active.connector.stop();
    this.activeSessions.delete(sessionId);

    await prisma.liveSession.update({
      where: { id: sessionId },
      data: { status: "ended", endedAt: new Date() },
    });
  }

  private async handleChatMessage(
    sessionId: string,
    sellerId: string,
    event: ChatEvent
  ): Promise<void> {
    // 1. 중복 체크
    const isDup = await isDuplicateMessage(sessionId, event.platform, event.platformMessageId);
    if (isDup) return;

    // 2. 채팅 메시지 DB 저장
    const isOrder = event.message.trim().startsWith("!주문");

    await prisma.chatMessage.create({
      data: {
        liveSessionId: sessionId,
        platform: event.platform,
        platformMessageId: event.platformMessageId,
        userId: event.userId,
        displayName: event.displayName,
        message: event.message,
        isOrder,
      },
    });

    // 3. Socket.IO로 채팅 메시지 전송 (대시보드 채팅 피드)
    emitToSeller(sellerId, "chat-message", {
      sessionId,
      platform: event.platform,
      userId: event.userId,
      displayName: event.displayName,
      message: event.message,
      isOrder,
      timestamp: event.timestamp,
    });

    // 주문 처리는 Step 7에서 연결
    // 여기서는 이벤트만 emit하여 주문 서비스가 구독하도록 준비
    if (isOrder) {
      this.emit("order-command", {
        sessionId,
        sellerId,
        event,
      });
    }
  }

  // EventEmitter가 아니므로 단순 콜백 패턴 사용
  private orderHandler: ((data: any) => void) | null = null;

  onOrderCommand(handler: (data: any) => void) {
    this.orderHandler = handler;
  }

  private emit(event: string, data: any) {
    if (event === "order-command" && this.orderHandler) {
      this.orderHandler(data);
    }
  }

  getActiveSession(sessionId: string): ActiveSession | undefined {
    return this.activeSessions.get(sessionId);
  }

  getActiveSessionsBySeller(sellerId: string): ActiveSession[] {
    return Array.from(this.activeSessions.values()).filter(
      (s) => s.sellerId === sellerId
    );
  }
}
```

5. `src/app/api/stream/start/route.ts` — 채팅 수신 시작 API:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { getAuthenticatedSeller } from "@/lib/api-utils";

export async function POST(req: NextRequest) {
  const { error, sellerId } = await getAuthenticatedSeller();
  if (error) return error;

  const { platform, channelId } = await req.json();

  if (!platform || !channelId) {
    return NextResponse.json({ error: "platform과 channelId를 입력하세요." }, { status: 400 });
  }

  if (platform !== "youtube") {
    return NextResponse.json({ error: "MVP는 YouTube만 지원합니다." }, { status: 400 });
  }

  try {
    const chatManager = (global as any).__chatManager;
    if (!chatManager) {
      return NextResponse.json({ error: "서버가 초기화되지 않았습니다." }, { status: 500 });
    }

    const sessionId = await chatManager.startSession(sellerId, platform, channelId);
    return NextResponse.json({ sessionId });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
```

6. `src/app/api/stream/stop/route.ts` — 채팅 수신 종료 API

7. `server.ts`를 수정하여 ChatManager를 초기화하라:
```typescript
// server.ts에 추가
import { ChatManager } from "./src/lib/chat/chat-manager";

// io 초기화 후:
(global as any).__chatManager = new ChatManager(io);
```

ChatManager는 EventEmitter를 상속하지 않으므로, 주문 처리 콜백은 `chatManager.onOrderCommand(handler)` 패턴으로 Step 7에서 연결한다.
```

### 생성/수정 파일
- `src/lib/chat/command-parser.ts`
- `src/lib/chat/dedup.ts`
- `src/lib/chat/youtube-connector.ts`
- `src/lib/chat/chat-manager.ts`
- `src/app/api/stream/start/route.ts`
- `src/app/api/stream/stop/route.ts`
- `server.ts` (ChatManager 초기화 추가)

### 검증 방법
- `npm run dev`로 서버 시작 확인
- `/api/stream/start`에 `{ platform: "youtube", channelId: "UCxxxxxx" }` POST → sessionId 반환 (실제 라이브 채널이 없으면 에러 메시지 확인)
- `command-parser.ts`의 단위 테스트: `parseOrderCommand("!주문 사과 3", sellerId)` → `{ success: true, productName: "사과", quantity: 3 }`
- 중복 방지: 동일 `platformMessageId`로 2번 호출 시 2번째는 무시

---

## Step 7: 주문 생성

### 의존성
- 선행 단계: Step 6 (채팅 커넥터 + 파서), Step 5 (상품 데이터)
- 필요 파일: `src/lib/chat/chat-manager.ts`, `src/lib/chat/command-parser.ts`, `src/lib/db.ts`, `src/lib/socket.ts`

### 목표
채팅 `!주문` 명령어로 주문이 자동 생성되고, reservedStock이 증가하며, 쿨다운/한도 체크가 작동하고, 대시보드에 실시간 알림이 전송된다.

### Claude Code 프롬프트

```
주문 생성 비즈니스 로직을 구현하라. 채팅 명령어에서 주문을 생성하고, Prisma 트랜잭션으로 원자성을 보장한다.

1. `src/lib/utils/order-number.ts` — 주문번호 생성기:
```typescript
import { prisma } from "@/lib/db";

/**
 * 주문번호 형식: LS-{YYMMDD}-{4자리 시퀀스}
 * 예: LS-240314-0001
 * 판매자별 일별 시퀀스.
 */
export async function generateOrderNumber(sellerId: string): Promise<string> {
  const now = new Date();
  const yy = String(now.getFullYear()).slice(2);
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  const datePrefix = `LS-${yy}${mm}${dd}-`;

  // 오늘의 마지막 주문번호 조회
  const lastOrder = await prisma.order.findFirst({
    where: {
      sellerId,
      orderNumber: { startsWith: datePrefix },
    },
    orderBy: { orderNumber: "desc" },
  });

  let seq = 1;
  if (lastOrder) {
    const lastSeq = parseInt(lastOrder.orderNumber.split("-")[2], 10);
    seq = lastSeq + 1;
  }

  return `${datePrefix}${String(seq).padStart(4, "0")}`;
}
```

2. `src/lib/order/order-throttle.ts` — 주문 속도 제한:
```typescript
import { prisma } from "@/lib/db";

interface ThrottleResult {
  allowed: boolean;
  reason?: "cooldown" | "max_pending";
}

/**
 * 쿨다운: 마지막 주문으로부터 {orderCooldown}초 미경과 시 거부
 * 동시 한도: 입금대기 주문이 {maxPendingPerUser}건 이상이면 거부
 */
export async function checkOrderThrottle(
  sellerId: string,
  chatUserId: string
): Promise<ThrottleResult> {
  const seller = await prisma.seller.findUnique({
    where: { id: sellerId },
    select: { orderCooldown: true, maxPendingPerUser: true },
  });

  if (!seller) return { allowed: false, reason: "cooldown" };

  // 1. 쿨다운 체크
  const cooldownCutoff = new Date(Date.now() - seller.orderCooldown * 1000);
  const recentOrder = await prisma.order.findFirst({
    where: {
      sellerId,
      chatUserId,
      createdAt: { gte: cooldownCutoff },
    },
  });

  if (recentOrder) {
    return { allowed: false, reason: "cooldown" };
  }

  // 2. 동시 입금대기 한도 체크
  const pendingCount = await prisma.order.count({
    where: {
      sellerId,
      chatUserId,
      status: "입금대기",
    },
  });

  if (pendingCount >= seller.maxPendingPerUser) {
    return { allowed: false, reason: "max_pending" };
  }

  return { allowed: true };
}
```

3. `src/lib/order/order-service.ts` — 주문 생성 서비스:
```typescript
import { prisma } from "@/lib/db";
import { parseOrderCommand } from "@/lib/chat/command-parser";
import { checkOrderThrottle } from "./order-throttle";
import { generateOrderNumber } from "@/lib/utils/order-number";
import { emitToSeller } from "@/lib/socket";
import { ChatEvent } from "@/lib/chat/youtube-connector";

interface CreateOrderResult {
  success: boolean;
  orderId?: string;
  orderNumber?: string;
  error?: string;
}

export async function createOrderFromChat(
  sellerId: string,
  sessionId: string,
  event: ChatEvent
): Promise<CreateOrderResult> {
  // 1. 명령어 파싱
  const parsed = await parseOrderCommand(event.message, sellerId);
  if (!parsed.success || !parsed.productId) {
    return { success: false, error: parsed.error };
  }

  // 2. 쿨다운 / 한도 체크
  const throttle = await checkOrderThrottle(sellerId, event.userId);
  if (!throttle.allowed) {
    if (throttle.reason === "max_pending") {
      emitToSeller(sellerId, "order-throttled", {
        userId: event.userId,
        displayName: event.displayName,
        reason: "max_pending",
      });
    }
    return { success: false, error: throttle.reason };
  }

  // 3. Prisma 트랜잭션으로 주문 생성
  try {
    const result = await prisma.$transaction(async (tx) => {
      // 상품 조회 + 가용 재고 확인
      const product = await tx.product.findUnique({
        where: { id: parsed.productId },
      });

      if (!product || !product.isActive) {
        throw new Error("product_not_found");
      }

      const availableStock = product.stock - product.reservedStock;
      if (availableStock < parsed.quantity!) {
        throw new Error("out_of_stock");
      }

      // 주문번호 생성
      const orderNumber = await generateOrderNumber(sellerId);

      // Seller의 autoCancel 설정 조회
      const seller = await tx.seller.findUnique({
        where: { id: sellerId },
        select: { autoCancel: true },
      });

      const cancelDeadline = new Date(
        Date.now() + (seller?.autoCancel || 30) * 60 * 1000
      );

      const totalAmount = product.price * parsed.quantity!;

      // Order 생성
      const order = await tx.order.create({
        data: {
          orderNumber,
          sellerId,
          liveSessionId: sessionId,
          chatPlatform: event.platform,
          chatUserId: event.userId,
          chatDisplayName: event.displayName,
          status: "입금대기",
          totalAmount,
          cancelDeadline,
        },
      });

      // OrderItem 생성
      await tx.orderItem.create({
        data: {
          orderId: order.id,
          productId: product.id,
          productName: product.name,
          quantity: parsed.quantity!,
          unitPrice: product.price,
        },
      });

      // reservedStock 증가
      await tx.product.update({
        where: { id: product.id },
        data: { reservedStock: { increment: parsed.quantity! } },
      });

      // ChatMessage에 processedOrderId 설정
      if (event.platformMessageId) {
        await tx.chatMessage.updateMany({
          where: {
            liveSessionId: sessionId,
            platform: event.platform,
            platformMessageId: event.platformMessageId,
          },
          data: { processedOrderId: order.id },
        });
      }

      // LiveSession.totalOrders 증가
      await tx.liveSession.update({
        where: { id: sessionId },
        data: { totalOrders: { increment: 1 } },
      });

      return { orderId: order.id, orderNumber };
    });

    // Socket.IO로 새 주문 알림
    emitToSeller(sellerId, "new-order", {
      orderId: result.orderId,
      orderNumber: result.orderNumber,
      displayName: event.displayName,
      productName: parsed.productName,
      quantity: parsed.quantity,
      totalAmount: parsed.quantity! * (await prisma.product.findUnique({ where: { id: parsed.productId } }))!.price,
    });

    return {
      success: true,
      orderId: result.orderId,
      orderNumber: result.orderNumber,
    };
  } catch (err: any) {
    if (err.message === "out_of_stock") {
      emitToSeller(sellerId, "stock-insufficient", {
        productName: parsed.productName,
        displayName: event.displayName,
      });
    }
    return { success: false, error: err.message };
  }
}
```

4. `server.ts`를 수정하여 ChatManager와 주문 서비스를 연결:
```typescript
// server.ts에 추가 (ChatManager 초기화 후):
import { createOrderFromChat } from "./src/lib/order/order-service";

chatManager.onOrderCommand(async ({ sessionId, sellerId, event }) => {
  const result = await createOrderFromChat(sellerId, sessionId, event);
  if (result.success) {
    console.log(`[Order] ${result.orderNumber} created from ${event.displayName}`);
  }
});
```

5. 주문 목록/상세 API:

`GET /api/orders` — 주문 목록:
- 쿼리: `?status=입금대기&sessionId=xxx&page=1&limit=20`
- 판매자 자신의 주문만 조회
- OrderItem 포함
- 정렬: 최신순

`GET /api/orders/[id]` — 주문 상세:
- OrderItem + Payment 포함

`PATCH /api/orders/[id]` — 주문 상태 변경:
- 바디: `{ status, note?, recipientName?, recipientPhone?, shippingAddress? }`
- "취소" 전환 시 → reservedStock 복원

`DELETE /api/orders/[id]` — 주문 수동 취소:
- 상태를 "취소"로 변경
- reservedStock 복원 (트랜잭션)

6. `src/app/api/orders/route.ts`, `src/app/api/orders/[id]/route.ts` 생성.
```

### 생성/수정 파일
- `src/lib/utils/order-number.ts`
- `src/lib/order/order-throttle.ts`
- `src/lib/order/order-service.ts`
- `src/app/api/orders/route.ts`
- `src/app/api/orders/[id]/route.ts`
- `server.ts` (주문 서비스 연결)

### 검증 방법
- `generateOrderNumber`이 `LS-YYMMDD-0001` 형식 반환
- 주문 생성 후 `reservedStock` 증가 확인 (Prisma Studio)
- 쿨다운 내 재주문 시 거부 확인
- 동시 입금대기 한도 초과 시 거부 확인
- 재고 부족 시 `stock-insufficient` 이벤트 전송 확인
- `GET /api/orders` 목록 조회 성공
- `DELETE /api/orders/[id]`로 취소 시 `reservedStock` 복원 확인

---

## Step 8: Socket.IO 실시간 대시보드

### 의존성
- 선행 단계: Step 7 (주문 생성 + Socket.IO 이벤트), Step 5 (상품/대시보드 레이아웃)
- 필요 파일: `src/hooks/use-socket.ts`, `src/lib/socket.ts`, `src/app/(dashboard)/layout.tsx`

### 목표
라이브 대시보드에서 실시간으로 채팅 메시지와 주문을 확인할 수 있고, 방송 시작/종료를 제어할 수 있다.

### Claude Code 프롬프트

```
라이브 대시보드 UI를 구현하라. Socket.IO를 통해 실시간 데이터를 수신하고 표시한다.

**Socket.IO 이벤트 목록** (서버 → 클라이언트):
- `chat-message` — 새 채팅 메시지
- `new-order` — 새 주문 생성
- `order-paid` — 입금 확인 (Step 9에서 사용)
- `order-cancelled` — 주문 취소 (Step 10에서 사용)
- `order-throttled` — 주문 한도 초과 알림
- `stock-insufficient` — 재고 부족 알림
- `stream-error` — 스트림 연결 에러

1. `src/stores/live-store.ts` — Zustand 스토어:
```typescript
import { create } from "zustand";

interface ChatMsg {
  platform: string;
  userId: string;
  displayName: string;
  message: string;
  isOrder: boolean;
  timestamp: string;
}

interface OrderEvent {
  orderId: string;
  orderNumber: string;
  displayName: string;
  productName: string;
  quantity: number;
  totalAmount: number;
  status: string;
  createdAt: string;
}

interface LiveStore {
  // 방송 상태
  sessionId: string | null;
  isStreaming: boolean;

  // 실시간 데이터
  chatMessages: ChatMsg[];
  recentOrders: OrderEvent[];
  notifications: { type: string; message: string; time: string }[];

  // 액션
  setSession: (sessionId: string | null) => void;
  addChatMessage: (msg: ChatMsg) => void;
  addOrder: (order: OrderEvent) => void;
  updateOrderStatus: (orderId: string, status: string) => void;
  addNotification: (type: string, message: string) => void;
  clearAll: () => void;
}

export const useLiveStore = create<LiveStore>((set) => ({
  sessionId: null,
  isStreaming: false,
  chatMessages: [],
  recentOrders: [],
  notifications: [],

  setSession: (sessionId) =>
    set({ sessionId, isStreaming: !!sessionId }),

  addChatMessage: (msg) =>
    set((state) => ({
      chatMessages: [msg, ...state.chatMessages].slice(0, 200), // 최대 200개 유지
    })),

  addOrder: (order) =>
    set((state) => ({
      recentOrders: [order, ...state.recentOrders].slice(0, 100),
    })),

  updateOrderStatus: (orderId, status) =>
    set((state) => ({
      recentOrders: state.recentOrders.map((o) =>
        o.orderId === orderId ? { ...o, status } : o
      ),
    })),

  addNotification: (type, message) =>
    set((state) => ({
      notifications: [
        { type, message, time: new Date().toISOString() },
        ...state.notifications,
      ].slice(0, 50),
    })),

  clearAll: () =>
    set({
      sessionId: null,
      isStreaming: false,
      chatMessages: [],
      recentOrders: [],
      notifications: [],
    }),
}));
```

2. `src/hooks/use-realtime-orders.ts` — Socket.IO 이벤트 핸들러 훅:
```typescript
"use client";
import { useEffect } from "react";
import { useSocket } from "./use-socket";
import { useLiveStore } from "@/stores/live-store";

export function useRealtimeOrders(sellerId: string | null) {
  const { socket, isConnected } = useSocket(sellerId);
  const store = useLiveStore();

  useEffect(() => {
    if (!socket) return;

    socket.on("chat-message", (data) => store.addChatMessage(data));
    socket.on("new-order", (data) => store.addOrder({ ...data, status: "입금대기", createdAt: new Date().toISOString() }));
    socket.on("order-paid", (data) => store.updateOrderStatus(data.orderId, "입금확인"));
    socket.on("order-cancelled", (data) => store.updateOrderStatus(data.orderId, "취소"));
    socket.on("order-throttled", (data) => store.addNotification("warning", `${data.displayName}님 주문 한도 초과`));
    socket.on("stock-insufficient", (data) => store.addNotification("error", `${data.productName} 재고 부족 (${data.displayName}님)`));
    socket.on("stream-error", (data) => store.addNotification("error", `스트림 오류: ${data.error}`));

    return () => {
      socket.off("chat-message");
      socket.off("new-order");
      socket.off("order-paid");
      socket.off("order-cancelled");
      socket.off("order-throttled");
      socket.off("stock-insufficient");
      socket.off("stream-error");
    };
  }, [socket]);

  return { isConnected };
}
```

3. `src/app/(dashboard)/live/page.tsx` — 라이브 대시보드 페이지:
구조:
- **상단바**: 방송 상태 표시등(초록/빨강), 플랫폼 아이콘, 방송 시간, 누적 주문/매출
- **좌측 패널 (60%)**: 실시간 주문 피드 (`recentOrders`)
  - 각 카드: 주문번호, 닉네임, 상품, 수량, 금액, 상태 뱃지 (입금대기=노랑, 입금확인=초록, 취소=빨강)
  - `cancelDeadline`까지 남은 시간 카운트다운 (분:초)
  - "입금확인" 빠른 버튼 (Step 9에서 연결)
- **우측 패널 (40%)**: 채팅 피드 (`chatMessages`)
  - 모든 메시지 표시 (최신 순 스크롤)
  - `isOrder=true`인 메시지는 파란색 하이라이트
  - 주문 명령어 감지 표시

4. `src/components/live/stream-controls.tsx` — 방송 제어:
- YouTube 채널 ID 입력 필드
- "방송 시작" / "방송 종료" 버튼
- `/api/stream/start`, `/api/stream/stop` 호출

5. `src/components/live/order-feed.tsx` — 실시간 주문 피드 컴포넌트

6. `src/components/live/chat-feed.tsx` — 실시간 채팅 피드 컴포넌트

7. `src/app/(dashboard)/page.tsx` — 대시보드 홈:
- 오늘의 요약: 총 주문, 입금대기, 입금확인, 취소, 총 매출
- 최근 주문 5건
- 현재 활성 방송 상태

8. `src/app/(dashboard)/orders/page.tsx` — 주문 관리 페이지:
- 필터 탭: 전체 | 입금대기 | 입금확인 | 취소
- 테이블: 주문번호, 닉네임, 상품, 금액, 상태, 주문시간
- 클릭 시 주문 상세 모달 또는 `/orders/[id]`

shadcn/ui 추가 설치: `npx shadcn@latest add tabs select separator scroll-area avatar dropdown-menu`.

모바일에서는 좌/우 패널 대신 탭으로 전환 가능하도록 하라. Tailwind의 `md:` 브레이크포인트 활용.
```

### 생성/수정 파일
- `src/stores/live-store.ts`
- `src/hooks/use-realtime-orders.ts`
- `src/app/(dashboard)/live/page.tsx`
- `src/app/(dashboard)/page.tsx`
- `src/app/(dashboard)/orders/page.tsx`
- `src/app/(dashboard)/orders/[id]/page.tsx`
- `src/components/live/stream-controls.tsx`
- `src/components/live/order-feed.tsx`
- `src/components/live/chat-feed.tsx`
- `src/components/orders/order-table.tsx`
- `src/components/orders/order-status-badge.tsx`

### 검증 방법
- `/live`에서 채널 ID 입력 후 "방송 시작" 클릭 → 연결 상태 표시
- 채팅 메시지가 우측 패널에 실시간 표시 (테스트 시 시뮬레이션 가능)
- `!주문` 메시지 시 좌측 패널에 새 주문 카드 표시
- 주문 상태 뱃지 색상 확인
- `/orders`에서 주문 목록 필터링 동작 확인
- 모바일 뷰에서 탭 전환 동작 확인

---

## Step 9: 수동 입금 확인 + CustomerMapping 생성 제안

### 의존성
- 선행 단계: Step 7 (주문 생성), Step 8 (대시보드)
- 필요 파일: `src/lib/db.ts`, `src/lib/socket.ts`, 주문 API

### 목표
판매자가 주문에 대해 수동으로 입금을 확인할 수 있고, 입금 확인 시 CustomerMapping 생성을 제안한다. 입금 확인 시 주문 상태가 변경되고, reservedStock이 감소하며, 실제 stock도 감소한다.

### Claude Code 프롬프트

```
수동 입금 확인(Tier 3)과 CustomerMapping 생성 제안을 구현하라.

**입금 확인 시 재고 변화 규칙:**
- 주문 생성 시: `reservedStock += quantity` (가용 재고 감소, 실 재고 유지)
- 입금 확인 시: `stock -= quantity` + `reservedStock -= quantity` (실 재고 감소, 가용 재고는 유지)
- 취소 시: `reservedStock -= quantity` (가용 재고 복원)

1. `src/app/api/payments/verify/route.ts` — 수동 입금 확인:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { getAuthenticatedSeller } from "@/lib/api-utils";
import { prisma } from "@/lib/db";
import { emitToSeller } from "@/lib/socket";

export async function POST(req: NextRequest) {
  const { error, sellerId } = await getAuthenticatedSeller();
  if (error) return error;

  const { orderId, depositorName, amount } = await req.json();

  if (!orderId || !depositorName) {
    return NextResponse.json({ error: "주문 ID와 입금자명을 입력하세요." }, { status: 400 });
  }

  // 트랜잭션으로 처리
  const result = await prisma.$transaction(async (tx) => {
    // 주문 조회
    const order = await tx.order.findFirst({
      where: { id: orderId, sellerId, status: "입금대기" },
      include: { items: true },
    });

    if (!order) {
      throw new Error("입금대기 상태의 주문을 찾을 수 없습니다.");
    }

    // Payment 생성 (bankTransactionId = null: 수동 확인)
    const payment = await tx.payment.create({
      data: {
        orderId: order.id,
        bankTransactionId: null,
        method: "manual",
        depositorName,
        amount: amount || order.totalAmount,
        matchConfidence: null,
        verifiedBy: "manual",
      },
    });

    // 주문 상태 변경
    await tx.order.update({
      where: { id: order.id },
      data: {
        status: "입금확인",
        paidAt: new Date(),
      },
    });

    // 재고 조정: stock 감소 + reservedStock 감소
    for (const item of order.items) {
      await tx.product.update({
        where: { id: item.productId },
        data: {
          stock: { decrement: item.quantity },
          reservedStock: { decrement: item.quantity },
        },
      });
    }

    // LiveSession.totalRevenue 증가
    if (order.liveSessionId) {
      await tx.liveSession.update({
        where: { id: order.liveSessionId },
        data: { totalRevenue: { increment: order.totalAmount } },
      });
    }

    return { order, payment };
  });

  // Socket.IO 알림
  emitToSeller(sellerId!, "order-paid", {
    orderId: result.order.id,
    orderNumber: result.order.orderNumber,
    depositorName,
  });

  // CustomerMapping 존재 여부 확인
  const existingMapping = await prisma.customerMapping.findUnique({
    where: {
      sellerId_chatPlatform_chatUserId: {
        sellerId: sellerId!,
        chatPlatform: result.order.chatPlatform,
        chatUserId: result.order.chatUserId,
      },
    },
  });

  return NextResponse.json({
    success: true,
    orderId: result.order.id,
    suggestMapping: !existingMapping, // 매핑이 없으면 생성 제안
    mappingData: !existingMapping
      ? {
          chatPlatform: result.order.chatPlatform,
          chatUserId: result.order.chatUserId,
          chatDisplayName: result.order.chatDisplayName,
          suggestedRealName: depositorName,
        }
      : null,
  });
}
```

2. `src/app/api/customers/route.ts` — CustomerMapping CRUD:
```typescript
// GET: 매핑 목록 (판매자별)
// POST: 매핑 생성
//   body: { chatPlatform, chatUserId, chatDisplayName, realName, phone?, address? }
//   Unique 제약: (sellerId, chatPlatform, chatUserId)
//   이미 존재하면 upsert로 갱신
```

3. `src/app/api/customers/[id]/route.ts`:
```typescript
// PUT: 매핑 수정
// DELETE: 매핑 삭제
```

4. UI — 입금 확인 모달:
주문 카드 또는 주문 목록에서 "입금확인" 버튼 클릭 시:
- 모달 열기
- 입금자명 입력 필드 (필수)
- 금액 입력 필드 (기본값: 주문 금액, 수정 가능)
- "확인" 클릭 → `/api/payments/verify` POST
- 성공 시:
  - 주문 상태 즉시 "입금확인"으로 변경 (Socket.IO로도 전파)
  - `suggestMapping=true`이면 "이 고객의 실명을 저장하시겠습니까?" 추가 다이얼로그
    - "예" → `/api/customers` POST로 CustomerMapping 생성
    - "아니오" → 닫기

5. `src/components/payments/payment-verify-modal.tsx` — 입금 확인 모달 컴포넌트

6. `src/app/(dashboard)/customers/page.tsx` — 고객 매핑 관리 페이지:
- 테이블: 플랫폼, 유저ID, 닉네임, 실명, 연락처, 주소
- 편집/삭제 기능
- "매핑 추가" 버튼

shadcn/ui 추가: `npx shadcn@latest add alert-dialog`.
```

### 생성/수정 파일
- `src/app/api/payments/verify/route.ts`
- `src/app/api/customers/route.ts`
- `src/app/api/customers/[id]/route.ts`
- `src/components/payments/payment-verify-modal.tsx`
- `src/app/(dashboard)/customers/page.tsx`
- `src/app/(dashboard)/live/page.tsx` (입금확인 버튼 연결)
- `src/app/(dashboard)/orders/page.tsx` (입금확인 버튼 연결)

### 검증 방법
- "입금대기" 주문에 대해 "입금확인" 클릭 → 입금자명 입력 → 확인
- 주문 상태가 "입금확인"으로 변경 확인
- Product의 `stock` 감소, `reservedStock` 감소 확인 (Prisma Studio)
- LiveSession의 `totalRevenue` 증가 확인
- CustomerMapping 생성 제안 다이얼로그 표시 확인
- "예" 선택 시 CustomerMapping 생성 확인
- 이미 매핑이 존재하는 고객의 주문에는 제안 미표시 확인
- `/customers`에서 매핑 목록 조회/편집/삭제 확인

---

## Step 10: 미입금 자동취소 스케줄러

### 의존성
- 선행 단계: Step 7 (주문 생성 — cancelDeadline), Step 3 (커스텀 서버)
- 필요 파일: `server.ts`, `src/lib/db.ts`, `src/lib/socket.ts`

### 목표
60초 간격으로 스케줄러가 실행되어, `cancelDeadline`이 지난 미입금 주문을 자동 취소하고, reservedStock을 복원하며, 대시보드에 실시간 알림을 전송한다.

### Claude Code 프롬프트

```
미입금 자동취소 스케줄러를 구현하라. `node-cron`을 사용하여 60초 간격으로 실행한다.

1. `src/lib/order/auto-cancel.ts`:
```typescript
import cron from "node-cron";
import { prisma } from "@/lib/db";
import { Server as SocketIOServer } from "socket.io";

/**
 * 60초 간격으로 실행:
 * 1. 상태 = "입금대기" AND cancelDeadline < 현재시간인 주문 조회
 * 2. 각 주문에 대해 트랜잭션 실행:
 *    - 주문 상태 → "취소"
 *    - 해당 주문의 모든 OrderItem에 대해 reservedStock 감소
 *    - LiveSession.totalOrders는 유지 (이력 보존)
 * 3. Socket.IO로 취소 알림 전송
 */
export function startAutoCancelScheduler(io: SocketIOServer) {
  // 매분 0초에 실행 (60초 간격)
  cron.schedule("* * * * *", async () => {
    try {
      const now = new Date();

      // 취소 대상 주문 조회
      const expiredOrders = await prisma.order.findMany({
        where: {
          status: "입금대기",
          cancelDeadline: { lt: now },
        },
        include: { items: true },
      });

      if (expiredOrders.length === 0) return;

      console.log(`[AutoCancel] ${expiredOrders.length}건 취소 처리 시작`);

      for (const order of expiredOrders) {
        await prisma.$transaction(async (tx) => {
          // 주문 상태 변경
          await tx.order.update({
            where: { id: order.id },
            data: { status: "취소" },
          });

          // reservedStock 복원
          for (const item of order.items) {
            await tx.product.update({
              where: { id: item.productId },
              data: { reservedStock: { decrement: item.quantity } },
            });
          }
        });

        // Socket.IO 알림 (판매자별 방에 전송)
        io.to(`seller:${order.sellerId}`).emit("order-cancelled", {
          orderId: order.id,
          orderNumber: order.orderNumber,
          displayName: order.chatDisplayName,
          reason: "auto_cancel",
        });

        console.log(`[AutoCancel] ${order.orderNumber} 취소 완료`);
      }

      console.log(`[AutoCancel] ${expiredOrders.length}건 취소 처리 완료`);
    } catch (err) {
      console.error("[AutoCancel] 스케줄러 오류:", err);
    }
  });

  console.log("[AutoCancel] 스케줄러 시작 (60초 간격)");
}
```

2. `server.ts` 수정 — 스케줄러 시작:
```typescript
// server.ts에 추가 (기존 코드 후):
import { startAutoCancelScheduler } from "./src/lib/order/auto-cancel";

// httpServer.listen 전에:
startAutoCancelScheduler(io);
```

3. `server.ts` 최종 형태 확인:
다음 순서로 초기화:
```typescript
app.prepare().then(() => {
  const httpServer = createServer(handle);
  const io = new SocketIOServer(httpServer, { cors: ... });

  (global as any).__socketIO = io;

  const chatManager = new ChatManager(io);
  (global as any).__chatManager = chatManager;

  // 주문 서비스 연결
  chatManager.onOrderCommand(async ({ sessionId, sellerId, event }) => {
    await createOrderFromChat(sellerId, sessionId, event);
  });

  // Socket.IO 이벤트 핸들러
  io.on("connection", (socket) => { ... });

  // 자동취소 스케줄러
  startAutoCancelScheduler(io);

  httpServer.listen(port);
});
```

4. 대시보드에서 자동 취소 알림 처리:
`order-cancelled` 이벤트 수신 시 → 주문 상태 "취소"로 업데이트 + 알림 표시.
`use-realtime-orders.ts`에 이미 구현되어 있으므로 추가 코드 불필요.

서버를 재시작하고 스케줄러가 로그를 출력하는지 확인하라.
```

### 생성/수정 파일
- `src/lib/order/auto-cancel.ts`
- `server.ts` (스케줄러 시작 추가, 전체 초기화 순서 정리)

### 검증 방법
- 서버 시작 시 `[AutoCancel] 스케줄러 시작 (60초 간격)` 로그 확인
- 테스트: Prisma Studio에서 주문의 `cancelDeadline`을 과거 시간으로 수정 → 60초 이내에 자동 취소 확인
- 취소된 주문의 상태가 "취소"로 변경 확인
- 해당 상품의 `reservedStock`이 감소 확인
- `LiveSession.totalOrders`는 유지 확인 (이력 보존)
- 대시보드에서 `order-cancelled` 이벤트 수신 및 UI 반영 확인

---

## 4. 의존성 그래프

```
Step 0: 프로젝트 생성 + 패키지 설치
  │
  ▼
Step 1: 스캐폴딩 (타입, Prisma 싱글턴, scripts)
  │
  ▼
Step 2: DB 스키마 + 마이그레이션
  │
  ├──────────────────┐
  ▼                  ▼
Step 3: 커스텀 서버    Step 4: 인증 시스템 ←── (Step 2 필요)
  │                  │
  │                  ▼
  │               Step 5: 상품 CRUD
  │                  │
  ├──────────────────┤
  ▼                  ▼
Step 6: YouTube 채팅 커넥터 + 파서 + dedup
  │
  ▼
Step 7: 주문 생성 (트랜잭션, reservedStock)
  │
  ├──────────────────┐
  ▼                  ▼
Step 8: 실시간        Step 9: 수동 입금 확인
  대시보드            + CustomerMapping
  │                  │
  └──────────────────┘
           │
           ▼
       Step 10: 자동취소 스케줄러
```

### 병렬 실행 가능 구간
- **Step 3 + Step 4**: 커스텀 서버와 인증 시스템은 독립적으로 구현 가능 (둘 다 Step 2 완료 후)
- **Step 8 + Step 9**: 실시간 대시보드와 수동 입금 확인은 독립적 (둘 다 Step 7 완료 후)

### 순차 필수 구간
- Step 0 → 1 → 2: 기초 인프라
- Step 6 → 7: 채팅 파서가 있어야 주문 생성 가능
- Step 7 → 10: 주문의 `cancelDeadline`이 설정되어야 자동취소 가능

---

## 5. Claude Code 전달 시 주의사항

### 컨텍스트 관리 요령

1. **한 번에 하나의 Step만 전달하라.** 각 프롬프트는 자급자족이므로, 이전 대화를 참조할 필요 없이 해당 Step의 프롬프트만 복사-붙여넣기하면 된다.

2. **Step 완료 확인 후 다음 단계로 넘어가라.** 각 Step의 "검증 방법"을 반드시 실행하고, 통과한 뒤 다음 Step을 시작하라.

3. **누적 에러에 주의하라.** Step 2(DB 스키마)에서 필드명이 틀리면 이후 모든 Step에 영향. Step 2 완료 후 `npx prisma studio`로 스키마를 꼭 확인하라.

4. **서버 재시작 타이밍:** Step 3, 6, 7, 10은 `server.ts`를 수정한다. 각 Step 완료 후 서버를 재시작하라.

5. **shadcn/ui 컴포넌트 설치:** UI 관련 Step(5, 8, 9)에서 필요한 컴포넌트를 먼저 설치한 후 코드를 작성하라. 프롬프트에 필요한 컴포넌트 목록이 명시되어 있다.

### 흔히 발생하는 문제와 대응

| 문제 | 대응 |
|------|------|
| Prisma 마이그레이션 충돌 | `npx prisma migrate reset`으로 초기화 후 재시도 |
| `youtube-chat` 타입 에러 | `@types`가 없을 수 있음. `any`로 타입 단언하거나 직접 타입 선언 |
| Socket.IO CORS 에러 | `server.ts`의 cors origin이 `.env.local`의 `NEXTAUTH_URL`과 일치하는지 확인 |
| NextAuth v5 설정 차이 | `next-auth@beta` 버전에 따라 API가 다를 수 있음. 공식 Auth.js 문서 참조 |
| `global` 객체 타입 에러 | `(global as any)` 캐스팅 사용. MVP 전제이므로 타입 안전성보다 동작 우선 |
| SQLite 동시 쓰기 잠금 | `prisma.$transaction` 사용 시 짧게 유지. MVP 규모에서는 문제 없음 |
| `tsx server.ts` 경로 문제 | `tsconfig.json`의 paths가 `tsx`에서 해석되지 않을 수 있음. `tsconfig-paths` 패키지 추가 또는 상대 경로 사용 |

### 설계 결정 반영 포인트

PLAN.md 섹션 13의 설계 결정이 각 Step에 어떻게 반영되었는지:

| 설계 결정 | 반영 Step |
|-----------|-----------|
| 13.1 BankTransaction 도입 | Step 2 (스키마), Step 9 (수동 확인 시 bankTransactionId=null) |
| 13.2 Idempotency (platformMessageId + 쿨다운) | Step 6 (dedup), Step 7 (쿨다운/한도) |
| 13.3 chatUserId 기준 전환 | Step 2 (스키마), Step 6 (커넥터에서 channelId 사용), Step 9 (CustomerMapping) |
| 13.4 MVP는 입금확인까지 | Step 7 (주문 상태: 입금대기/입금확인/취소만) |
| 13.5 reservedStock + 주문 제한 | Step 7 (쿨다운, 한도, reservedStock 트랜잭션) |
| 13.6 단일 서버 전제 | Step 3 (global 객체), Step 10 (단일 cron) |
