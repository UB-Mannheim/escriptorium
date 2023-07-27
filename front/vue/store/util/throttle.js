import store from "../";

// code from https://upstatement.com/blog/see-you-later-generator/

/**
 * A simple class we create just for tracking our running functions
 */
class Concurrency {
    get(key) {
        return this[key] || {};
    }

    set(key, value) {
        this[key] = value;
    }
}

const concurrencyInstance = new Concurrency();

/**
 *
 * @param {function} generatorFunction to be called
 * @param {number} timeToWait time in milliseconds - default half a second
 */
const throttle = (generatorFunction, timeToWait = 1000) => {
    // I explain how I got this convenient method in a blog post:
    // https://medium.com/stories-from-upstatement/last-vuex-action-hero-f8482c985b27
    // Get the name of the last action called
    const { name } = store.state.lastDispatchedAction;

    // See if there is a stored function with the same name as the one we are trying
    const instanceFunction = concurrencyInstance.get(name);

    // If there is, stop it from running
    if (instanceFunction.return) {
        instanceFunction.return();
    }

    // Reset it with the new version of the function we just received
    const newInstance = generatorFunction();
    concurrencyInstance.set(name, newInstance);

    // An internal function that will actually execute our generator function
    const run = async () => {
        // Go to the next yield block
        const result = newInstance.next();

        // Generator functions have a concept of `done`
        // Which means they have completed any task written or been cancelled
        if (result.done) {
            return result.value;
        } else {
            // if it is not finished, wait for the promise to resolve and go onto the next promise
            await result.value;
            run();
        }
    };

    // Wait a small amount of time before actually completing the function
    // Meaning we won't ever call the same function more than once in a small period of time
    setTimeout(run, timeToWait);
};

export { throttle, concurrencyInstance };
