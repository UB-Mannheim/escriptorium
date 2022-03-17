<template>
    <g @mouseover="showOverlay"
        @mouseleave="hideOverlay"
        @click="edit">
        <polygon    v-bind:fill="$store.state.document.confidenceVisible ? maskFillColor : 'transparent'"
                    v-bind:stroke="maskStrokeColor"
                    v-bind:points="maskPoints"/>
        <path v-bind:id="textPathId"
                ref="pathElement"
                fill="none"
                v-bind:stroke="pathStrokeColor"
                v-bind:d="baselinePoints"></path>

        <text :text-anchor="$store.state.document.defaultTextDirection == 'rtl' ? 'end' : ''"
                ref="textElement"
                lengthAdjust="spacingAndGlyphs" 
                data-toggle="tooltip"
                v-if="$store.state.document.mainTextDirection != 'ttb'">
            <textPath v-bind:href="'#' + textPathId"
                        v-if="line.currentTrans">
                {{ line.currentTrans.content }}
            </textPath>
        </text>

        <text :text-anchor="$store.state.document.defaultTextDirection == 'rtl' ? 'end' : ''"
                ref="textElement"
                rotate="-90"
                font-size="1em"
                data-toggle="tooltip"
                v-else>
            <textPath v-bind:href="'#' + textPathId"
                        v-if="line.currentTrans">
                {{ line.currentTrans.content }}
            </textPath>
        </text>

    </g>
</template>

<script>
import { LineBase } from '../../src/editor/mixins.js';

export default Vue.extend({
    mixins: [LineBase],
    mounted() {
    },
    watch: {
        'line.currentTrans.content': function(n, o) {
            this.$nextTick(this.reset);
        },
        'line.baseline': function(n, o) {
            this.$nextTick(this.reset);
        }
    },
    methods: {
        computeLineHeight() {
            let lineHeight;
            if (this.line.mask) {
                let poly = this.line.mask.flat(1).map(pt => Math.round(pt));
                var area = 0;
                // A = 1/2(x_1y_2-x_2y_1+x_2y_3-x_3y_2+...+x_(n-1)y_n-x_ny_(n-1)+x_ny_1-x_1y_n),

                var liste = String(poly).split(",");
                var indexCoordonnee = 0;
                var arrayCoordonnees = new Array();
                var paire = [];
                for(var i = 0; i < liste.length; i++){
                    paire.push(liste[i]);
                    if(indexCoordonnee==0){
                        indexCoordonnee = 1;
                    }else{
                        indexCoordonnee = 0;
                        arrayCoordonnees.push(paire);
                        paire = new Array();
                    }
                }

                for (let i=0; i<arrayCoordonnees.length; i++) {
                    let j = (i+1) % arrayCoordonnees.length; // loop back to 1
                    area += arrayCoordonnees[i][0]*arrayCoordonnees[j][1] - arrayCoordonnees[j][0]*arrayCoordonnees[i][1];
                }

                area = Math.abs(area*this.ratio);
                lineHeight = area / this.$refs.pathElement.getTotalLength();

            } else {
                lineHeight = 30;
            }
 
            lineHeight = Math.max(Math.round(lineHeight), 5) * 0.3;

            let ratio = 1/4;    //  more well suited for horizontal latin writings
            if(this.$store.state.document.mainTextDirection == 'ttb')
                ratio = 1/2;

            this.$refs.textElement.setAttribute("font-size", String(lineHeight * (ratio)) + 'px'); 

            //return lineHeight+'px';
            return 10+'px';
        },
        computeTextLength() {
            if (!this.line.currentTrans) return;
            const content = this.line.currentTrans.content;
            if (content) {
                // adjust the text length to fit in the box
                let textLength = this.$refs.textElement.getComputedTextLength();
                let pathLength = this.$refs.pathElement.getTotalLength();
                if (textLength && pathLength) {
                    this.$refs.textElement.setAttribute('textLength', pathLength+'px');
                }
            }
        },
        computeConfidence() {
            // compute the average confidence for this line
            if (this.line.currentTrans?.graphs?.length) {
                const lineConfidences = this.line.currentTrans.graphs.map(g => g.confidence);
                const avgConfidence = lineConfidences.reduce((all, one, _, src) => all += one / src.length, 0);
                const confidence =  `Confidence: ${(avgConfidence * 100).toFixed(2)}%`;
                // add confidence to bootstrap title related attributes
                this.$refs.textElement.setAttribute('title' ,confidence);
                this.$refs.textElement.setAttribute('data-original-title', confidence);
            } else {
                // remove confidence from title attributes
                this.$refs.textElement.setAttribute('title', '');
                this.$refs.textElement.setAttribute('data-original-title', '');
            }
        },
        edit() {
            this.$store.dispatch('lines/toggleLineEdition', this.line);
        },
        reset() {
            this.computeLineHeight();
            this.computeTextLength();
            this.computeConfidence();
        },
    },
    computed: {
        textPathId() {
            return this.line ? 'textPath'+this.line.pk : '';
        },
        maskStrokeColor() {
            if (this.line.currentTrans && this.line.currentTrans.content) {
                return 'none';
            } else {
                return 'lightgrey';
            }
        },
        maskFillColor() {
            if (this.line.currentTrans?.graphs?.length) {
                // compute the average confidence for this line
                const lineConfidences = this.line.currentTrans.graphs.map(g => g.confidence);
                const avgConfidence = lineConfidences.reduce((all, one, _, src) => all += one / src.length, 0);
                // convert the avg confidence to hue (0 = red, 120 = green)
                // use a slight curve so that values are more easily red/yellow
                const hue = Math.pow(avgConfidence, 3) * 120;
                return `hsl(${hue}, 100%, 50%, 50%)`;
            }
            return 'transparent';
        },
        maskPoints() {
            if (this.line == null || !this.line.mask) return '';
            return this.line.mask.map(pt => Math.round(pt[0]*this.ratio)+','+Math.round(pt[1]*this.ratio)).join(' ');
        },
        fakeBaseline() {
            // create a fake path based on the mask,
            var min = this.line.mask.reduce((minPt, curPt) => (curPt[0] < minPt[0]) ? curPt : minPt);
            var max = this.line.mask.reduce((maxPt, curPt) => (curPt[0] > maxPt[0]) ? curPt : maxPt);
            return [min, max];
        },
        pathStrokeColor() {
            if (this.line.currentTrans && this.line.currentTrans.content) {
                return 'none';
            } else {
                return 'blue';
            }
        },
        baselinePoints() {
            var baseline, ratio = this.ratio;
            function ptToStr(pt) {
                return Math.round(pt[0]*ratio)+' '+Math.round(pt[1]*ratio);
            }
            if (this.line == null || this.line.baseline === null) {
                baseline = this.fakeBaseline;
            } else {
                baseline = this.line.baseline
            }
            return 'M '+baseline.map(pt => ptToStr(pt)).join(' L ');
        },
    }
});
</script>

<style scoped>
</style>
