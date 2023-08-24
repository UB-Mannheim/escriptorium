export var msgSocket;

var alerts = {};
export class Alert {
    constructor(id, message, level, links) {
        this.id = id;
        this.count = 1;
        this.message = message;
        this.level = level || "info";
        this.links = links;
        var $new = $(".alert", "#alert-tplt").clone();
        $new.addClass("alert-" + this.level);
        $(".message", $new).html(message);
        if (this.links !== undefined) {
            for (let i = 0; i < this.links.length; i++) {
                let link = $("<div>").html(
                    '<a href="' +
                        this.links[i].src +
                        '" target="_blank">' +
                        this.links[i].text +
                        "</a>",
                );
                if (this.links[i].cssClass)
                    $("a", link).addClass(this.links[i].cssClass);
                if (this.links[i].targetBlank === false)
                    $("a", link).removeAttr("target");
                $(".additional", $new).append(link).css("display", "block");
            }
        }
        this.$element = $new;
        this.htmlElement = this.$element.get(0);
        $("#alerts-container").append($new);
        $new.show();

        this.$element.on(
            "closed.bs.alert",
            $.proxy(function () {
                delete alerts[this.id];
            }, this),
        );
    }

    static add(id, message, level, link) {
        var id_ = id || new Date().getTime();
        if (alerts[id_] === undefined) {
            alerts[id_] = new Alert(id_, message, level, link);
        } else {
            alerts[id_].incrementCounter();
        }
        return alerts[id_];
    }

    incrementCounter() {
        this.count++;
        $(".counter", this.$element)
            .text("(" + this.count + ")")
            .show();
    }
}

export function bootWebsocket() {
    let scheme = location.protocol === "https:" ? "wss:" : "ws:";
    msgSocket = new ReconnectingWebSocket(
        scheme + "//" + window.location.host + "/ws/notif/",
    );
    msgSocket.maxReconnectAttempts = 3;

    msgSocket.addEventListener("open", function (e) {
        if (DEBUG) {
            console.log("Connected to notification socket");
        }
    });

    msgSocket.addEventListener("message", function (e) {
        var data = JSON.parse(e.data);
        if (DEBUG) {
            console.log("Received ws message: ", data);
        }

        if (data.type == "message") {
            var message = data["text"];
            Alert.add(data["id"], message, data["level"], data["links"]);
        } else if (data.type == "event") {
            var $container = $("#alerts-container");
            $container.trigger(data["name"], data["data"]);
        }
    });

    msgSocket.addEventListener("close", function (e) {
        if (DEBUG) {
            console.error("Notification socket closed unexpectedly");
        }
    });
}

export function joinDocumentRoom(pk) {
    msgSocket.addEventListener("open", function (e) {
        msgSocket.send(
            '{"type": "join-room", "object_cls": "document", "object_pk": ' +
                pk +
                " }",
        );
    });
}
