import DiploLine from "../../../vue/components/DiploLine.vue";

const orderWatcher = DiploLine.options.watch["line.order"];

describe("DiploLine", () => {
    describe("line.order watcher", () => {
        it("repositions element and updates content when parentNode exists", () => {
            const mockChildren = [{}, {}, {}];
            const mockElement = {};
            const mockParent = {
                removeChild: jest.fn(),
                insertBefore: jest.fn(),
                children: mockChildren,
            };
            mockElement.parentNode = mockParent;
            const ctx = {
                getEl: jest.fn(() => mockElement),
                line: { order: 1, currentTrans: { content: "hello" } },
                setElContent: jest.fn(),
            };
            orderWatcher.call(ctx, 1, 0);
            expect(mockParent.removeChild).toHaveBeenCalledWith(mockElement);
            expect(mockParent.insertBefore).toHaveBeenCalledWith(
                mockElement,
                mockChildren[1],
            );
            expect(ctx.setElContent).toHaveBeenCalledWith("hello");
        });
    });
});
