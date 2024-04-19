<!-- eslint-disable vue/multiline-html-element-content-newline -->
<template>
    <li
        :data-order="line.order"
        :data-line-pk="line.pk"
        @mousemove="showOverlay"
        @mouseleave="hideOverlay"
    >
        <div
            v-if="sortMode"
            :class="{
                ['escr-line-dropzone-before']: true,
                ['is-dragging']: isDragging,
                ['drag-over']: dragOver === -1,
            }"
            @dragover="(e) => handleDragOver(e, -1)"
            @dragenter="(e) => e.preventDefault()"
            @dragleave="() => setDragOver(0)"
            @drop="(e) => handleDrop(e, -1)"
        />
        <span>{{ line.currentTrans.content }}</span>
        <div
            v-if="sortMode"
            draggable
            class="draggable-overlay"
            @click="selectLine"
            @dragend="handleDragEnd"
            @dragstart="handleDragStart"
        />
        <div
            v-if="sortMode"
            :class="{
                ['escr-line-dropzone-after']: true,
                ['is-dragging']: isDragging,
                ['drag-over']: dragOver === 1,
            }"
            @dragover="(e) => handleDragOver(e, 1)"
            @dragenter="(e) => e.preventDefault()"
            @dragleave="() => setDragOver(0)"
            @drop="(e) => handleDrop(e, 1)"
        />
    </li>
</template>

<script>
import { mapMutations, mapState } from "vuex";
import { LineBase } from "../../../src/editor/mixins.js";
import "./GroupedLine.css";

export default {
    mixins: [LineBase],
    props: {
        moveLines: {
            type: Function,
            required: true,
        },
        selectLine: {
            type: Function,
            required: true,
        },
        selectedLines: {
            type: Array,
            required: true,
        },
        sortMode: {
            type: Boolean,
            required: true,
        },
    },
    data() {
        return {
            dragOver: 0,
            isBeingDragged: false,
        }
    },
    computed: {
        ...mapState({
            allLines: (state) => state.lines.all,
            loading: (state) => state.lines.loading,
            isDragging: (state) => state.lines.isDragging,
        })
    },
    methods: {
        ...mapMutations("lines", ["setIsDragging"]),
        getEl() {
            return this.$el.querySelector(":scope > span");
        },
        /**
         * Tell this component that it is not being dragged; tell state that dragging has stopped
         */
        handleDragEnd() {
            this.isBeingDragged = false;
            // timeout hack to prevent z-fighting with drag handle
            setTimeout(() => {
                this.setIsDragging(false);
            }, 100);
        },
        /**
         * On drag, set this line's pk on the event data so that it can be retrieved on drop.
         */
        handleDragStart(e) {
            e.dataTransfer.setData("draggingPk", this.line.pk);
            // timeout hack to prevent z-fighting with drag handle
            setTimeout(() => {
                this.setIsDragging(true);
            }, 100);
        },
        /**
         * Set the component state to indicate whether the "after" drop zone is being dragged
         * over (1), the "before" drop zone is (-1), or neither is (0)
         */
        setDragOver(idx) {
            this.dragOver = idx;
        },
        /**
         * When one of this line's drop zones are dragged over, tell component whether it is
         * before (-1) or after (1) this line; also, set the drop effect on the event
         */
        handleDragOver(e, idx) {
            e.preventDefault();
            this.setDragOver(idx);
            e.dataTransfer.dropEffect = "move";
        },
        /**
         * On drop, perform the reordering operation, then turn off all drag-related
         * component and store states.
         */
        async handleDrop(e, idx) {
            // pk of the line being dragged
            const draggingPk = parseInt(e.dataTransfer.getData("draggingPk"));
            // set up things to be reassigned if move conditions are met
            let selection = [];
            let filterCondition = () => {};
            let shouldMove = false;
            if (
                this.selectedLines.includes(draggingPk) &&  // dragging a selected line
                !this.selectedLines.includes(this.line.pk) // not dropping within the selected lines
            ) {
                // move all selected
                selection = this.selectedLines;
                filterCondition = (line) => !this.selectedLines.includes(line.pk);
                shouldMove = true;
            } else if (
                !this.selectedLines.includes(draggingPk) && // not dragging a selected line
                this.line.pk !== draggingPk // not dropping unselected line onto itself
            ) {
                // move one
                selection = [draggingPk];
                filterCondition = (line) => line.pk !== draggingPk;
                shouldMove = true;
            }
            // generic move operation: splice line(s) into the correct position and recalculate ordering
            if (shouldMove) {
                const insertBefore = idx === -1;
                let newPos = -1;
                // get order of all lines without the ones to move
                let reorderedLines = this.allLines
                    .filter(filterCondition)
                    .toSorted((a, b) => a.order - b.order)
                    .map((line, pos) => {
                        // store the new position based on line where selection was dropped
                        if (line.pk === this.line.pk) {
                            newPos = pos;
                        }
                        return line.pk;
                    });
                // splice the selected lines back in at the new position
                reorderedLines.splice(insertBefore ? newPos : newPos + 1, 0, ...selection);
                // reorder starting from 0
                const toMove = reorderedLines.map((pk, order) => ({ pk, order }));
                await this.moveLines(toMove);
            }
            // reset states
            this.isBeingDragged = false;
            this.dragOver = 0;
            // timeout hack to prevent z-fighting with drag handle
            setTimeout(() => {
                this.setIsDragging(false);
            }, 100);
        }
    }
}
</script>
