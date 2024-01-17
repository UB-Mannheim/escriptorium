export function bootHelp() {
    var closed = userProfile.get("closedHelps") || [];

    let clBtns = document.querySelectorAll(".help-text .close");
    clBtns.forEach((e) =>
        e.addEventListener("click", function (ev) {
            let btn = ev.target.closest("button");
            let alert = btn.parentNode;
            let container = alert.parentNode;
            if (!closed) closed = [];
            if (alert.getAttribute("id")) {
                closed.push(alert.getAttribute("id"));
                userProfile.set("closedHelps", closed);
            }
            alert.style.display = "none";
        }),
    );

    let btns = document.querySelectorAll("button.help");
    btns.forEach((e) =>
        e.addEventListener("click", function (ev) {
            let btn = ev.target.closest("button");
            let container = btn.parentNode;
            let helpText = container.querySelector(".alert.help-text");
            let helpIndex = closed.indexOf(container.getAttribute("id"));
            if (window.getComputedStyle(helpText).display == "none") {
                // open
                if (helpIndex != -1) closed.splice(helpIndex, 1);
                container.querySelector(".alert.help-text").style.display =
                    "block";
            } else {
                // close
                if (helpIndex == -1) closed.push(container.getAttribute("id"));
                container.querySelector(".alert.help-text").style.display =
                    "none";
            }
            userProfile.set("closedHelps", closed);
        }),
    );

    if (closed) {
        closed.forEach(function (e, i) {
            let help = document.querySelector(".help-text#" + e);
            if (help) help.style.display = "none";
        });
    }
}
