## Summary

### **Claude**
- BGE-M3 dense-head-only ONNX is viable (instability concerns apply only to full multi-vector mode)
- Index rebuild cost (384d→768d vs →1024d) and WKI's actual chunk count are decisive factors
- Recommend 2-track approach: test BGE-M3 with specific metrics (ONNX export, recall@5, indexing speed); E5-large as fallback

### **Codex**
- BGE-M3 is optimal for current WKI requirements
- E5-large cannot reach its potential without query/document separation during search

### **Gemini**
- BGE-M3 has reported ONNX stability risks but warrants focused technical investigation rather than dismissal
- Dense-head-only ONNX export could bypass sparse/colbert head issues while preserving BGE-M3's strengths
- Validate both BGE-M3 (prioritized deep-dive) and E5-large (empirically tested as fallback)

---

## Areas of Agreement
- BGE-M3 has highest potential for code+doc hybrid and cross-lingual search
- E5-large is a practical, stable alternative
- Empirical validation on WKI's real data is necessary

## Areas of Disagreement
- **Confidence level**: Codex is most confident in BGE-M3; Claude emphasizes practical constraints; Gemini positions investigation as prerequisite
- **ONNX viability**: Claude claims dense-only is stable; Gemini frames it as unproven but worth investigating
- **E5-large utility**: Codex claims it underperforms without query/document separation; others don't address this constraint

## Open Questions
1. Is BGE-M3 dense-only ONNX export stable and performant in practice?
2. What is the actual recall improvement (%) of BGE-M3 vs E5-large on WKI's real search queries?
3. What are rebuild time and storage increase for WKI's current dataset?
4. Does E5-large require query/document separation in WKI's search pipeline, and if so, is this implemented?