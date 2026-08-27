import { isTransient, withRetry } from "../../../src/editor/util/retry";

// an axios-shaped error
const httpError = (status) => ({ response: { status } });
// what axios throws when the request never got a response
const networkError = () => Object.assign(new Error("Network Error"), {
    response: undefined,
});

describe("retry util", () => {
    describe("isTransient", () => {
        it("treats a missing response as transient", () => {
            // network error, timeout, server restarting: worth another try
            expect(isTransient(networkError())).toBe(true);
        });

        it.each([408, 429, 500, 502, 503, 504])(
            "treats %i as transient",
            (status) => {
                expect(isTransient(httpError(status))).toBe(true);
            },
        );

        it.each([400, 401, 403, 404, 409])(
            "treats %i as permanent",
            (status) => {
                // these would fail identically however many times we send them
                expect(isTransient(httpError(status))).toBe(false);
            },
        );
    });

    describe("withRetry", () => {
        it("returns the result without retrying when the call succeeds", async () => {
            const fn = jest.fn().mockResolvedValue("ok");

            await expect(withRetry(fn)).resolves.toBe("ok");
            expect(fn).toHaveBeenCalledTimes(1);
        });

        it("retries a transient failure and returns the eventual success", async () => {
            const fn = jest
                .fn()
                .mockRejectedValueOnce(httpError(503))
                .mockResolvedValue("saved");

            await expect(withRetry(fn, { delay: 0 })).resolves.toBe("saved");
            expect(fn).toHaveBeenCalledTimes(2);
        });

        it("rethrows once the retries are exhausted", async () => {
            const error = httpError(500);
            const fn = jest.fn().mockRejectedValue(error);

            // the caller still needs the error so it can report the failure
            await expect(withRetry(fn, { retries: 2, delay: 0 })).rejects.toBe(
                error,
            );
            expect(fn).toHaveBeenCalledTimes(3); // initial attempt + 2 retries
        });

        it("does not retry a permanent failure", async () => {
            const error = httpError(400);
            const fn = jest.fn().mockRejectedValue(error);

            await expect(withRetry(fn, { delay: 0 })).rejects.toBe(error);
            expect(fn).toHaveBeenCalledTimes(1);
        });

        it("retries a network error, which has no response at all", async () => {
            const fn = jest
                .fn()
                .mockRejectedValueOnce(networkError())
                .mockResolvedValue("saved");

            await expect(withRetry(fn, { delay: 0 })).resolves.toBe("saved");
            expect(fn).toHaveBeenCalledTimes(2);
        });

        it("backs off exponentially between attempts", async () => {
            const timeout = jest.spyOn(global, "setTimeout");
            const fn = jest.fn().mockRejectedValue(httpError(500));

            await expect(
                withRetry(fn, { retries: 3, delay: 10 }),
            ).rejects.toBeDefined();

            const delays = timeout.mock.calls.map((call) => call[1]);
            expect(delays).toEqual([10, 20, 40]);
            timeout.mockRestore();
        });
    });
});
