export function bootModels() {
    let $alertsContainer = $("#alerts-container");

    let max_accuracy = {};

    $("#models-table tr.model-head").each(function (i, e) {
        max_accuracy[$(e).data("id")] = $(
            "td#accuracy-" + $(e).data("id"),
            e,
        ).data("value");
    });

    $alertsContainer.on("training:start", function (ev, data) {
        let $row = $("tr#tr-" + data.id);
        $(".training-ongoing", $row).show();
        $(".training-done", $row).hide();
        $(".training-error", $row).hide();
        $(".cancel-training", $row).show();
    });
    $alertsContainer.on("training:gathering", function (ev, data) {
        let $row = $("tr#tr-" + data.id);
        $(".training-ongoing", $row).show();
        $(".training-done", $row).hide();
        $(".training-error", $row).hide();
        $(".training-gathering", $row).css("display", "flex");
        $(".training-gathering .progress-bar", $row).css(
            "width",
            Math.round((data.index / data.total) * 100) + "%",
        );
        $(".cancel-training", $row).show();
    });
    $alertsContainer.on("training:eval", function (ev, data) {
        let $row = $("tr#tr-" + data.id);
        $(".training-ongoing", $row).show();
        $(".training-done", $row).hide();
        $(".training-error", $row).hide();
        $(".training-gathering", $row).hide();
        if (max_accuracy[data.id] < data.accuracy) {
            $row.data("value", data.accuracy);
            $("td#accuracy-" + data.id, $row).text(
                Math.round(data.accuracy * 100 * 100) / 100 + "%",
            );
            max_accuracy[data.id] = data.accuracy;
        }
        $(".cancel-training", $row).show();
    });
    $alertsContainer.on("training:done", function (ev, data) {
        let $row = $("tr#tr-" + data.id);
        $(".training-ongoing", $row).hide();
        $(".training-done", $row).show();
        // $('.training-error', $row).hide();
        $(".training-gathering", $row).hide();
        $(".cancel-training", $row).hide();
    });
    $alertsContainer.on("training:error", function (ev, data) {
        let $row = $("tr#tr-" + data.id);
        $(".training-ongoing", $row).hide();
        $(".training-done", $row).hide();
        $(".training-error", $row).show();
        $(".cancel-training", $row).hide();
    });
}
