// SegPanel pulls in paper.js via baseline.editor.js, which doesn't initialise under
// jsdom -- we only exercise the save/report methods, so stub the module out.
jest.mock("../../../src/baseline.editor.js", () => ({ Segmenter: class {} }));
// keep the retry semantics themselves in retry.spec.js; here we just want to know
// that the save paths go through it, without waiting for real backoffs
jest.mock("../../../src/editor/util/retry", () => ({
    withRetry: jest.fn((fn) => fn()),
}));

import SegPanelComponent from "../../../vue/components/SegPanel.vue";
import { withRetry } from "../../../src/editor/util/retry";

// SegPanel is declared with Vue.extend, so the default export is a constructor and
// the methods hang off its options
const SegPanel = { methods: SegPanelComponent.options.methods };

const httpError = (status) => ({ response: { status } });

/**
 * A stand-in for the component instance: the methods under test only touch the
 * store, the alert action and the segmenter.
 */
const makeContext = ({ dispatch, regions = [] } = {}) => ({
    add: jest.fn(),
    $store: {
        dispatch: dispatch || jest.fn().mockResolvedValue({}),
        commit: jest.fn(),
        state: { transcriptions: { selectedTranscription: 1 } },
    },
    segmenter: {
        regions,
        loadRegion: jest.fn(),
        refreshRegionSavedState: jest.fn(),
    },
    reportSaveFailure: SegPanel.methods.reportSaveFailure,
});

// a region as the segmenter hands it over: already drawn, not yet persisted
const unsavedRegion = () => ({
    id: undefined,
    box: [[0, 0], [0, 10], [10, 10], [10, 0]],
    type: "Form-Field",
    context: { pk: null },
});

describe("SegPanel save failures", () => {
    beforeEach(() => {
        jest.clearAllMocks();
        jest.spyOn(console, "error").mockImplementation(() => {});
    });

    afterEach(() => {
        console.error.mockRestore();
    });

    describe("reportSaveFailure", () => {
        it("raises an alert instead of only logging", () => {
            const ctx = makeContext();

            SegPanel.methods.reportSaveFailure.call(ctx, "region", httpError(500));

            expect(ctx.add).toHaveBeenCalledTimes(1);
            const alert = ctx.add.mock.calls[0][0];
            expect(alert.color).toBe("alert");
            expect(alert.message).toContain("region");
        });

        it("includes the status code when there is one", () => {
            const ctx = makeContext();

            SegPanel.methods.reportSaveFailure.call(ctx, "region", httpError(503));

            expect(ctx.add.mock.calls[0][0].message).toContain("503");
        });

        it("still reports when there is no response to read a status from", () => {
            const ctx = makeContext();

            SegPanel.methods.reportSaveFailure.call(ctx, "line", new Error("boom"));

            expect(ctx.add).toHaveBeenCalledTimes(1);
            expect(ctx.add.mock.calls[0][0].message).toContain("line");
        });

        it("names the action, so a failed delete doesn't read as a failed save", () => {
            const ctx = makeContext();

            SegPanel.methods.reportSaveFailure.call(
                ctx,
                "region",
                httpError(500),
                "delete",
            );

            expect(ctx.add.mock.calls[0][0].message).toContain("delete");
        });
    });

    describe("bulkCreate for regions", () => {
        it("assigns the returned pk when the create succeeds", async () => {
            const dispatch = jest.fn().mockResolvedValue({ pk: 42 });
            const ctx = makeContext({ dispatch });
            const data = { regions: [unsavedRegion()] };

            await SegPanel.methods.bulkCreate.call(ctx, data, false);

            expect(data.regions[0].context.pk).toBe(42);
            expect(ctx.add).not.toHaveBeenCalled();
        });

        it("goes through withRetry", async () => {
            const ctx = makeContext();

            await SegPanel.methods.bulkCreate.call(
                ctx,
                { regions: [unsavedRegion()] },
                false,
            );

            expect(withRetry).toHaveBeenCalled();
        });

        it("alerts the user when the region cannot be saved", async () => {
            // this is the reported bug: the region stays on the canvas, so without
            // an alert it looks saved and is only found missing on the next load
            const dispatch = jest.fn().mockRejectedValue(httpError(500));
            const ctx = makeContext({ dispatch });
            const data = { regions: [unsavedRegion()] };

            await SegPanel.methods.bulkCreate.call(ctx, data, false);

            expect(ctx.add).toHaveBeenCalledTimes(1);
            expect(ctx.add.mock.calls[0][0].color).toBe("alert");
            // and it is still marked unsaved, which is what dashes its outline
            expect(data.regions[0].context.pk).toBeNull();
            expect(ctx.segmenter.refreshRegionSavedState).toHaveBeenCalled();
        });

        it("does not abandon the remaining regions after one fails", async () => {
            const dispatch = jest
                .fn()
                .mockRejectedValueOnce(httpError(500))
                .mockResolvedValue({ pk: 7 });
            const ctx = makeContext({ dispatch });
            const data = { regions: [unsavedRegion(), unsavedRegion()] };

            await SegPanel.methods.bulkCreate.call(ctx, data, false);

            expect(data.regions[0].context.pk).toBeNull();
            expect(data.regions[1].context.pk).toBe(7);
        });
    });

    describe("deleteRegion", () => {
        it("removes the region from the canvas once the delete succeeds", async () => {
            const segRegion = { context: { pk: 3 }, remove: jest.fn() };
            const ctx = makeContext({ regions: [segRegion] });

            await SegPanel.methods.deleteRegion.call(ctx, { context: { pk: 3 } });

            expect(segRegion.remove).toHaveBeenCalled();
            expect(ctx.add).not.toHaveBeenCalled();
        });

        it("keeps the region on the canvas when the delete fails", async () => {
            // the dispatch used not to be awaited, so the rejection escaped the
            // try/catch and the region was removed while still in the database
            const segRegion = { context: { pk: 3 }, remove: jest.fn() };
            const dispatch = jest.fn().mockRejectedValue(httpError(500));
            const ctx = makeContext({ dispatch, regions: [segRegion] });

            await SegPanel.methods.deleteRegion.call(ctx, { context: { pk: 3 } });

            expect(segRegion.remove).not.toHaveBeenCalled();
            expect(ctx.add).toHaveBeenCalledTimes(1);
        });
    });
});
