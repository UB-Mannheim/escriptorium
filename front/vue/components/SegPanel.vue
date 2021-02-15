<template>
    <div class="col panel">
        <div class="tools">
            <i title="Segmentation Panel" class="panel-icon fas fa-align-left"></i>
            <div class="btn-group">
                <button id="undo"
                        ref="undo"
                        title="Undo. (Ctrl+Z)"
                        class="btn btn-sm btn-outline-dark ml-3 fas fa-undo"
                        autocomplete="off" disabled></button>
                <button id="redo"
                        ref="redo"
                        title="Redo. (Ctrl+Y)"
                        class="btn btn-sm btn-outline-dark fas fa-redo"
                        autocomplete="off" disabled></button>
            </div>

            <div class="btn-group">
                <button id="toggle-settings"
                        title="Editor settings."
                        class="btn btn-sm btn-info ml-3 fas fa-cogs dropdown-toggle"
                        type="button"
                        data-toggle="dropdown">
                </button>
                <div id="be-settings-menu" class="dropdown-menu">
                    <div>
                        <label for="be-even-bl-color">Baselines</label>
                        <br><input id="be-bl-color" type="color"/>
                    </div>
                    <div>
                        <label for="be-dir-color">Line direction hints (by type)</label>
                        <br>
                        <input  type="color" id="be-dir-color-0" title="None">
                        <input  type="color"
                                v-for="(type, index) in $store.state.document.types.lines"
                                :key="'BT' + type + index"
                                v-bind:data-type="type.name"
                                v-bind:title="type.name"
                                v-bind:id="'be-dir-color-'+(index+1)"/>
                    </div>
                    <div>
                        <label for="be-reg-color">Regions (by type)</label>
                        <br>
                        <input  type="color" id="be-reg-color-0" title="None">
                        <input  type="color"
                                v-for="(type, index) in $store.state.document.types.regions"
                                :key="'LT' + type + index"
                                v-bind:data-type="type.name"
                                v-bind:title="type.name"
                                v-bind:id="'be-reg-color-'+(index+1)"/>

                    </div>
                    <!-- <div class="dropdown-divider"></div> -->
                    <!-- Line thickness<input type="slider"/> -->
                </div>
            </div>


            <button v-if="hasBinaryColor"
                    @click="toggleBinary"
                    v-bind:class="[colorMode == 'binary' ? 'btn-success' : 'btn-info']"
                    id="toggle-binary"
                    title="Toggle binary image."
                    class="btn btn-sm fas fa-adjust"
                    autocomplete="off"></button>
            <div class="btn-group">
                <button id="be-toggle-regions"
                        title="Switch to region mode. (R)"
                        class="btn btn-sm btn-info fas fa-th-large"
                        autocomplete="off"></button>
                <button id="be-toggle-order"
                        title="Toggle ordering display. (L)"
                        class="btn btn-sm btn-info fas fa-sort-numeric-down"
                        autocomplete="off"></button>
                <button id="be-toggle-line-mode"
                        title="Toggle line masks and stroke width. (M)"
                        class="btn btn-sm btn-info fas fa-mask"></button>
            </div>
            <div class="btn-group">
                <button id="be-split-lines"
                        title="Cut through lines. (C)"
                        class="btn btn-sm btn-warning fas fa-cut"></button>
            </div>

            <button v-if="!$store.getters['lines/hasMasks'] && $store.state.lines.all.length > 0"
                    @click="processLines"
                    class="btn btn-sm btn-success fas fa-thumbs-up ml-auto"
                    title="Segmentation is ready for mask calculation!">
            </button>
            <button id="segmentation-help-ben"
                    data-toggle="collapse"
                    data-target="#segmentation-help"
                    title="Help."
                    class="btn btn-sm btn-info fas fa-question help nav-item ml-2">
            </button>
            <div id="segmentation-help" class="alert alert-primary help-text collapse">
                <button type="button" class="close" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
                <help></help>
            </div>
        </div>

        <div id="context-menu">
            <button id="be-link-region"
                    title="Link selected lines to (the first detected) background region. (Y)"
                    class="hide btn btn-info m-1 fas fa-link"></button>
            <button id="be-unlink-region"
                    title="Unlink selected lines from their region. (U)"
                    class="hide btn btn-info m-1 fas fa-unlink"></button>
            <button id="be-merge-selection"
                    title="Join selected lines. (J)"
                    class="hide btn btn-info fas m-1 fa-compress-arrows-alt"></button>
            <button id="be-reverse-selection"
                    title="Reverse selected lines. (I)"
                    class="hide btn btn-info fas m-1 fa-arrows-alt-h"></button>
            <button id="be-set-type"
                    title="Set the type on all selected lines/regions. (T)"
                    class="btn m-1 btn-info fas fa-text-height"></button>
            <button id="be-delete-point"
                    title="Delete selected points. (ctrl+suppr)"
                    class="hide btn btn-warning m-1 fas fa-trash"></button>
            <button id="be-delete-selection"
                    title="Delete all selected lines/regions. (suppr)"
                    class="btn m-1 btn-danger fas fa-trash"></button>
        </div>

        <div id="info-tooltip"></div>

        <div class="content-container">
            <div id="seg-zoom-container" ref="segZoomContainer" class="content">
                <div id="seg-data-binding" v-if="loaded">
                    <segregion v-for="region in $store.state.regions.all"
                                v-bind:region="region"
                                v-bind:key="'sR' + region.pk">
                    </segregion>
                    <segline v-for="line in $store.state.lines.all"
                                v-bind:line="line"
                                v-bind:key="'sL' + line.pk">
                    </segline>
                </div>

                <img class="panel-img" ref="img"/>
                <!-- TODO: make line overlay component -->
                <div id="segmentation-overlay" class="overlay panel-overlay">
                    <svg width="100%" height="100%">
                        <defs>
                            <mask id="seg-overlay">
                                <rect x="0" y="0" width="100%" height="100%" fill="white"/>
                                <polygon points=""/>
                            </mask>
                        </defs>
                        <rect x="0" y="0" fill="grey" opacity="0.5" width="100%" height="100%" mask="url(#seg-overlay)" />
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
import { BasePanel } from '../../src/editor/mixins.js';
import SegRegion from "./SegRegion.vue";
import SegLine from "./SegLine.vue";
import Help from "./Help.vue";
import { Segmenter } from "../../src/baseline.editor.js";

export default Vue.extend({
  mixins: [BasePanel],
  props: ["fullsizeimage"],
  data() {
    return {
      segmenter: { loaded: false },
      imgloaded: false,
      colorMode: "color", //  color - binary - grayscale
      undoManager: new UndoManager(),
    };
  },
  components: {
    segline: SegLine,
    segregion: SegRegion,
    help: Help,
  },
  mounted() {
    // wait for the element to be rendered
    Vue.nextTick(
      function () {
        this.$parent.zoom.register(
          this.$refs.segZoomContainer,
          { map: true }
        );
        let beSettings =
          userProfile.get("baseline-editor-" + this.$store.state.document.id) || {};
        this.$img = this.$refs.img;

        this.segmenter = new Segmenter(this.$img, {
          delayInit: true,
          idField: "pk",
          defaultTextDirection: this.$store.state.document.mainTextDirection.slice(-2),
          regionTypes: this.$store.state.document.types.regions.map((t) => t.name),
          lineTypes: this.$store.state.document.types.lines.map((t) => t.name),
          baselinesColor: beSettings["color-baselines"] || null,
          regionColors: beSettings["color-regions"] || null,
          directionHintColors: beSettings["color-directions"] || null,
        });
        // we need to move the baseline editor canvas up one tag so that it doesn't get caught by wheelzoom.
        let canvas = this.segmenter.canvas;
        canvas.parentNode.parentNode.appendChild(canvas);

        // already mounted with a part = opening the panel after page load
        if (this.$store.state.parts.loaded) {
          this.initSegmenter();
        }

        // simulates wheelzoom for canvas
        var zoom = this.$parent.zoom;
        zoom.events.addEventListener(
          "wheelzoom.updated",
          function (e) {
            this.updateZoom();
          }.bind(this)
        );

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
  computed: {
    hasBinaryColor() {
      return this.$store.state.parts.loaded && this.$store.state.parts.bw_image !== null;
    },
    loaded() {
      // for this panel we need both the image and the segmenter
      return this.segmenter && this.segmenter.loaded && this.$img.complete;
    },
    imageSrc() {
      // empty the src to make sure the complete event gets fired
      // this.$img.src = '';
      if (!this.$store.state.parts.loaded) return "";
      // overrides imageSrc to deal with color modes
      // Note: vue.js doesn't have super call wtf we need to copy the code :(
      let src =
        (!this.fullsizeimage && this.$store.state.parts.image.thumbnails.large) ||
        this.$store.state.parts.image.uri;

      let bwSrc =
        (this.colorMode == "binary" &&
          this.$store.state.parts.bw_image &&
          this.$store.state.parts.bw_image.uri) ||
        src;

      return bwSrc;
    },
  },
  watch: {
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
          this.$img.src = src;
          this.refreshSegmenter();
        }.bind(this)
      );
    },
    fullsizeimage: function (n, o) {
      // it was prefetched
      if (n && n != o) {
        this.$img.src = this.imageSrc;
        this.segmenter.scale = 1;
        this.segmenter.refresh();
      }
    },
    '$store.state.document.blockShortcuts': function(n, o) {
      // make sure the segmenter doesnt trigger keyboard shortcuts either
      this.segmenter.disableShortcuts = n;
    }
  },
  methods: {
    toggleBinary(ev) {
      if (this.colorMode == "color") this.colorMode = "binary";
      else this.colorMode = "color";
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
          this.$img.src = src;
          this.refreshSegmenter();
        }.bind(this)
      );
    },
    refreshSegmenter() {
      Vue.nextTick(
        function () {
          this.segmenter.scale =
            this.$img.naturalWidth / this.$store.state.parts.image.size[0];
          if (this.segmenter.loaded) {
            this.segmenter.refresh();
          } else {
            this.segmenter.init();
          }
        }.bind(this)
      );
    },
    updateZoom() {
      // might not be mounted yet
      if (this.segmenter && this.$img.complete) {
        var zoom = this.$parent.zoom;
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
      if (this.segmenter.loaded && this.$store.state.document.visible_panels.segmentation) {
        this.segmenter.refresh();
      }
    },
    // undo manager helpers
    async bulkCreate(data, createInEditor) {
      if (data.regions && data.regions.length) {
        // note: regions dont get a bulk_create
        for (let i = 0; i < data.regions.length; i++) {
          try {
            const newRegion = await this.$store.dispatch('regions/create',
              {
                pk: data.regions[i].id,
                box: data.regions[i].box,
                type: data.regions[i].type,
              }
            );
            if (createInEditor) {
              this.segmenter.loadRegion(newRegion);
            }
            // also update pk in the original data for undo/redo
            data.regions[i].context.pk = newRegion.pk;
            this.$store.commit('regions/load', newRegion.pk);
          } catch (err) {
            console.log('couldnt create region', err);
          }
        }
      }
      if (data.lines && data.lines.length) {
        try {
          const newLines = await this.$store.dispatch('lines/bulkCreate', {
            lines: data.lines.map((l) => {
              return {
                pk: l.pk,
                baseline: l.baseline,
                mask: l.mask,
                region: (l.region && l.region.context.pk) || null,
              };
            }),
            transcription: this.$store.state.transcriptions.selectedTranscription
          })
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
            this.$store.commit('lines/load', line.pk);
          }
        } catch (err) {
          console.log('couldnt create lines', err)
        }
      }
    },
    async bulkUpdate(data) {
      if (data.regions && data.regions.length) {
        for (let i = 0; i < data.regions.length; i++) {
          try {
            let region = data.regions[i];
            const updatedRegion = await this.$store.dispatch('regions/update',
              {
                pk: region.context.pk,
                box: region.box,
                type: region.type,
              }
            );
            let segmenterRegion = this.segmenter.regions.find(
              (r) => r.context.pk == updatedRegion.pk
            );
            segmenterRegion.update(updatedRegion.box);
          } catch (err) {
            console.log('couldnt update region', err);
          }
        }
      }
      if (data.lines && data.lines.length) {
        try {
          const updatedLines = await this.$store.dispatch('lines/bulkUpdate', data.lines.map((l) => {
            return {
              pk: l.context.pk,
              baseline: l.baseline,
              mask: l.mask,
              region: l.region && l.region.context.pk,
              type: l.type,
            };
          }));
          for (let i = 0; i < updatedLines.length; i++) {
            let line = updatedLines[i];
            let region =
              this.segmenter.regions.find(
                (r) => r.context.pk == line.region
              ) || null;
            let segmenterLine = this.segmenter.lines.find(
              (l) => l.context.pk == line.pk
            );
            segmenterLine.update(
              line.baseline,
              line.mask,
              region,
              line.order
            );
          }
        } catch (err) {
          console.log('couldnt update line', err);
        }
      }
    },
    async bulkDelete(data) {
      if (data.regions && data.regions.length) {
        // regions have a bulk delete
        for (let i = 0; i < data.regions.length; i++) {
          try {
            await this.$store.dispatch('regions/delete', data.regions[i].context.pk);
            let region = this.segmenter.regions.find(
              (r) => r.context.pk == data.regions[i].context.pk
            );
            if (region) region.remove();
          } catch (err) {
            console.log('couldnt delete region #', data.regions[i].context.pk, err);
          }
        }
      }
      if (data.lines && data.lines.length) {
        try {
          const deletedLines = await this.$store.dispatch('lines/bulkDelete', data.lines.map((l) => l.context.pk));
          this.segmenter.lines
            .filter((l) => {
              return deletedLines.indexOf(l.context.pk) >= 0;
            })
            .forEach((l) => {
              l.remove();
            });
        } catch (err) {
          console.log('couldnt bulk delete lines', err);
        }
      }
    },

    extractPrevious(data) {
      // given modifications on lines/regions,
      // update data with a previous attribute containing the current state
      if (data.regions && data.regions.length) {
        data.regions.forEach(
          function (r) {
            let region = this.$store.state.regions.all.find((e) => e.pk == r.context.pk);
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
            let line = this.$store.state.lines.all.find((e) => e.pk == l.context.pk);
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
      await this.$store.dispatch('lines/recalculateMasks');
    },

    /* History */
    undo() {
      this.undoManager.undo();
      this.refreshHistoryBtns();
    },
    redo() {
      this.undoManager.redo();
      this.refreshHistoryBtns();
    },
    refreshHistoryBtns() {
      if (this.undoManager.hasUndo())
        this.$refs.undo.disabled = false;
      else this.$refs.undo.disabled = true;
      if (this.undoManager.hasRedo())
        this.$refs.redo.disabled = false;
      else this.$refs.redo.disabled = true;
    },
  },
});
</script>

<style scoped>
</style>
