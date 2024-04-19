window.Vue = require("vue/dist/vue");

export var BasePanel = {
    // Base class for all editor panels.

    props: {
        /**
         * true if all buttons and controls should be disabled
         */
        disabled: {
            type: Boolean,
            required: true,
        },
        /**
         * Whether or not legacy mode is enabled by the user.
         */
        legacyModeEnabled: {
            type: Boolean,
            required: true,
        },
        /**
         * The index of this panel, to allow swapping in EditorToolbar dropdown
         */
        panelIndex: {
            type: Number,
            default: -1,
        },
    },
    data() {
        return {
            ratio: 1,
        };
    },
    created() {
        // Update ratio on window resize
        window.addEventListener("resize", this.refresh);
    },
    destroyed() {
        window.removeEventListener("resize", this.refresh);
    },
    watch: {
        "$store.state.parts.loaded": function (n, o) {
            if (n) {
                this.refresh();
            }
        },
        "$store.state.document.visible_panels": function (n, o) {
            if (this.$store.state.parts.loaded) {
                this.refresh();
            }
        },
        "$store.state.document.editorPanels": function (n, o) {
            if (this.$store.state.parts.loaded) {
                this.refresh();
            }
        },
    },
    methods: {
        setRatio() {
            this.ratio =
                this.$el.firstChild.clientWidth /
                this.$store.state.parts.image.size[0];
        },
        refresh() {
            this.setRatio();
            this.updateView();
        },
        updateView() {},
    },
};

export var LineBase = {
    props: ["line", "ratio"],
    methods: {
        showOverlay() {
            if (this.line && this.line.mask) {
                Array.from(document.querySelectorAll(".panel-overlay")).map(
                    function (e) {
                        e.classList.add("show");
                        if (this.maskPoints) {
                            e.querySelector("polygon").setAttribute(
                                "points",
                                this.maskPoints,
                            );
                        }
                    }.bind(this),
                );
            }
        },
        hideOverlay() {
            Array.from(document.querySelectorAll(".panel-overlay")).map(
                function (e) {
                    e.classList.remove("show");
                },
            );
        },
    },
    computed: {
        maskPoints() {
            if (this.line == null || !this.line.mask) return "";
            return this.line.mask
                .map(
                    (pt) =>
                        Math.round(pt[0] * this.ratio) +
                        "," +
                        Math.round(pt[1] * this.ratio),
                )
                .join(" ");
        },
    },
};

var KeyValueWidget = function (args) {
    // Annotorious/recogito-js widget to a key/value input in the annotation modal.

    var purpose = "attribute-" + args.name;
    var currentValue = args.annotation
        ? args.annotation.bodies.find((b) => b.purpose == purpose)
        : null;

    var addTag = function (evt) {
        if (currentValue) {
            args.onUpdateBody(currentValue, {
                type: "TextualBody",
                purpose: purpose,
                value: evt.target.value,
            });
        } else {
            args.onAppendBody({
                type: "TextualBody",
                purpose: purpose,
                value: evt.target.value,
            });
        }
    };

    var container = document.createElement("div");
    container.className = "r6o-widget keyvalue-widget r6o-nodrag";
    var wid = "anno-widget-" + args.name;
    var label = document.createElement("label");
    label.htmlFor = wid;
    label.innerText = args.name;
    container.append(label);
    if (args.values.length) {
        var input = document.createElement("select");
        args.values.forEach((v) => {
            let opt = document.createElement("option");
            opt.value = v;
            opt.text = v;
            if (currentValue && currentValue.value == v) opt.selected = true;
            input.append(opt);
        });
    } else {
        var input = document.createElement("input");
        if (currentValue) input.value = currentValue.value;
    }

    input.id = wid;
    container.append(input);
    input.addEventListener("change", addTag);
    return container;
};

export var AnnoPanel = {
    // Base class for panels who integrate annotorious/recogito-js.

    data() {
        return {
            currentTaxonomy: null,
        };
    },
    methods: {
        toggleTaxonomy(taxo) {
            if (this.currentTaxonomy == taxo) {
                this.disableTaxonomy(taxo);
            } else {
                if (this.currentTaxonomy) {
                    this.disableTaxonomy(this.currentTaxonomy);
                }
                this.enableTaxonomy(taxo);
                this.setThisAnnoTaxonomy(taxo);
            }
        },

        disableTaxonomy(taxo) {
            this.anno.readOnly = true;
            this.currentTaxonomy = null;
            document.querySelectorAll(".taxo-group .btn-info").forEach((e) => {
                e.classList.remove("btn-info");
                e.classList.add("btn-outline-info");
            });
        },

        enableTaxonomy(taxo) {
            this.anno.readOnly = false;
            if (taxo) {
                let btn = this.getTaxoButton(taxo);
                if (btn) {
                    btn.classList.remove("btn-outline-info");
                    btn.classList.add("btn-info");
                }
            }
        },

        getTaxoButton(taxo) {
            return document.getElementById("anno-taxo-" + taxo.pk);
        },

        setThisAnnoTaxonomy(taxo) {
            throw "override this method in the subclass!";
        },

        setAnnoTaxonomy(taxo) {
            this.currentTaxonomy = taxo;

            if (taxo.has_comments || taxo.components.length) {
                this.anno.disableEditor = false;
            } else {
                // this.anno.disableEditor = true;
            }
            let widgets = [];
            if (taxo.has_comments) {
                widgets.push("COMMENT");
            }
            taxo.components.forEach((compo) => {
                widgets.push({
                    widget: KeyValueWidget,
                    name: compo.name,
                    values: compo.allowed_values,
                });
            });
            this.anno.widgets = widgets;
        },

        getAPIAnnotationBody(annotation) {
            return {
                part: this.$store.state.parts.pk,
                taxonomy: annotation.taxonomy ? annotation.taxonomy.pk : null,
                comments: [
                    ...annotation.body.filter((e) => e.purpose == "commenting"),
                ].map((b) => b.value),
                components: [
                    ...annotation.body.filter((e) =>
                        e.purpose.startsWith("attribute"),
                    ),
                ].map((b) => {
                    return {
                        component: annotation.taxonomy.components.find(
                            (c) => "attribute-" + c.name == b.purpose,
                        ).pk,
                        value: b.value,
                    };
                }),
            };
        },
    },
};
