import TranscriptionModalComponent from "../../../vue/components/TranscriptionModal.vue";

// TranscriptionModal is declared with Vue.extend, so the default export is a constructor
// and the methods / computed hang off its options
const { methods, computed } = TranscriptionModalComponent.options;

const BOX_KEY = "escr-line-box-height-12";

/**
 * A stand-in for the component instance: the zoom / box height logic only touches its
 * own data, the image container and the store's document id.
 */
const makeContext = (overrides = {}) => {
    const ctx = {
        zoom: { scale: 1, x: 0, y: 0 },
        boxHeight: null,
        legacyModeEnabled: false,
        mainTextDirection: "ltr",
        $store: { state: { document: { id: 12 } } },
        $nextTick: (fn) => fn(),
        $refs: {
            modalImgContainer: {
                clientWidth: 400,
                clientHeight: 100,
                getBoundingClientRect: () => ({ left: 10, top: 20 }),
            },
            transModal: { clientHeight: 800 },
        },
        computeStyles: jest.fn(),
        resetZoom: methods.resetZoom,
        zoomBy: methods.zoomBy,
        boxHeightKey: methods.boxHeightKey,
        loadBoxHeight: methods.loadBoxHeight,
        applyBoxHeight: methods.applyBoxHeight,
        resetBoxHeight: methods.resetBoxHeight,
        ...overrides,
    };
    return ctx;
};

describe("TranscriptionModal line image zoom", () => {
    describe("zoomBy", () => {
        it("zooms around the given point", () => {
            const ctx = makeContext();

            methods.zoomBy.call(ctx, 2, 100, 50);

            // the point under the cursor must stay where it is
            expect(ctx.zoom).toEqual({ scale: 2, x: -100, y: -50 });
        });

        it("zooms around the center of the box by default", () => {
            const ctx = makeContext();

            methods.zoomBy.call(ctx, 2);

            expect(ctx.zoom).toEqual({ scale: 2, x: -200, y: -50 });
        });

        it("never zooms out past 1x", () => {
            const ctx = makeContext();

            methods.zoomBy.call(ctx, 0.5, 0, 0);

            expect(ctx.zoom.scale).toBe(1);
        });

        it("caps the zoom at 10x", () => {
            const ctx = makeContext({ zoom: { scale: 9, x: 0, y: 0 } });

            methods.zoomBy.call(ctx, 5, 0, 0);

            expect(ctx.zoom.scale).toBe(10);
        });
    });

    describe("onExcerptWheel", () => {
        it("zooms in when scrolling up, relative to the box position", () => {
            const ctx = makeContext();
            const wheel = { deltaY: -1, clientX: 110, clientY: 70 };

            methods.onExcerptWheel.call(ctx, wheel);

            expect(ctx.zoom.scale).toBeCloseTo(1.1);
            // cursor at (100, 50) inside the box
            expect(ctx.zoom.x).toBeCloseTo(100 - 100 * 1.1);
            expect(ctx.zoom.y).toBeCloseTo(50 - 50 * 1.1);
        });

        it("zooms out when scrolling down", () => {
            const ctx = makeContext({ zoom: { scale: 2, x: 0, y: 0 } });

            methods.onExcerptWheel.call(ctx, { deltaY: 1, clientX: 10, clientY: 20 });

            expect(ctx.zoom.scale).toBeCloseTo(2 / 1.1);
        });
    });

    describe("panning", () => {
        beforeEach(() => {
            jest.spyOn(window, "addEventListener").mockImplementation(() => {});
            jest.spyOn(window, "removeEventListener").mockImplementation(() => {});
        });

        afterEach(() => {
            jest.restoreAllMocks();
        });

        it("moves the image with the mouse, even when not zoomed", () => {
            const ctx = makeContext();
            const down = { button: 0, clientX: 50, clientY: 50, preventDefault: jest.fn() };

            methods.onExcerptMouseDown.call(ctx, down);
            methods.onExcerptMouseMove.call(ctx, { clientX: 70, clientY: 130 });

            expect(ctx.zoom).toEqual({ scale: 1, x: 20, y: 80 });
        });

        it("keeps panning relative to the current offset", () => {
            const ctx = makeContext({ zoom: { scale: 3, x: -40, y: -10 } });

            methods.onExcerptMouseDown.call(ctx, { button: 0, clientX: 0, clientY: 0, preventDefault: jest.fn() });
            methods.onExcerptMouseMove.call(ctx, { clientX: 5, clientY: 5 });

            expect(ctx.zoom).toEqual({ scale: 3, x: -35, y: -5 });
        });

        it("ignores buttons other than the main one", () => {
            const ctx = makeContext();

            methods.onExcerptMouseDown.call(ctx, { button: 2, clientX: 0, clientY: 0, preventDefault: jest.fn() });

            expect(window.addEventListener).not.toHaveBeenCalled();
        });

        it("stops listening once the mouse is released", () => {
            const ctx = makeContext({ onExcerptMouseMove: jest.fn(), onExcerptMouseUp: jest.fn() });

            methods.onExcerptMouseUp.call(ctx);

            expect(window.removeEventListener).toHaveBeenCalledWith("mousemove", ctx.onExcerptMouseMove);
            expect(window.removeEventListener).toHaveBeenCalledWith("mouseup", ctx.onExcerptMouseUp);
        });
    });

    describe("resetZoom", () => {
        it("goes back to the centered, unzoomed image", () => {
            const ctx = makeContext({ zoom: { scale: 4, x: -30, y: 12 } });

            methods.resetZoom.call(ctx);

            expect(ctx.zoom).toEqual({ scale: 1, x: 0, y: 0 });
        });
    });

    describe("zoomStyle", () => {
        it("translates then scales the image layer", () => {
            const style = computed.zoomStyle.call({ zoom: { scale: 2, x: -10, y: 5 } });

            expect(style.transform).toBe("translate(-10px, 5px) scale(2)");
        });
    });

    describe("zoomTools", () => {
        it("offers the height reset for horizontal text", () => {
            const labels = computed.zoomTools.call({ mainTextDirection: "ltr" }).map((t) => t.label);

            expect(labels).toEqual(["Zoom in", "Zoom out", "Reset zoom and position", "Reset image height"]);
        });

        it("has no height reset for vertical text, whose box sizes itself", () => {
            const labels = computed.zoomTools.call({ mainTextDirection: "ttb" }).map((t) => t.label);

            expect(labels).not.toContain("Reset image height");
        });
    });
});

describe("TranscriptionModal line image box height", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    describe("boxStyle", () => {
        it("is empty until the user picks a height", () => {
            expect(computed.boxStyle.call(makeContext())).toEqual({});
        });

        it("applies the chosen height", () => {
            expect(computed.boxStyle.call(makeContext({ boxHeight: 150 }))).toEqual({ height: "150px" });
        });

        it("is ignored in legacy mode and for vertical text", () => {
            expect(computed.boxStyle.call(makeContext({ boxHeight: 150, legacyModeEnabled: true }))).toEqual({});
            expect(computed.boxStyle.call(makeContext({ boxHeight: 150, mainTextDirection: "ttb" }))).toEqual({});
        });
    });

    describe("persistence", () => {
        it("stores the height per document", () => {
            const ctx = makeContext({ boxHeight: 220, resizeStart: { y: 0, height: 100 } });

            methods.onResizeMouseUp.call(ctx);

            expect(localStorage.getItem(BOX_KEY)).toBe("220");
            expect(ctx.resizeStart).toBeNull();
        });

        it("restores it when the modal opens", () => {
            localStorage.setItem(BOX_KEY, "180");

            expect(methods.loadBoxHeight.call(makeContext())).toBe(180);
        });

        it("does not use another document's height", () => {
            localStorage.setItem("escr-line-box-height-99", "180");

            expect(methods.loadBoxHeight.call(makeContext())).toBeNull();
        });

        it("falls back to the default when storage holds garbage", () => {
            localStorage.setItem(BOX_KEY, "abc");

            expect(methods.loadBoxHeight.call(makeContext())).toBeNull();
        });

        it("does not break when storage is unavailable", () => {
            jest.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
                throw new Error("blocked");
            });

            expect(methods.loadBoxHeight.call(makeContext())).toBeNull();

            jest.restoreAllMocks();
        });

        it("does not store anything if no drag was started", () => {
            const ctx = makeContext({ boxHeight: 220, resizeStart: null });

            methods.onResizeMouseUp.call(ctx);

            expect(localStorage.getItem(BOX_KEY)).toBeNull();
        });
    });

    describe("resizing", () => {
        const start = (ctx) => methods.onResizeMouseDown.call(ctx, {
            button: 0,
            clientY: 100,
            pointerId: 1,
            target: { setPointerCapture: jest.fn() },
        });

        it("follows the pointer and refits the image", () => {
            const ctx = makeContext();

            start(ctx);
            methods.onResizeMouseMove.call(ctx, { clientY: 160 });

            expect(ctx.boxHeight).toBe(160);  // 100px box + 60px dragged
            expect(ctx.computeStyles).toHaveBeenCalled();
        });

        it("captures the pointer so the drag can leave the box", () => {
            const ctx = makeContext();
            const target = { setPointerCapture: jest.fn() };

            methods.onResizeMouseDown.call(ctx, { button: 0, clientY: 0, pointerId: 7, target });

            expect(target.setPointerCapture).toHaveBeenCalledWith(7);
        });

        it("keeps a minimum height", () => {
            const ctx = makeContext();

            start(ctx);
            methods.onResizeMouseMove.call(ctx, { clientY: -500 });

            expect(ctx.boxHeight).toBe(64);
        });

        it("is limited by the modal height", () => {
            const ctx = makeContext();

            start(ctx);
            methods.onResizeMouseMove.call(ctx, { clientY: 5000 });

            expect(ctx.boxHeight).toBe(800);
        });

        it("ignores moves when no drag is running", () => {
            const ctx = makeContext();

            methods.onResizeMouseMove.call(ctx, { clientY: 300 });

            expect(ctx.boxHeight).toBeNull();
        });

        it("resets to the default height and forgets the stored one", () => {
            localStorage.setItem(BOX_KEY, "220");
            const ctx = makeContext({ boxHeight: 220 });

            methods.resetBoxHeight.call(ctx);

            expect(ctx.boxHeight).toBeNull();
            expect(localStorage.getItem(BOX_KEY)).toBeNull();
            expect(ctx.computeStyles).toHaveBeenCalled();
        });
    });
});
