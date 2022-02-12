function scriptName() {
    let prefix = document.currentScript.src.split('/').slice(3, -2).join('/');
    return (prefix.length > 0 ? "/" + prefix : "");
}

export const SCRIPT_NAME = scriptName();
