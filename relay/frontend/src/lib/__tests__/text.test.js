import { describe, expect, it } from "vitest";
import { estimateTokens } from "../text";
describe("estimateTokens", () => {
    it("returns 0 for empty input", () => {
        expect(estimateTokens("")).toBe(0);
    });
    it("rounds up using heuristic chunk size", () => {
        expect(estimateTokens("1234")).toBe(1);
        expect(estimateTokens("12345")).toBe(2);
    });
    it("never returns less than 1 for non-empty text", () => {
        expect(estimateTokens("a")).toBe(1);
    });
});
