jest.mock("../../../src/editor/api");

import { actions, getters, initialState } from "../../../src/editor/store/lines";
import * as api from "../../../src/editor/api";

// lines.js uses lodash as a global `_` (via vendor bundle in production)
global._ = require("lodash");

describe("lines store", () => {
    describe("getters", () => {
        describe("hasMasks", () => {
            it("returns false when no lines have masks", () => {
                const state = {
                    ...initialState(),
                    all: [
                        { pk: 1, baseline: [[0, 0]], mask: null },
                        { pk: 2, baseline: [[1, 0]], mask: null },
                    ],
                };
                expect(getters.hasMasks(state)).toBe(false);
            });

            it("returns true when at least one line has a mask", () => {
                const state = {
                    ...initialState(),
                    all: [
                        { pk: 1, baseline: [[0, 0]], mask: [[0, 0], [1, 0], [1, 1]] },
                        { pk: 2, baseline: [[1, 0]], mask: null },
                    ],
                };
                expect(getters.hasMasks(state)).toBe(true);
            });
        });
    });

    describe("actions", () => {
        describe("merge", () => {
            let state, dispatch, commit, rootState, storeGetters;

            beforeEach(() => {
                state = {
                    ...initialState(),
                    all: [
                        { pk: 1, baseline: [[0, 0], [1, 1]], mask: [[0, 0], [1, 0], [1, 1]], region: null, order: 0 },
                        { pk: 2, baseline: [[2, 0], [3, 1]], mask: [[2, 0], [3, 0], [3, 1]], region: null, order: 1 },
                    ],
                    autoOrder: false,
                };
                dispatch = jest.fn().mockResolvedValue();
                commit = jest.fn();
                rootState = { document: { id: 1 }, parts: { pk: 10 } };
                storeGetters = { hasMasks: getters.hasMasks(state) };

                api.mergeLines = jest.fn().mockResolvedValue({
                    data: {
                        lines: {
                            deleted: [{ pk: 1 }, { pk: 2 }],
                            created: { pk: 3, baseline: [[0, 0], [3, 1]], mask: null, transcriptions: [] },
                        },
                    },
                });
            });

            it("dispatches recalculateMasks with the new line pk when lines have masks", async () => {
                await actions.merge(
                    { state, dispatch, commit, rootState, getters: storeGetters },
                    { pks: [1, 2], transcription: 5 },
                );

                expect(dispatch).toHaveBeenCalledWith("recalculateMasks", [3]);
            });

            it("does not dispatch recalculateMasks when no lines have masks", async () => {
                state.all.forEach((l) => (l.mask = null));
                storeGetters = { hasMasks: getters.hasMasks(state) };

                await actions.merge(
                    { state, dispatch, commit, rootState, getters: storeGetters },
                    { pks: [1, 2], transcription: 5 },
                );

                expect(dispatch).not.toHaveBeenCalledWith(
                    "recalculateMasks",
                    expect.anything(),
                );
            });
        });
    });
});
