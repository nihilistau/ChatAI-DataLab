/** Rough heuristic for estimating GPT-style token counts client-side. */
// @tag: frontend,lib,telemetry

export function estimateTokens(text: string): number {
  if (!text) return 0;
  const approximateTokenLength = 4; // heuristic: 1 token ≈ 4 chars
  return Math.max(1, Math.ceil(text.length / approximateTokenLength));
}
