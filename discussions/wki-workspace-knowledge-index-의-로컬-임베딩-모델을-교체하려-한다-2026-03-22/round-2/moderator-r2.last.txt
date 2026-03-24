## Participant Positions (3-line summaries)

**Claude:**
- Recommends **multilingual-e5-large** (768d) for immediate production use
- Cites ONNX export instability of BGE-M3 due to sparse/colbert heads; proven ONNX path for E5-large
- Defers BGE-M3 as post-migration target after ONNX ecosystem matures

**Codex:**
- Optimal choice is **multilingual-e5-large + query/document separation** (implementation-aware recommendation)
- Adds architectural component beyond model selection alone
- (Position minimal; implies E5-large is viable path)

**Gemini:**
- Recommends **BGE-M3 with rigorous 1024d performance/ONNX stability testing**; E5-large as fallback
- Acknowledges 1024d dimension increase is resource concern for local efficiency
- Emphasizes ONNX deployment practicality (pre-built availability, community support) as critical evaluator

---

## Agreement
- ONNX local-execution, cross-lingual, code+doc hybrid search are requirements
- Model selection involves performance vs. resource tradeoff
- Implementation/deployment practicality matters alongside theory

## Disagreement
- **Model choice**: Claude (E5-large now) vs. Gemini (BGE-M3 with testing) vs. Codex (E5-large + architectural addition)
- **ONNX risk assessment**: Claude treats BGE-M3 export instability as deployment blocker; Gemini as testable concern
- **384d→1024d cost**: Claude emphasizes index storage bottleneck for large workspaces; Gemini frames as testable tradeoff

## Open Questions
1. Actual ONNX export stability/pathway for BGE-M3 (dense-head only workaround quality?)
2. Performance/memory/storage impact of 1024d in WKI's real environment
3. Whether multilingual-e5-large's 768d cross-lingual code+doc performance is empirically sufficient
4. How query/document separation (Codex) affects model performance calculus