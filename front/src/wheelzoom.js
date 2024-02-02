/*
 * Usage:
 * var zoom = new WheelZoom(domElement)
 * zoom.register(container);
 */

"use strict";

class zoomTarget {
    constructor(
        domElement,
        {
            map = false,
            mapScale = 0.2,
            mapColors = ["grey", "white"],
            mapMargin = 10,
            mapDuration = 2,
        },
    ) {
        // wrap the element in a container:
        var container = document.createElement("div");
        container.classList.add("js-wheelzoom-container");
        // disables right click menu
        container.addEventListener("contextmenu", function (e) {
            e.preventDefault();
        });
        // var rotationContainer = document.createElement('div');
        domElement.parentNode.insertBefore(container, domElement);
        container.appendChild(domElement);
        // rotationContainer.appendChild(domElement);
        // container.appendChild(rotationContainer);
        // rotationContainer.style.transformOrigin = 'center';
        container.style.position = "relative";
        container.style.overflow = "hidden";
        // container.style.width = '100%';
        // container.style.height = '100%';
        domElement.style.transformOrigin = "0 0";
        domElement.style.transition = "scale 0.3s";
        // domElement.style.display = 'block';
        domElement.classList.add("js-zoom-target");
        this.container = container;
        //this.rotationContainer = rotationContainer;
        this.element = domElement;

        this.map = map;
        if (this.map) {
            this.mapScale = mapScale;
            this.mapDuration = mapDuration;
            this.mapTimer = null;
            this.mapMargin = mapMargin;
            this.makeMap(mapMargin, mapColors);
            this.refreshMap();
        }
    }

    update(pos, scale) {
        this.element.style.transform =
            "translate(" +
            pos.x +
            "px," +
            pos.y +
            "px) " +
            "scale(" +
            scale +
            ")";
    }

    showMap(pos, scale) {
        if (this.map && scale > 1) {
            this.refreshMap();
            this.mapWhole.style.opacity = 0.7;
            this.mapCurrent.textContent = Math.round(scale * 100) + "%";
            this.mapCurrent.style.transform =
                "" +
                "translate(" +
                (-pos.x * this.mapScale) / scale +
                "px," +
                (-pos.y * this.mapScale) / scale +
                "px) " +
                "scale(" +
                1 / scale +
                ")";

            // fadeOut
            if (this.mapTimer) clearInterval(this.mapTimer);
            let nTicks = (this.mapDuration * 1000) / 100;
            let factor = this.mapWhole.style.opacity / nTicks;
            this.mapTimer = setInterval(
                function () {
                    if (this.mapWhole.style.opacity <= 0) {
                        clearInterval(this.mapTimer);
                    }
                    this.mapWhole.style.opacity =
                        this.mapWhole.style.opacity - factor;
                }.bind(this),
                100,
            );
        }
    }

    refreshMap() {
        if (this.map) {
            let bounds = this.container.getBoundingClientRect();
            this.mapWhole.style.top = bounds.y + this.mapMargin + "px";
            this.mapWhole.style.left = bounds.x + this.mapMargin + "px";
            this.mapWhole.style.width = bounds.width * this.mapScale + "px";
            this.mapWhole.style.height = bounds.height * this.mapScale + "px";
        }
    }

    makeMap(mapMargin, mapColors) {
        this.mapWhole = document.createElement("div");
        this.mapWhole.classList.add("wheelzoom-outter-map");
        this.mapWhole.style.position = "fixed";
        this.mapWhole.style.opacity = 0;
        this.mapWhole.style.backgroundColor = mapColors[0];
        this.mapWhole.style.pointerEvents = "none";
        this.container.appendChild(this.mapWhole);

        this.mapCurrent = document.createElement("div");
        this.mapCurrent.classList.add("wheelzoom-inner-map");
        this.mapCurrent.style.position = "absolute";
        this.mapCurrent.style.opacity = 0.5;
        this.mapCurrent.style.width = "100%";
        this.mapCurrent.style.height = "100%";
        this.mapCurrent.style.backgroundColor = mapColors[1];
        this.mapCurrent.style.transformOrigin = "0 0";
        this.mapWhole.appendChild(this.mapCurrent);
    }
}

export class WheelZoom {
    constructor({
        factor = 0.1,
        minScale = 0.2,
        maxScale = 10,
        initialScale = 1,
        disabled = false,
        legacyModeEnabled = true,
        getActiveTool = () => {},
    } = {}) {
        this.factor = factor;
        this.minScale = minScale;
        this.maxScale = maxScale;
        this.initialScale = initialScale;
        this.disabled = disabled;
        this.legacyModeEnabled = legacyModeEnabled;
        this.getActiveTool = getActiveTool;

        // create a dummy tag for event bindings
        this.events = document.createElement("div");
        this.events.classList.add("wheelzoom-events-js");
        document.body.appendChild(this.events);

        this.targets = [];
        this.previousEvent = null;
        this.scale = this.initialScale;
        this.angle = 0;
        this.pos = { x: 0, y: 0 };
    }

    register(domElement, { mirror = false, map = false } = {}) {
        this.events.addEventListener("wheelzoom.reset", this.reset.bind(this));
        this.events.addEventListener(
            "wheelzoom.refresh",
            this.refresh.bind(this),
        );

        let target = new zoomTarget(domElement, { map: map });
        target.update(this.pos, this.scale);
        this.targets.push(target);
        if (!mirror) {
            // domElement.style.cursor = 'zoom-in';

            const scroll = function (event) {
                // looks like it breaks on some configurations?
                // if (event.altKey) return;  // supposed to move in history
                // if (event.ctrlKey) return;  // browser zoom
                this.scrolling = target;
                this.scrolled.bind(this)(event);
            }
            const drag = function (event) {
                // in case of mask over the element, bc we bind to document so event.target can be whatever
                if (
                    (this.legacyModeEnabled || this.getActiveTool() !== "pan") &&
                    !(event.which === 3 || event.button === 2)
                ) {
                    return; // right click only
                }
                this.dragging = target;
                this.draggable.bind(this)(event);
            }

            target.container.addEventListener("mousewheel", scroll.bind(this));
            target.container.addEventListener(
                "DOMMouseScroll",
                scroll.bind(this),
            ); // firefox
            target.container.addEventListener("mousedown", drag.bind(this));
        } else {
            target.container.classList.add("mirror");
        }
        return target;
    }

    zoomTo(target, delta) {
        var oldScale = this.scale;
        this.scale *= Math.exp(delta);
        if (this.minScale !== null)
            this.scale = Math.max(this.minScale, this.scale);
        if (this.maxScale !== null)
            this.scale = Math.min(this.maxScale, this.scale);

        var diff = { scale: this.scale / oldScale };
        this.pos.x -= Math.round(
            (target.x - target.x / diff.scale) * diff.scale,
        );
        this.pos.y -= Math.round(
            (target.y - target.y / diff.scale) * diff.scale,
        );

        this.updateStyle(diff);
        for (let itarget of this.targets) {
            itarget.showMap(this.pos, this.scale);
        }
        return diff;
    }

    zoomIn() {
        var tr = this.targets[0].element.getBoundingClientRect();
        var target = {
            x: tr.width / 2 - this.pos.x,
            y: tr.height / 2 - this.pos.y,
        };
        this.zoomTo(target, 0.1);
    }

    zoomOut() {
        var tr = this.targets[0].element.getBoundingClientRect();
        var target = {
            x: tr.width / 2 - this.pos.x,
            y: tr.height / 2 - this.pos.y,
        };
        this.zoomTo(target, -0.1);
    }

    scrolled(e) {
        if (this.disabled) return null;
        e.preventDefault();

        var delta = e.delta || e.wheelDelta;
        if (delta === undefined) {
            //we are on firefox
            delta = -e.detail;
        }
        // cap the delta to [-1,1] for cross browser consistency
        delta = Math.max(-1, Math.min(1, delta));
        // determine the point on where the slide is zoomed in
        let bounds = e.target.getBoundingClientRect();
        var zoom_point = {
            x: e.pageX - bounds.x - document.documentElement.scrollLeft,
            y: e.pageY - bounds.y - document.documentElement.scrollTop,
        };

        return this.zoomTo(zoom_point, delta * this.factor);
    }

    drag(e) {
        if (this.disabled) return null;
        e.preventDefault();
        var target = this.dragging;
        if (!target) return null;
        var ts = target.container.getBoundingClientRect();
        var ter = target.element.getBoundingClientRect();
        var delta,
            oldPos = { x: this.pos.x, y: this.pos.y },
            oldAngle = this.angle;

        if (this.previousEvent) {
            if (e.altKey) {
                this.angle =
                    (this.angle + (e.pageX - this.previousEvent.pageX)) % 360;
            } else {
                this.pos.x += e.pageX - this.previousEvent.pageX;
                this.pos.y += e.pageY - this.previousEvent.pageY;
            }
        }
        // Make sure the slide stays in its container area when zooming in/out
        if (this.legacyModeEnabled) {
            // disabled on new UI. there's a reset zoom button for this!
            if (ter.width * this.scale > ts.width) {
                if (this.pos.x > 0) {
                    this.pos.x = 0;
                }
                if (this.pos.x + ter.width < ts.width) {
                    this.pos.x = ts.width - ter.width;
                }
            } else {
                if (this.pos.x < 0) {
                    this.pos.x = 0;
                }
                if (this.pos.x + ter.width > ts.width) {
                    this.pos.x = ts.width - ter.width;
                }
            }
            if (ter.height * this.scale > ts.height) {
                if (this.pos.y > 0) {
                    this.pos.y = 0;
                }
                if (this.pos.y + ter.height < ts.height) {
                    this.pos.y = ts.height - ter.height;
                }
            } else {
                if (this.pos.y < 0) {
                    this.pos.y = 0;
                }
                if (this.pos.y + ter.height > ts.height) {
                    this.pos.y = ts.height - ter.height;
                }
            }
        }
        this.previousEvent = e;
        let diff = {
            x: (this.pos.x - oldPos.x) / this.scale,
            y: (this.pos.y - oldPos.y) / this.scale,
            angle: this.angle - oldAngle,
        };
        this.updateStyle(diff);
        this.dragging.showMap(this.pos, this.scale);
        return diff;
    }

    removeDrag() {
        // this.targets.forEach(function(target,i) {
        //     target.element.classList.remove('notransition');
        // });

        document.removeEventListener("mouseup", this.bRemDrag);
        document.removeEventListener("mousemove", this.bDrag);
        this.previousEvent = null;
    }

    draggable(event) {
        if (this.disabled) return;
        event.preventDefault();
        this.previousEvent = event;
        // this.rotationOrigin = e.point;

        // set bound event handlers
        this.bDrag = this.drag.bind(this);
        this.bRemDrag = this.removeDrag.bind(this);
        document.addEventListener("mousemove", this.bDrag);
        document.addEventListener("mouseup", this.bRemDrag);
    }

    updateStyle(delta) {
        this.targets.forEach(
            function (target, i) {
                target.update(this.pos, this.scale);
                // if (this.rotationOrigin) {
                //     target.rotationContainer.style.transformOrigin = this.rotationOrigin.x+'px '+this.rotationOrigin.y+'px';
                //     target.rotationContainer.style.transform = 'rotate('+this.angle+'deg)';
                // }
            }.bind(this),
        );
        var event = new CustomEvent("wheelzoom.updated", {
            detail: { delta: delta, pos: this.pos, scale: this.scale },
        });
        if (this.events) this.events.dispatchEvent(event);
    }

    refresh() {
        this.updateStyle();
    }

    reset() {
        var oldPos = { x: this.pos.x, y: this.pos.y },
            oldAngle = this.angle;
        this.pos = { x: 0, y: 0 };
        this.scale = this.initialScale || 1;
        this.updateStyle({ x: -oldPos.x, y: -oldPos.y, scale: 1 / oldAngle });
    }

    disable() {
        this.disabled = true;
    }

    enable() {
        this.disabled = false;
    }

    destroy() {
        // TODO
    }
}
