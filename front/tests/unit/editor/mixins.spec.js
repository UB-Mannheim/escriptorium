import { BasePanel } from "../../../src/editor/mixins";

describe("BasePanel mixin", () => {
    describe("setRatio", () => {
        it("computes ratio from element width divided by image width", () => {
            const ctx = {
                $el: { firstChild: { clientWidth: 200 } },
                $store: { state: { parts: { image: { size: [400, 300] } } } },
                ratio: 1,
            };
            BasePanel.methods.setRatio.call(ctx);
            expect(ctx.ratio).toBe(0.5);
        });
    });
});
