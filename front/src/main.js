import "../css/escriptorium.css";
import "../css/rtl.css";
import "../css/ttb.css";
import "@recogito/annotorious/dist/annotorious.min.css";
import "@recogito/recogito-js/dist/recogito.min.css";
import "./ajax.js";
import { Alert, bootWebsocket, joinDocumentRoom } from "./messages.js";
window.Alert = Alert;
window.bootWebsocket = bootWebsocket;
window.joinDocumentRoom = joinDocumentRoom;

import { bootHelp } from "./help.js";
window.bootHelp = bootHelp;

import { bootLazyload, addImageToLoader } from "./lazyload.js";
window.bootLazyload = bootLazyload;
window.addImageToLoader = addImageToLoader;

import { WheelZoom } from "./wheelzoom.js";
window.WheelZoom = WheelZoom;

import { userProfile } from "./profile.js";
window.userProfile = userProfile;

import { setupFormSet } from "./formsets.js";
window.setupFormSet = setupFormSet;

import { bootDocumentForm } from "./document_form.js";
window.bootDocumentForm = bootDocumentForm;

import { bootOntologyForm } from "./ontology_form.js";
window.bootOntologyForm = bootOntologyForm;

import { bootImageCards } from "./image_cards.js";
window.bootImageCards = bootImageCards;

import { bootModels } from "./models.js";
window.bootModels = bootModels;

import { bootAlignForm } from "./align_form.js";
window.bootAlignForm = bootAlignForm;
