import DiploLine from "../../../vue/components/DiploLine.vue";

const orderWatcher = DiploLine.options.watch["line.order"];

describe("DiploLine", () => {
    describe("line.order watcher", () => {
        it("repositions element and updates content when parentNode exists", () => {
            const mockChildren = [{}, {}, {}];
            const mockParent = {
                insertBefore: jest.fn(),
                children: mockChildren,
            };
            const ctx = {
                $el: { parentNode: mockParent },
                line: { order: 1, currentTrans: { content: "hello" } },
                setElContent: jest.fn(),
            };
            orderWatcher.call(ctx, 1, 0);
            expect(mockParent.insertBefore).toHaveBeenCalledWith(
                ctx.$el,
                mockChildren[1],
            );
            expect(ctx.setElContent).toHaveBeenCalledWith("hello");
        });
    });
});
