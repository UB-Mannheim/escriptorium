jest.mock("../../../src/api", () => ({}));
jest.mock("../../../vue/store/util/metadata", () => ({
    getMetadataCRUD: jest.fn(),
}));

import { initialState, mutations } from "../../../src/editor/store/parts";

describe("parts store", () => {
    describe("initialState", () => {
        it("has image as an empty object", () => {
            expect(initialState().image).toEqual({});
        });

        it("has loaded as false", () => {
            expect(initialState().loaded).toBe(false);
        });

        it("returns a new object on each call", () => {
            expect(initialState()).not.toBe(initialState());
        });
    });

    describe("mutations", () => {
        describe("load", () => {
            it("merges part data onto state and sets loaded to true", () => {
                const state = initialState();
                mutations.load(state, {
                    image: { uri: "/img.png", size: [800, 600] },
                    name: "Page 1",
                });
                expect(state.image).toEqual({ uri: "/img.png", size: [800, 600] });
                expect(state.name).toBe("Page 1");
                expect(state.loaded).toBe(true);
            });

            it("handles image with null size (file not found on disk)", () => {
                const state = initialState();
                mutations.load(state, { image: { uri: "/img.png", size: null } });
                expect(state.image.size).toBeNull();
            });
        });

        describe("reset", () => {
            it("restores initial state", () => {
                const state = initialState();
                state.loaded = true;
                state.pk = 42;
                state.image = { uri: "/img.png", size: [800, 600] };
                mutations.reset(state);
                expect(state).toEqual(initialState());
            });
        });

        describe("setPartPk", () => {
            it("sets pk on state", () => {
                const state = initialState();
                mutations.setPartPk(state, 99);
                expect(state.pk).toBe(99);
            });
        });

        describe("setOrder", () => {
            it("sets order on state", () => {
                const state = initialState();
                mutations.setOrder(state, 3);
                expect(state.order).toBe(3);
            });
        });
    });
});
