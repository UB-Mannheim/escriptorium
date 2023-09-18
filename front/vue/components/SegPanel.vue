<template>
    <div class="col panel">
        <div
            v-if="legacyModeEnabled"
            class="tools"
        >
            <i
                title="Segmentation Panel"
                class="panel-icon fas fa-align-left"
            />
            <div class="btn-group">
                <button
                    id="undo"
                    ref="undo"
                    title="Undo. (Ctrl+Z)"
                    class="btn btn-sm btn-outline-dark ml-3 fas fa-undo"
                    autocomplete="off"
                    disabled
                />
                <button
                    id="redo"
                    ref="redo"
                    title="Redo. (Ctrl+Y)"
                    class="btn btn-sm btn-outline-dark fas fa-redo"
                    autocomplete="off"
                    disabled
                />
            </div>

            <div class="btn-group">
                <button
                    id="toggle-settings"
                    title="Editor settings."
                    class="btn btn-sm btn-info ml-3 fas fa-cogs dropdown-toggle"
                    type="button"
                    data-toggle="dropdown"
                />
                <div
                    id="be-settings-menu"
                    class="dropdown-menu"
                >
                    <div>
                        <label for="be-even-bl-color">Baselines</label>
                        <br><input
                            id="be-bl-color"
                            type="color"
                        >
                    </div>
                    <div>
                        <label for="be-dir-color">Line direction hints (by type)</label>
                        <br>
                        <input
                            id="be-dir-color-0"
                            type="color"
                            title="None"
                        >
                        <input
                            v-for="(type, index) in $store.state.document.types.lines"
                            :id="'be-dir-color-' + (index + 1)"
                            :key="'BT' + type + index"
                            type="color"
                            :data-type="type.name"
                            :title="type.name"
                        >
                    </div>
                    <div>
                        <label for="be-reg-color">Regions (by type)</label>
                        <br>
                        <input
                            id="be-reg-color-0"
                            type="color"
                            title="None"
                        >
                        <input
                            v-for="(type, index) in $store.state.document.types.regions"
                            :id="'be-reg-color-' + (index + 1)"
                            :key="'LT' + type + index"
                            type="color"
                            :data-type="type.name"
                            :title="type.name"
                        >
                    </div>
                    <!-- <div class="dropdown-divider"></div> -->
                    <!-- Line thickness<input type="slider"/> -->
                </div>
            </div>

            <button
                v-if="hasBinaryColor"
                id="toggle-binary"
                :class="[colorMode == 'binary' ? 'btn-success' : 'btn-info']"
                title="Toggle binary image."
                class="btn btn-sm fas fa-adjust"
                autocomplete="off"
                @click="toggleBinary"
            />
            <div class="btn-group">
                <button
                    id="be-toggle-regions"
                    title="Switch to region mode. (R)"
                    class="btn btn-sm btn-info fas fa-th-large"
                    autocomplete="off"
                />

                <button
                    id="be-toggle-line-mode"
                    title="Toggle line masks and stroke width. (M)"
                    class="btn btn-sm btn-info fas fa-mask"
                />
            </div>
            <div class="btn-group">
                <button
                    id="be-split-lines"
                    title="Cut through lines. (C)"
                    class="btn btn-sm btn-warning fas fa-cut"
                />
            </div>

            <div class="btn-group">
                <button
                    id="be-toggle-order"
                    title="Toggle ordering display. (L)"
                    class="btn btn-sm btn-info fas fa-sort-numeric-down"
                    autocomplete="off"
                />
                <button
                    id="toggle-auto-order"
                    title="Toggle automatic reordering on line creation/deletion."
                    class="btn btn-sm fas fa-robot"
                    :class="[autoOrder ? 'btn-success' : 'btn-info']"
                    @click="toggleAutoOrder"
                />
                <button
                    v-if="!autoOrder"
                    id="manualOrder"
                    title="Reorder line automatically"
                    class="btn btn-sm btn-info fas fa-sort"
                    @click="recalculateOrdering"
                />
            </div>

            <button
                v-if="
                    !$store.getters['lines/hasMasks'] && $store.state.lines.all.length > 0
                "
                class="btn btn-sm btn-success fas fa-thumbs-up ml-auto"
                title="Segmentation is ready for mask calculation!"
                @click="processLines"
            />
            <button
                id="segmentation-help-ben"
                data-toggle="collapse"
                data-target="#segmentation-help"
                title="Help."
                class="btn btn-sm btn-info fas fa-question help nav-item ml-2"
            />
            <div
                id="segmentation-help"
                class="alert alert-primary help-text collapse"
            >
                <button
                    type="button"
                    data-toggle="collapse"
                    data-target="#segmentation-help"
                    class="close"
                    aria-label="Close"
                >
                    <span aria-hidden="true">&times;</span>
                </button>
                <help />
            </div>
        </div>
        <SegmentationToolbar
            v-else
            ref="segmentation-toolbar"
            :display-mode="(segmenter && segmenter.mode) || 'lines'"
            :can-redo="undoManager && undoManager.hasRedo()"
            :can-undo="undoManager && undoManager.hasUndo()"
            :disabled="isWorking"
            :has-selection="hasSelection"
            :has-points-selection="hasPointsSelection"
            :line-numbering-enabled="(segmenter && segmenter.showLineNumbers) || false"
            :on-change-mode="onChangeMode"
            :on-change-selection-type="onChangeType"
            :on-delete="onDelete"
            :on-link-unlink="onLinkUnlink"
            :on-join="onJoin"
            :on-toggle-line-numbering="onToggleLineNumbering"
            :on-redo="redo"
            :on-reverse="onReverse"
            :on-undo="undo"
            :selected-type="selectedType"
            :selection-is-linked="selectionIsLinked"
            :toggle-tool="onToggleTool"
            :tool="activeTool"
        />
        <div
            v-if="legacyModeEnabled"
            id="context-menu"
        >
            <button
                id="be-link-region"
                title="Link selected lines to (the first detected) background region. (Y)"
                class="hide btn btn-info m-1 fas fa-link"
            />
            <button
                id="be-unlink-region"
                title="Unlink selected lines from their region. (U)"
                class="hide btn btn-info m-1 fas fa-unlink"
            />
            <button
                id="be-merge-selection"
                title="Join selected lines. (J)"
                class="hide btn btn-info fas m-1 fa-compress-arrows-alt"
            />
            <button
                id="be-reverse-selection"
                title="Reverse selected lines. (I)"
                class="hide btn btn-info fas m-1 fa-arrows-alt-h"
            />
            <button
                id="be-set-type"
                title="Set the type on all selected lines/regions. (T)"
                class="btn m-1 btn-info fas fa-text-height"
            />
            <button
                id="be-delete-point"
                title="Delete selected points. (ctrl+suppr)"
                class="hide btn btn-warning m-1 fas fa-trash"
            />
            <button
                id="be-delete-selection"
                title="Delete all selected lines/regions. (suppr)"
                class="btn m-1 btn-danger fas fa-trash"
            />
        </div>

        <div id="info-tooltip" />

        <div
            :class="{ 'content-container': true, 'pan-active': activeTool === 'pan' }"
        >
            <div
                id="seg-zoom-container"
                ref="segZoomContainer"
                class="content"
            >
                <div
                    v-if="loaded"
                    id="seg-data-binding"
                >
                    <segregion
                        v-for="region in $store.state.regions.all"
                        :key="'sR' + region.pk"
                        :region="region"
                    />
                    <segline
                        v-for="line in $store.state.lines.all"
                        :key="'sL' + line.pk"
                        :line="line"
                    />
                </div>

                <img
                    ref="img"
                    class="panel-img"
                >
                <!-- TODO: make line overlay component -->
                <div
                    id="segmentation-overlay"
                    class="overlay panel-overlay"
                    :class="{working: isWorking}"
                >
                    <svg
                        width="100%"
                        height="100%"
                    >
                        <defs>
                            <mask id="seg-overlay">
                                <rect
                                    x="0"
                                    y="0"
                                    width="100%"
                                    height="100%"
                                    fill="white"
                                />
                                <polygon points="" />
                            </mask>
                        </defs>
                        <rect
                            x="0"
                            y="0"
                            fill="grey"
                            opacity="0.5"
                            width="100%"
                            height="100%"
                            mask="url(#seg-overlay)"
                        />
                    </svg>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
/*
   Baseline editor panel (or segmentation panel)
 */
import { mapActions, mapState } from "vuex";
import { BasePanel } from "../../src/editor/mixins.js";
import SegRegion from "./SegRegion.vue";
import SegLine from "./SegLine.vue";
import SegmentationToolbar from "./SegmentationToolbar/SegmentationToolbar.vue";
import Help from "./Help.vue";
import { Segmenter } from "../../src/baseline.editor.js";

export default Vue.extend({
    components: {
        segline: SegLine,
        segregion: SegRegion,
        help: Help,
        SegmentationToolbar,
    },
    mixins: [BasePanel],
    props: {
        fullsizeimage: {
            type: Boolean,
            required: true,
        },
        /**
         * Whether or not legacy mode is enabled on this instance.
         */
        legacyModeEnabled: {
            type: Boolean,
            required: true,
        }
    },
    data() {
        return {
            segmenter: { loaded: false },
            imageLoaded: false,
            colorMode: "color", //  color - binary - grayscale
            undoManager: new UndoManager(),
            isWorking: false,
            autoOrder: userProfile.get("autoOrder", true),
        };
    },
    computed: {
        ...mapState({
            activeTool: (state) => state.globalTools.activeTool,
        }),
        hasBinaryColor() {
            return (
                this.$store.state.parts.loaded &&
        this.$store.state.parts.bw_image !== null
            );
        },
        loaded() {
            // for this panel we need both the image and the segmenter
            return this.segmenter && this.segmenter.loaded && this.imageLoaded;
        },
        imageSrc() {
            // empty the src to make sure the complete event gets fired
            // this.$img.src = '';
            if (!this.$store.state.parts.loaded) return "";
            // overrides imageSrc to deal with color modes
            // Note: vue.js doesn't have super call wtf we need to copy the code :(
            let src =
        (!this.fullsizeimage &&
         this.$store.state.parts.image.thumbnails !== undefined &&
         this.$store.state.parts.image.thumbnails.large) ||
        this.$store.state.parts.image.uri;

            let bwSrc =
        (this.colorMode == "binary" &&
          this.$store.state.parts.bw_image &&
          this.$store.state.parts.bw_image.uri) ||
        src;

            return bwSrc;
        },
        /**
         * Return true if there are any segments, regions, or lines selected.
         */
        hasSelection() {
            return (
                this.segmenter?.selection?.segments?.length !== 0 ||
                this.segmenter?.selection?.regions?.length !== 0 ||
                this.segmenter?.selection?.lines?.length !== 0
            ) || false;
        },
        /**
         * Return true if there are any segments selected.
         */
        hasPointsSelection() {
            return this.segmenter?.selection?.segments?.length !== 0 || false;
        },
        /**
         * Return true if there is any line selected that is linked to a region.
         */
        selectionIsLinked() {
            return (this.segmenter?.regions?.length > 0 &&
                    this.segmenter.selection?.lines?.filter(
                        (l) => l.region !== null
                    ).length > 0
            ) || false;
        },
        /**
         * Returns the selected type name, if all selected lines or regions are the same type,
         * or else returns "None".
         */
        selectedType() {
            if (
                this.segmenter?.selection?.lines?.length && this.segmenter.selection.lines.every(
                    (line, _, lines) => line.type === lines[0].type,
                )
            ) {
                return this.segmenter.selection.lines[0].type || "None";
            } else if (
                this.segmenter?.selection?.regions?.length &&
                this.segmenter.selection.regions.every(
                    (reg, _, regions) => reg.type === regions[0].type
                )
            ) {
                return this.segmenter.selection.regions[0].type || "None";
            } else {
                return "None";
            }
        },
    },
    watch: {
        activeTool: function (tool, _) {
            // set active tool on segmenter
            this.segmenter.activeTool = tool;

            // handle other per-tool state requirements
            if (tool === "cut") {
                this.segmenter.splitting = !this.segmenter.splitting;
            } else {
                this.segmenter.splitting = false;
            }

            // change the cursor according to the active tool
            this.segmenter.setCursor();
        },
        "$store.state.parts.loaded": function (isLoaded, wasLoaded) {
            if (isLoaded === true) {
                if (this.colorMode !== "binary" && !this.hasBinaryColor) {
                    this.colorMode = "color";
                }
                this.initSegmenter();
            } else {
                this.segmenter.reset();
                this.undoManager.clear();
                this.refreshHistoryBtns();
            }
        },
        colorMode: function (n, o) {
            this.$parent.prefetchImage(
                this.imageSrc,
                function (src) {
                    this.setImageSource(src);
                    this.refreshSegmenter();
                }.bind(this)
            );
        },
        fullsizeimage: function (n, o) {
            // it was prefetched
            if (n && n != o) {
                this.setImageSource(this.imageSrc);
                this.segmenter.scale = 1;
                this.segmenter.refresh();
            }
        },
        "$store.state.document.blockShortcuts": function(n, o) {
            // make sure the segmenter does not trigger keyboard shortcuts either
            this.segmenter.disableShortcuts = n;
        },
    },
    mounted() {
    // wait for the element to be rendered
        Vue.nextTick(
            function () {
                this.$store.commit("lines/setAutoOrdering", this.autoOrder);

                this.$parent.zoom.register(this.$refs.segZoomContainer, { map: true });
                let beSettings =
          userProfile.get("baseline-editor-" + this.$store.state.document.id) ||
          {};
                this.$img = this.$refs.img;

                this.segmenter = new Segmenter(this.$img, {
                    delayInit: true,
                    idField: "pk",
                    defaultTextDirection:
            this.$store.state.document.mainTextDirection.slice(-2),
                    regionTypes: this.$store.state.document.types.regions.map(
                        (t) => t.name
                    ),
                    lineTypes: this.$store.state.document.types.lines.map((t) => t.name),
                    baselinesColor: beSettings["color-baselines"] || null,
                    regionColors: beSettings["color-regions"] || null,
                    directionHintColors: beSettings["color-directions"] || null,
                    newUiEnabled: !this.legacyModeEnabled,
                    toolbar: this.$refs["segmentation-toolbar"]?.$el,
                    toolbarSubmenuIds: [
                        // for click handling on toolbar, list all submenu node IDs here
                        "type-select-menu",
                    ],
                    activeTool: this.activeTool,
                });
                // we need to move the baseline editor canvas up one tag so that it doesn't get caught by wheelzoom.
                let canvas = this.segmenter.canvas;
                canvas.parentNode.parentNode.appendChild(canvas);

                // already mounted with a part = opening the panel after page load
                if (this.$store.state.parts.loaded) {
                    this.initSegmenter();
                }

                // Prevent shortcuts from interfering with the searchbox in the navbar and conversely
                let searchbox = document.getElementById("navbar-searchbox")
                if (searchbox) {
                    searchbox.addEventListener(
                        "focus",
                        function (e) {
                            this.$store.commit("document/setBlockShortcuts", true);
                        }.bind(this)
                    );
                    searchbox.addEventListener(
                        "blur",
                        function (e) {
                            this.$store.commit("document/setBlockShortcuts", false);
                        }.bind(this)
                    );
                }

                // simulates wheelzoom for canvas
                var zoom = this.$parent.zoom;
                zoom.events.addEventListener(
                    "wheelzoom.updated",
                    function (e) {
                        this.updateZoom(e.detail);
                    }.bind(this)
                );
                this.updateZoom(zoom);

                this.segmenter.events.addEventListener(
                    "baseline-editor:settings",
                    function (ev) {
                        let key = "baseline-editor-" + this.$store.state.document.id;
                        let settings = userProfile.get(key) || {};
                        settings[event.detail.name] = event.detail.value;
                        userProfile.set(key, settings);
                    }.bind(this)
                );
                this.segmenter.events.addEventListener(
                    "baseline-editor:delete",
                    function (ev) {
                        let data = ev.detail;
                        this.bulkDelete(data);
                        this.pushHistory(
                            function () {
                                this.bulkCreate(data, true);
                            }.bind(this),
                            function () {
                                this.bulkDelete(data);
                            }.bind(this)
                        );
                    }.bind(this)
                );
                this.segmenter.events.addEventListener(
                    "baseline-editor:merge",
                    async (ev) => {
                        const data = ev.detail;
                        this.isWorking = true;
                        try {
                            await this.merge(data); // Updates data and adds createdLine
                        } catch (error) {
                            console.warn("Failed to merge lines:", error);
                            this.isWorking = false;
                            return;
                        }

                        this.pushHistory(
                            () => {
                                this.bulkDelete({ lines: [data.createdLine] });
                                this.bulkCreate(data, true);
                            },
                            () => {
                                this.bulkDelete(data);
                                this.bulkCreate({ lines: [data.createdLine]}, true);
                            }
                        )

                        this.isWorking = false;
                    }
                );
                this.segmenter.events.addEventListener(
                    "baseline-editor:update",
                    function (ev) {
                        // same event for creation and modification of a line/region
                        let data = ev.detail;
                        this.extractPrevious(data);
                        let toCreate = {
                            lines:
                (data.lines &&
                  data.lines.filter((l) => l.context.pk === null)) ||
                [],
                            regions:
                (data.regions &&
                  data.regions.filter((l) => l.context.pk === null)) ||
                [],
                        };
                        let toUpdate = {
                            lines:
                (data.lines &&
                  data.lines.filter((l) => l.context.pk !== null)) ||
                [],
                            regions:
                (data.regions &&
                  data.regions.filter((l) => l.context.pk !== null)) ||
                [],
                        };
                        this.bulkCreate(toCreate, false);
                        this.bulkUpdate(toUpdate);
                        this.pushHistory(
                            function () {
                                // undo
                                this.bulkDelete(toCreate);
                                this.bulkUpdate({
                                    lines: toUpdate.lines.map((l) => l.previous),
                                    regions: toUpdate.regions.map((r) => r.previous),
                                });
                            }.bind(this),
                            function () {
                                // redo
                                this.bulkCreate(toCreate, true);
                                this.bulkUpdate(toUpdate);
                            }.bind(this)
                        );
                    }.bind(this)
                );
            }.bind(this)
        );

        // history
        if (this.legacyModeEnabled) {
            this.$refs.undo.addEventListener(
                "click",
                function (ev) {
                    this.undo();
                }.bind(this)
            );
            this.$refs.redo.addEventListener(
                "click",
                function (ev) {
                    this.redo();
                }.bind(this)
            );
        }

        // when undo or redo completes, turn off isWorking
        this.undoManager.setCallback(() => this.isWorking = false);

        this.$refs.img.addEventListener(
            "load",
            function (ev) {
                this.onImageLoaded();
            }.bind(this)
        );

        document.addEventListener(
            "keyup",
            function (ev) {
                if (ev.ctrlKey) {
                    if (ev.key == "z") this.undo();
                    if (ev.key == "y") this.redo();
                }
            }.bind(this)
        );
    },
    methods: {
        ...mapActions("globalTools", ["toggleTool"]),
        toggleBinary(ev) {
            if (this.colorMode == "color") this.colorMode = "binary";
            else this.colorMode = "color";
        },

        toggleAutoOrder(ev) {
            this.autoOrder = !this.autoOrder;
            this.$store.commit("lines/setAutoOrdering", this.autoOrder);
            userProfile.set("autoOrder", this.autoOrder);
        },

        pushHistory(undo, redo) {
            this.undoManager.add({
                undo: undo,
                redo: redo,
            });
            this.refreshHistoryBtns();
        },
        initSegmenter() {
            this.$parent.prefetchImage(
                this.imageSrc,
                function (src) {
                    this.setImageSource(src);
                    this.refreshSegmenter();
                }.bind(this)
            );
        },
        setImageSource(src) {
            this.$img.src = src;
            this.imageLoaded = false;
        },
        refreshSegmenter() {
            Vue.nextTick(
                function () {
                    if (!this.$store.state.parts.image || this.$img.naturalWidth === 0) {
                        console.warn("refreshSegmenter called with no image");
                        return;
                    }
                    this.segmenter.scale =
            this.$img.naturalWidth / this.$store.state.parts.image.size[0];
                    if (this.segmenter.loaded) {
                        this.segmenter.refresh();
                    } else {
                        this.segmenter.init({ newUiEnabled: !this.legacyModeEnabled });
                    }
                }.bind(this)
            );
        },
        updateZoom(zoom) {
            // might not be mounted yet
            if (this.segmenter && this.$img.complete) {
                this.segmenter.canvas.style.top = zoom.pos.y + "px";
                this.segmenter.canvas.style.left = zoom.pos.x + "px";
                this.segmenter.refresh();
            }
        },
        updateView() {
            // We REALLY need to check that SegPanel is opened
            // (with this.$store.state.document.visible_panels.segmentation == true)
            // before trying to refresh the segmenter.
            // If SegPanel is closed, paper.js will try to transform a null canvas and
            // will throw multiple errors in the browser console when the mouse is moving.
            if (
                this.segmenter.loaded &&
        this.$store.state.document.visible_panels.segmentation
            ) {
                this.segmenter.refresh();
            }
        },
        // undo manager helpers
        async bulkCreate(data, createInEditor) {
            if (data.regions && data.regions.length) {
                // note: regions dont get a bulk_create
                for (let i = 0; i < data.regions.length; i++) {
                    try {
                        const newRegion = await this.$store.dispatch("regions/create", {
                            pk: data.regions[i].id,
                            box: data.regions[i].box,
                            type: data.regions[i].type,
                        });
                        if (createInEditor) {
                            this.segmenter.loadRegion(newRegion);
                        }
                        // also update pk in the original data for undo/redo
                        data.regions[i].context.pk = newRegion.pk;
                        this.$store.commit("regions/load", newRegion.pk);
                    } catch (err) {
                        console.log("couldn't create region", err);
                    }
                }
            }
            if (data.lines && data.lines.length) {
                try {
                    const newLines = await this.$store.dispatch("lines/bulkCreate", {
                        lines: data.lines.map((l) => {
                            const mapped = {
                                pk: l.pk,
                                baseline: l.baseline,
                                mask: l.mask,
                                region: (l.region && l.region.context.pk) || null,
                            };

                            if (l.transcriptionsForUndelete) {
                                mapped.transcriptions = l.transcriptionsForUndelete?.map(
                                    (t) => {
                                        return {
                                            content: t.content,
                                            transcription: t.transcription,
                                        };
                                    }
                                );
                            }

                            return mapped;
                        }),
                        transcription:
              this.$store.state.transcriptions.selectedTranscription,
                    });
                    for (let i = 0; i < newLines.length; i++) {
                        let line = newLines[i];
                        // create a new line in case the event didn't come from the editor
                        if (createInEditor) {
                            let region = this.segmenter.regions.find(
                                (r) => r.context.pk == line.region
                            );
                            this.segmenter.loadLine(line, region);
                        }
                        // update the segmenter pk
                        data.lines[i].context.pk = line.pk;
                        this.$store.commit("lines/load", line.pk);
                    }
                } catch (err) {
                    console.log("couldn't create lines", err);
                }
            }
        },
        async bulkUpdate(data) {
            if (data.regions && data.regions.length) {
                for (let i = 0; i < data.regions.length; i++) {
                    try {
                        let region = data.regions[i];
                        const updatedRegion = await this.$store.dispatch("regions/update", {
                            pk: region.context.pk,
                            box: region.box,
                            type: region.type,
                        });
                        let segmenterRegion = this.segmenter.regions.find(
                            (r) => r.context.pk == updatedRegion.pk
                        );
                        segmenterRegion.update(updatedRegion.box);
                    } catch (err) {
                        console.log("couldn't update region", err);
                    }
                }
            }
            if (data.lines && data.lines.length) {
                try {
                    const updatedLines = await this.$store.dispatch(
                        "lines/bulkUpdate",
                        data.lines.map((l) => {
                            return {
                                pk: l.context.pk,
                                baseline: l.baseline,
                                mask: l.mask,
                                region: l.region && l.region.context.pk,
                                type: l.type,
                            };
                        })
                    );
                    for (let i = 0; i < updatedLines.length; i++) {
                        let line = updatedLines[i];
                        let region =
              this.segmenter.regions.find((r) => r.context.pk == line.region) ||
              null;
                        let segmenterLine = this.segmenter.lines.find(
                            (l) => l.context.pk == line.pk
                        );
                        segmenterLine.update(line.baseline, line.mask, region, line.order);
                    }
                } catch (err) {
                    console.log("couldn't update line", err);
                }
            }
        },

        async deleteRegion(region) {
            try {
                this.$store.dispatch(
                    "regions/delete",
                    region.context.pk
                );
                let segRegion = this.segmenter.regions.find(
                    (r) => r.context.pk == region.context.pk
                );
                if (segRegion) segRegion.remove();
            } catch (err) {
                console.log(
                    "couldn't delete region #",
                    region.context.pk,
                    err
                );
            }
        },

        async bulkDelete(data) {
            if (data.regions && data.regions.length) {
                // regions don't have a bulk delete
                await Promise.all(data.regions.map((r) => this.deleteRegion(r)));
            }
            if (data.lines && data.lines.length) {
                try {
                    const { deletedPKs, deletedLines } = await this.$store.dispatch(
                        "lines/bulkDelete",
                        data.lines.map((l) => l.context.pk)
                    );
                    this.processDeleteResponse(data, deletedPKs, deletedLines);
                } catch (err) {
                    console.error("couldn't bulk delete lines", err);
                }
            }
        },

        processDeleteResponse(data, deletedPKs, deletedLines) {
            // Remove the lines from the segmenter
            const segmenterLines = this.segmenter.lines.filter(
                (l) => deletedPKs.indexOf(l.context.pk) >= 0
            );

            for (const line of segmenterLines) {
                line.remove();
            }

            // Update the original data.lines - adding the transcriptions, because we will want to pass them on to bulkCreate.
            // The same data object is placed in the undo stack, so changing the lines in place is enough
            for (const deletedLine of deletedLines) {
                const dataLine = data.lines.find(
                    (l) => l.context.pk === deletedLine.pk
                );
                if (!dataLine) {
                    console.warn(
                        `Response of bulkDelete contained line ${deletedLine.pk} which we have never tried to delete`
                    );
                    continue;
                }
                dataLine.transcriptionsForUndelete = deletedLine.transcriptions;
            }
        },

        async merge(data) {
            const { createdLine, deletedPKs, deletedLines } =
        await this.$store.dispatch(
            "lines/merge", {
                pks: data.lines.map((l) => l.context.pk),
                transcription: this.$store.state.transcriptions.selectedTranscription,
            }
        );
            let region = this.segmenter.regions.find(
                (r) => r.context.pk == createdLine.region
            );
            const segmenterLine = this.segmenter.loadLine(createdLine, region);

            // update the segmenter pk
            segmenterLine.context.pk = createdLine.pk;
            data.createdLine = segmenterLine.get();
            this.$store.commit("lines/load", createdLine.pk);
            this.processDeleteResponse(data, deletedPKs, deletedLines);
        },

        extractPrevious(data) {
            // given modifications on lines/regions,
            // update data with a previous attribute containing the current state
            if (data.regions && data.regions.length) {
                data.regions.forEach(
                    function (r) {
                        let region = this.$store.state.regions.all.find(
                            (e) => e.pk == r.context.pk
                        );
                        if (region) {
                            r.previous = {
                                context: r.context,
                                box: region && region.box.slice(), // copy the array
                            };
                        }
                    }.bind(this)
                );
            }
            if (data.lines && data.lines.length) {
                data.lines.forEach(
                    function (l) {
                        let line = this.$store.state.lines.all.find(
                            (e) => e.pk == l.context.pk
                        );
                        if (line) {
                            l.previous = {
                                context: l.context,
                                baseline: line.baseline && line.baseline.slice(),
                                mask: line.mask && line.mask.slice(),
                                region:
                  (line.region &&
                    this.segmenter.regions.find(
                        (r) => r.context.pk == line.region
                    )) ||
                  null,
                            };
                        }
                    }.bind(this)
                );
            }
        },

        async processLines(ev) {
            ev.target.disabled = true;
            await this.$store.dispatch("lines/recalculateMasks");
        },

        async recalculateOrdering(ev) {
            await this.$store.dispatch("lines/recalculateOrdering");
        },

        onImageLoaded() {
            this.imageLoaded = true;
            this.refreshSegmenter();
        },
        /* History */
        undo() {
            this.isWorking = true;
            this.undoManager.undo();
            this.refreshHistoryBtns();
        },
        redo() {
            this.isWorking = true;
            this.undoManager.redo();
            this.refreshHistoryBtns();
        },
        refreshHistoryBtns() {
            if (this.$refs.undo) {
                if (this.undoManager.hasUndo()) this.$refs.undo.disabled = false;
                else this.$refs.undo.disabled = true;
                if (this.undoManager.hasRedo()) this.$refs.redo.disabled = false;
                else this.$refs.redo.disabled = true;
            }
        },
        /**
         * Change the mode between lines, regions, and masks.
         *
         * @param {String} value One of "lines", "regions", or "masks"
         */
        onChangeMode(value) {
            this.segmenter.purgeSelection();
            if (this.activeTool !== "pan") {
                // set tool back to select (default), unless in pan tool
                this.toggleTool("select");
            }
            this.segmenter.setMode(value);
            switch(value) {
                case "lines":
                    this.segmenter.toggleMasks(false);
                    this.segmenter.toggleLineStrokes(true);
                    this.segmenter.evenMasksGroup.bringToFront();
                    this.segmenter.oddMasksGroup.bringToFront();
                    this.segmenter.linesGroup.bringToFront();
                    break;
                case "regions":
                    this.segmenter.toggleMasks(false);
                    this.segmenter.toggleLineStrokes(false);
                    break;
                case "masks":
                    this.segmenter.toggleMasks(true);
                    this.segmenter.toggleLineStrokes(true);
                    this.segmenter.evenMasksGroup.bringToFront();
                    this.segmenter.oddMasksGroup.bringToFront();
                    this.segmenter.linesGroup.sendToBack();
                    break;
            }
            this.segmenter.applyRegionMode();
        },
        /**
         * Turn line numbering on and off.
         */
        onToggleLineNumbering(e) {
            this.segmenter.setOrdering(e.target.checked);
        },
        /**
         * change the currently active tool
         */
        onToggleTool(tool) {
            // purge the selection before changing tool
            this.segmenter.purgeSelection();

            // use the vuex store callback for toggling the active tool
            this.toggleTool(tool);
        },
        /**
         * Link or unlink depending on state of selection.
         */
        onLinkUnlink() {
            if (this.selectionIsLinked) {
                this.segmenter.unlinkSelection();
            } else if (this.hasSelection) {
                this.segmenter.linkSelection();
            }
        },
        /**
         * Change the type of lines or regions
         *
         * @param {String} type Name of the selected type
         */
        onChangeType(type) {
            this.segmenter.setSelectionType(type);
        },
        /**
         * Delete the currently selected points, lines, or regions
         *
         * @param {Boolean} onlyPoints Whether or not to delete selected points
         */
        onDelete(onlyPoints) {
            if (onlyPoints) {
                this.segmenter.deleteSelectedSegments();
            } else {
                this.segmenter.deleteSelection();
            }
        },
        /**
         * Merge/join the currently selected lines or regions
         */
        onJoin() {
            this.segmenter.mergeSelection();
        },
        /**
         * Reverse the direction of the currently selected lines
         */
        onReverse() {
            this.segmenter.reverseSelection();
        },
    },
});
</script>

<style scoped>
</style>
