# MCP 서버 + Web UI 구축 계획

> 이 PC를 서버로 사용하여 외부 기기에서 3-엔진(Claude, Codex/GPT, Gemini) 오케스트레이션에 접근한다.

## 현재 상태 (2026-03-14)

- 3-엔진 혼합 `/sub` 오케스트레이션 **완성 및 검증 완료**
- 엔진 디스패치: PowerShell `Start-Process` → CLI 직접 실행
- 인코딩 수정 완료 (UTF-8 강제)
- 구독 인증 기반 (API 키 불필요)

## 아키텍처

```
[외부 기기]                              [이 PC - 서버]
                                         ┌─────────────────────────┐
 브라우저/모바일 ──── HTTPS ────→         │  Web UI (Phase 3)       │
                                         │    └─ REST API          │
 Claude Code ──── MCP/SSE ────→          │  MCP Server (Phase 2)   │
                                         │    ├─ tool: run-codex   │
 SSH 터미널 ──── SSH ────→               │    ├─ tool: run-gemini  │
                                         │    ├─ tool: run-claude  │
                                         │    └─ tool: run-sub     │
                                         │  Engine Layer           │
                                         │    ├─ codex CLI (GPT)   │
                                         │    ├─ gemini CLI         │
                                         │    └─ claude CLI         │
                                         └─────────────────────────┘
                                              Tailscale / Cloudflare Tunnel
```

## Phase 1: SSH 원격 접근 (즉시 가능)

### 목표
이 PC 터미널을 외부에서 접근하여 기존 `/sub` 시스템 그대로 사용.

### 작업
1. OpenSSH 서버 활성화 (Windows 기본 제공)
   ```powershell
   # 관리자 PowerShell
   Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
   Start-Service sshd
   Set-Service -Name sshd -StartupType Automatic
   ```
2. Tailscale 설치 (NAT 통과, 포트 포워딩 불필요)
   - https://tailscale.com/download
   - 외부 기기에도 Tailscale 설치
   - `ssh haj@<tailscale-ip>` 로 접근
3. 방화벽 규칙 확인 (Tailscale 사용 시 자동 처리)

### 검증
- [ ] 외부 기기에서 SSH 접속 성공
- [ ] SSH 세션에서 `/sub` 테스트 실행 성공
- [ ] 한글 출력 정상 확인

---

## Phase 2: MCP 서버 구축

### 목표
외부 기기의 Claude Code에서 이 PC의 3-엔진을 MCP tool로 직접 호출.

### 기술 스택
- **런타임**: Node.js (이미 설치됨)
- **MCP SDK**: `@modelcontextprotocol/sdk`
- **전송**: SSE (Server-Sent Events over HTTP) — 원격 접근용
- **인증**: Bearer token (간단한 시크릿 키)

### 디렉토리 구조
```
mcp-server/
├── IMPLEMENTATION-PLAN.md    ← 이 파일
├── package.json
├── src/
│   ├── index.ts              ← MCP 서버 엔트리포인트
│   ├── tools/
│   │   ├── run-codex.ts      ← Codex CLI 래핑
│   │   ├── run-gemini.ts     ← Gemini CLI 래핑
│   │   ├── run-claude.ts     ← Claude CLI 래핑
│   │   └── run-sub.ts        ← /sub 오케스트레이션 전체 실행
│   ├── engine/
│   │   └── dispatcher.ts     ← Start-Process 로직을 Node.js child_process로 포팅
│   └── config.ts             ← 실행 파일 경로, 포트, 인증 설정
├── .env                      ← MCP_AUTH_TOKEN, PORT
└── tsconfig.json
```

### MCP Tool 정의

#### `run-engine`
```typescript
{
  name: "run-engine",
  description: "지정된 AI 엔진으로 프롬프트 실행",
  inputSchema: {
    type: "object",
    properties: {
      engine: { enum: ["claude", "codex", "gemini"] },
      model: { type: "string" },  // 선택. 없으면 엔진 기본값
      prompt: { type: "string" },
      sandbox: { type: "string" } // codex 전용
    },
    required: ["engine", "prompt"]
  }
}
```

#### `run-sub`
```typescript
{
  name: "run-sub",
  description: "혼합 엔진 /sub 오케스트레이션 실행",
  inputSchema: {
    type: "object",
    properties: {
      spec: { type: "object" },      // 인라인 스펙 JSON
      spec_path: { type: "string" }   // 또는 서버 로컬 스펙 파일 경로
    }
  }
}
```

### 핵심 구현 포인트

1. **CLI 래핑 (child_process)**
   ```typescript
   import { spawn } from 'child_process';

   async function runEngine(engine: string, prompt: string, model?: string) {
     const cmd = engineCommands[engine]; // { exe, args }
     const proc = spawn(cmd.exe, [...cmd.args(model), prompt], {
       encoding: 'utf-8',
       env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
     });
     // stdout 수집 → 반환
   }
   ```

2. **엔진-모델 매핑 (기존 PowerShell 로직 포팅)**
   ```typescript
   const engineModelDefaults = {
     codex:  { allowed: ["gpt-5.4", "o3", "o4-mini"], default: "gpt-5.4" },
     claude: { allowed: ["haiku", "sonnet", "opus"],   default: "sonnet" },
     gemini: { allowed: ["gemini-2.5-pro", "gemini-2.5-flash"], default: "gemini-2.5-pro" }
   };
   ```

3. **SSE 전송 설정**
   ```typescript
   import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
   import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';

   const server = new McpServer({ name: "sub-orchestrator", version: "1.0.0" });
   // tool 등록 후 SSE로 리슨
   ```

4. **외부 접근 (Tailscale)**
   - 이 PC에서 MCP 서버를 `0.0.0.0:3100`으로 리슨
   - 외부 기기 Claude Code 설정: `"url": "http://<tailscale-ip>:3100/sse"`

### 외부 기기 Claude Code 설정
```json
// ~/.claude/mcp_settings.json (외부 기기)
{
  "mcpServers": {
    "sub-orchestrator": {
      "type": "sse",
      "url": "http://<tailscale-ip>:3100/sse",
      "headers": {
        "Authorization": "Bearer <MCP_AUTH_TOKEN>"
      }
    }
  }
}
```

### 검증
- [ ] MCP 서버 로컬 기동 성공
- [ ] stdio 모드에서 tool 호출 테스트 (로컬 Claude Code)
- [ ] SSE 모드로 전환 후 외부 기기에서 연결 성공
- [ ] `run-engine` tool로 3개 엔진 각각 실행 성공
- [ ] `run-sub` tool로 혼합 오케스트레이션 실행 성공
- [ ] 한글 입출력 정상 확인

---

## Phase 3: Web UI

### 목표
브라우저/모바일에서 오케스트레이션 실행 및 결과 확인.

### 기술 스택
- **프레임워크**: Next.js 또는 Express + 정적 프론트엔드
- **MCP 서버와 통신**: 내부 HTTP 호출 (같은 PC)
- **인증**: 간단한 패스워드 또는 Tailscale ACL

### 기능
1. **스펙 에디터**: JSON 스펙을 UI에서 작성/수정
2. **실행 대시보드**: 스테이지별 진행 상황 실시간 표시
3. **결과 뷰어**: `.last.txt` 파일 내용 렌더링
4. **히스토리**: `subagent-runs/` 과거 실행 결과 브라우징

### 디렉토리 구조
```
mcp-server/
├── src/           ← MCP 서버 (Phase 2)
├── web/
│   ├── app/       ← Next.js 앱
│   ├── components/
│   │   ├── SpecEditor.tsx
│   │   ├── RunDashboard.tsx
│   │   └── ResultViewer.tsx
│   └── api/
│       └── run.ts ← MCP tool 호출 프록시
└── ...
```

### 검증
- [ ] 브라우저에서 스펙 작성 → 실행 → 결과 확인 전체 플로우
- [ ] 모바일 브라우저 접근 성공
- [ ] 실시간 진행 상황 업데이트

---

## 전환 시 기존 시스템 영향

| 기존 구성 요소 | 영향 |
|---|---|
| PowerShell 런처 스크립트 | **유지** — MCP 서버가 내부적으로 호출 가능 |
| `/sub` 스킬 | **유지** — 로컬에서 그대로 사용 |
| 스펙 템플릿 | **유지** — MCP `run-sub` tool이 동일 스펙 형식 사용 |
| `subagent-runs/` 증거 | **유지** — 동일 디렉토리에 저장 |
| 인코딩 수정 | **유지** — Node.js는 기본 UTF-8 |

기존 시스템을 건드리지 않고, 그 위에 MCP 계층을 추가하는 구조.

---

## 의존성 사전 확인

- [ ] Node.js 설치 확인: `node --version` (이미 설치됨)
- [ ] npm 확인: `npm --version` (이미 설치됨)
- [ ] TypeScript: `npm install -g typescript` (필요 시)
- [ ] Tailscale 설치: https://tailscale.com/download
- [ ] 외부 기기에 Tailscale 설치

## 참고 문서

- MCP 공식 스펙: https://modelcontextprotocol.io
- `@modelcontextprotocol/sdk`: npm 패키지
- 기존 엔진 어댑터 문서: `skills/claude-subagent-orchestrator/references/engine-adapters.md`
- 기존 스펙 형식: `skills/codex-subagent-orchestrator/references/spec-format.md`
- 기존 런처 스크립트: `skills/codex-subagent-orchestrator/scripts/start-codex-subagent-team.ps1`
