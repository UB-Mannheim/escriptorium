<template>
    <div>
        <p>
            <b>Left click</b> on the image to <u>create</u> new line, <b>Right click</b> to <b>add points</b> and <b>Left click</b> again to <u>finish</u> it.
            <br>You can keep the mouse button pressed for free drawing.
            <br>Hitting <b>escape</b> while drawing a line <u>cancels</u> it.
            <br>If regions matter to you switch to region mode first <i class="fas fa-th-large" /> (R key).
            <br>when in region mode <b>Left click</b> to create a new rectangular region, left click again to finish it.
            <br>lines drawn inside a region will automatically be bound to it.
            <br>When the quality of the segmentation is good, you can prompt the system to calculate masks <i class="text-success fas fa-thumbs-up" />,
            <br>once a page already has masks new lines will automatically get a mask and updating a line will also recalculate its mask.
            <br><b>Note</b> that the quality of the masks is highly dependent on the quality of the whole segmentation, not only the corresponding line,
            <br>so make sure to draw all the lines before calculating the masks.
            <br>You can also have the option to calculate the masks <i>en masse</i> in the Images tab -> segment -> choose 'Only masks'.
        </p>
        <p>
            <b>Left click</b> on a line to select it, then you can drag its closest control point.
            <br><b>Double click</b> on the line will create a <u>new control point</u> at the mouse location.
            <br>You can reverse the order of the line's points by selecting a line (or multiple) and using reverse <i class="fas fa-arrow-alt-h" /> (I key).
            <br>When in region mode, Regions can be edited the same way.
            <br>Selected lines can be linked or unlinked to regions with the corresponding buttons <i class="fas fa-link" />(Y key) <i class="fas fa-unlink"> (U key).</i>
            <br>By using the cut mode <i class="text-warning fas fa-cut" /> (C key) you can cut through lines, splitting them in two or removing part of them.
            <br>If at least two lines are selected an option to join them becomes available <i class="fas fa-compress-arrows-alt" /> (J key).
            <br>You can go through your changes <u>history</u> back and forth with <b>Ctrl+Z</b>(undo) and <b>Ctrl+Y</b>(redo) or by using the corresponding buttons <i class="fas fa-undo" /><i class="fas fa-redo" />.
        </p>
        <p>
            <b>Shift+click</b> allows to add or remove a line from the <u>selection</u>,
            <br>Clicking on an empty space clears the selection,
            <br><b>shift and drag</b> creates a <u>lasso</u> selection tool that allows to select control points (they then appear black).
            <br><b>Note:</b> If lines are already selected the lasso will only select points in those lines.
            <br><b>Ctrl+drag</b> allows to move all the selected control points at once (or the selected lines if no control points are selected).

            <br>The red trash <i class="text-danger fas fa-trash" /> button <b>deletes</b> all selected <b>lines/regions</b>,
            <br>The yellow trash button <i class="text-warning fas fa-trash" /> only <b>deletes</b> selected control <b>points</b>.
        </p>
    </div>
</template>

<script>
export default {}
</script>

<style scoped>
</style>
