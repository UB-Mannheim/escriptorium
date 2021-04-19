import '../css/escriptorium.css';
import '../css/rtl.css';
import '../css/ttb.css';
import './ajax.js';
import { Alert, bootWebsocket, joinDocumentRoom } from './messages.js';
window.Alert = Alert;
window.bootWebsocket = bootWebsocket;
window.joinDocumentRoom = joinDocumentRoom;

import { bootHelp } from './help.js';
window.bootHelp = bootHelp;

import { bootLazyload, addImageToLoader } from './lazyload.js';
window.bootLazyload = bootLazyload;
window.addImageToLoader = addImageToLoader;

import { WheelZoom } from './wheelzoom.js'
window.WheelZoom = WheelZoom;

import { userProfile } from './profile.js'
window.userProfile = userProfile;

import { bootOnboarding } from './onboarding.js';
window.bootOnboarding = bootOnboarding;

import { bootDocumentForm } from './document_form.js';
window.bootDocumentForm = bootDocumentForm;

import { bootImageCards } from './image_cards.js';
window.bootImageCards = bootImageCards;

import { bootModels } from './models.js';
window.bootModels = bootModels;
