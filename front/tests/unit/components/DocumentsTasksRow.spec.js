import Row from "../../../vue/components/DocumentsTasks/Row.vue";

const { hasActiveTasks } = Row.computed;

describe("DocumentsTasks Row", () => {
    describe("hasActiveTasks", () => {
        it("is true when there are queued tasks", () => {
            const ctx = { documentTasks: { tasks_stats: { Queued: 1, Running: 0 } } };
            expect(hasActiveTasks.call(ctx)).toBe(true);
        });

        it("is true when there are running tasks", () => {
            const ctx = { documentTasks: { tasks_stats: { Queued: 0, Running: 2 } } };
            expect(hasActiveTasks.call(ctx)).toBe(true);
        });

        it("is false when all tasks are finished/canceled/crashed", () => {
            const ctx = {
                documentTasks: {
                    tasks_stats: { Queued: 0, Running: 0, Finished: 5, Canceled: 1, Crashed: 0 },
                },
            };
            expect(hasActiveTasks.call(ctx)).toBe(false);
        });

        it("is false when tasks_stats is missing", () => {
            const ctx = { documentTasks: {} };
            expect(hasActiveTasks.call(ctx)).toBe(false);
        });
    });
});
