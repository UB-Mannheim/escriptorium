import "jquery-ui-dist/jquery-ui.min.js";
import "jquery-ui-dist/jquery-ui.min.css";
import "popper.js";
import "bootstrap";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/css/bootstrap-reboot.min.css";
import "dropzone/dist/min/basic.min.css";
import "dropzone/dist/min/dropzone.min.css";
// import '@recogito/annotorious/dist/annotorious.min.css';
import "lodash";
import "@fortawesome/fontawesome-free/css/all.min.css";
import "moment-timezone/builds/moment-timezone-with-data-10-year-range.min.js";
import "@teklia/virtual-keyboard/dist-lib/content.js";
import "bootstrap-select/dist/css/bootstrap-select.css";

// JQuery needs to be explicitly set on window, as it's used at boot time
// by various scripts
window.jQuery = window.$ = require("jquery");

// Dropzone needs to be explicitly set on window, as it's modified at boot time
// by image-cards.js
// window.Dropzone = require('dropzone/dist/dropzone');
import Dropzone from "dropzone";
window.Dropzone = Dropzone;

// moment needs to be explicitly set on window, as it's used at boot time
// by trans_modal.js
window.moment = require("moment/moment");

// Paper needs to be explicitly set on window, as it's used at boot time
// by baseline.editor.js
window.paper = require("paper");

// Undo-manager needs to be explicitly set on window, as it's used at boot time
// by seg_panel.js
window.UndoManager = require("undo-manager");

// Sortable needs to be explicitly set on window, as it's used at boot time
// by diplo_panel.js
window.Sortable = require("sortablejs/Sortable");

// ReconnectingWebSocket needs to be explicitly set on window, as it's used at boot time
// by messages.js
window.ReconnectingWebSocket = require("reconnectingwebsocket");

// Js-cookie needs to be explicitly set on window, as it's used at boot time
// by ajax.js
window.Cookies = require("js-cookie");

// Diff needs to be explicitly set on window, as it's used at boot time
// by various scripts
window.Diff = require("diff");

// Mathjs needs to be explicitly set on window, as it's used at boot time
// by baseline.editor.js
window.math = require("mathjs/dist/math.min");

//Bootstrap select
window.BootstrapSelect = require("bootstrap-select/dist/js/bootstrap-select");
