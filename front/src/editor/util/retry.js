// Retrying helper for the editor's save calls.
//
// The segmentation editor saves as you draw: a region or line exists on the
// canvas before the request that persists it resolves. A dropped request
// therefore leaves something on screen that was never saved, so it's worth
// retrying anything that might succeed on a second attempt.

// Statuses that are worth another try. Anything else (400 validation, 403,
// 404, ...) will fail identically however many times we send it.
const TRANSIENT_STATUSES = [408, 429, 500, 502, 503, 504];

/**
 * True if the error looks like it might not happen again.
 */
export const isTransient = (error) => {
    const status = error?.response?.status;
    // no response at all: network error, timeout, server restarting
    if (status === undefined) return true;
    return TRANSIENT_STATUSES.includes(status);
};

/**
 * Call fn, retrying on transient failures with an exponential backoff.
 * Rethrows the last error once the attempts are exhausted, so callers still
 * get to report the failure.
 */
export const withRetry = async (fn, { retries = 2, delay = 500 } = {}) => {
    for (let attempt = 0; ; attempt++) {
        try {
            return await fn();
        } catch (error) {
            if (attempt >= retries || !isTransient(error)) throw error;
            await new Promise((resolve) =>
                setTimeout(resolve, delay * Math.pow(2, attempt)),
            );
        }
    }
};
