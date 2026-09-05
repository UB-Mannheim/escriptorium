import List from "../../../vue/components/DocumentsTasks/List.vue";

const { hasActiveTasks } = List.methods;

describe("DocumentsTasks List", () => {
    describe("hasActiveTasks", () => {
        it("is true when there are queued tasks", () => {
            expect(hasActiveTasks({ tasks_stats: { Queued: 1, Running: 0 } })).toBe(true);
        });

        it("is true when there are running tasks", () => {
            expect(hasActiveTasks({ tasks_stats: { Queued: 0, Running: 2 } })).toBe(true);
        });

        it("is false when all tasks are finished/canceled/crashed", () => {
            expect(hasActiveTasks({
                tasks_stats: { Queued: 0, Running: 0, Finished: 5, Canceled: 1, Crashed: 0 },
            })).toBe(false);
        });

        it("is false when tasks_stats is missing", () => {
            expect(hasActiveTasks({})).toBe(false);
        });
    });
});
