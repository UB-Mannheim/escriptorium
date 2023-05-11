import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import DocumentDashboard from "../../vue/pages/Document/Document.vue";
import {
    annotationTypes,
    blockTypes,
    blockTypesRandomized,
    characters,
    charactersRandomized,
    groups,
    lineTypes,
    partTypes,
    scripts,
    sorted,
    tags,
    transcriptions,
    users,
} from "./util";

export default {
    title: "Pages/Document Dashboard",
    component: DocumentDashboard,
};

const doc = {
    line_offset: 0,
    main_script: "Arabic",
    name: "Document Name",
    parts_count: 32,
    project: {
        id: 1,
        name: "Project name that is really really long",
    },
    read_direction: "rtl",
    shared_with_groups: groups,
    shared_with_users: users,
    tags,
    transcriptions,
    updated_at: "2023-03-17T13:54:15.352146Z",
};
const parts = [
    {
        title: "Element 2 - name_of_image.jpg",
        image: {
            thumbnails: {
                card:
                    // eslint-disable-next-line max-len
                    "http://localhost:8000/media/documents/11/exampldpdf_gpZmcsU.pdf_page_2.png.180x180_q85_crop-smart.png",
            },
        },
        updated_at: "2023-03-17T13:46:38.076375Z",
    },
    {
        title: "Element 1 - name_of_image.jpg",
        image: {
            thumbnails: {
                card:
                    // eslint-disable-next-line max-len
                    "http://localhost:8000/media/documents/11/exampldpdf_gpZmcsU.pdf_page_1.png.180x180_q85_crop-smart.png",
            },
        },
        updated_at: "2022-07-08T13:40:30.810030Z",
    },
    {
        title: "Element 3 - name_of_image.jpg",
        image: {
            thumbnails: {
                card:
                    // eslint-disable-next-line max-len
                    "http://localhost:8000/media/documents/11/exampldpdf_gpZmcsU.pdf_page_3.png.180x180_q85_crop-smart.png",
            },
        },
        updated_at: "2022-07-08T13:40:37.484940Z",
    },
    {
        title: "Element 4 - name_of_image.jpg",
        image: {
            thumbnails: {
                card:
                    // eslint-disable-next-line max-len
                    "http://localhost:8000/media/documents/11/exampldpdf_gpZmcsU.pdf_page_4.png.180x180_q85_crop-smart.png",
            },
        },
        updated_at: "2022-07-08T13:40:40.970483Z",
    },
];

const newPk = Math.max(...tags.map((tag) => tag.pk)) + 1;
const newDocumentTagPks = [newPk];

const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { DocumentDashboard },
    template: '<DocumentDashboard v-bind="$props" />',
    setup() {
        // setup mocks for API requests
        const mock = new MockAdapter(axios);
        const documentEndpoint = new RegExp(/\/documents\/\d+$/);
        const documentTagsEndpoint = new RegExp(/\/projects\/\d+\/tags$/);
        const scriptsEndpoint = "/scripts";
        const partsEndpoint = new RegExp(/\/documents\/\d+\/parts$/);
        const blockEndpointA = new RegExp(
            /\/documents\/\d+\/transcriptions\/1\/types\/block$/,
        );
        const blockEndpointB = new RegExp(
            /\/documents\/\d+\/transcriptions\/2\/types\/block$/,
        );
        const lineEndpoint = new RegExp(
            /\/documents\/\d+\/transcriptions\/\d+\/types\/line$/,
        );
        const annotationsEndpoint = new RegExp(
            /\/documents\/\d+\/transcriptions\/\d+\/types\/annotations$/,
        );
        const partEndpoint = new RegExp(
            /\/documents\/\d+\/transcriptions\/\d+\/types\/part$/,
        );
        const charactersEndpointA = new RegExp(
            /\/documents\/\d+\/transcriptions\/1\/characters$/,
        );
        const charactersEndpointB = new RegExp(
            /\/documents\/\d+\/transcriptions\/2\/characters$/,
        );
        const charCountA = new RegExp(
            /\/documents\/\d+\/transcriptions\/1\/character_count$/,
        );
        const charCountB = new RegExp(
            /\/documents\/\d+\/transcriptions\/2\/character_count$/,
        );
        // mock document response
        mock.onGet(documentEndpoint).reply(async function() {
            // wait for 100-300 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, doc];
        });
        // mock ontology
        mock.onGet(blockEndpointA).reply(async function(config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [200, { results: sorted(blockTypes, { ordering }) }];
            }
            return [200, { results: blockTypes }];
        });
        mock.onGet(blockEndpointB).reply(async function(config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [
                    200,
                    { results: sorted(blockTypesRandomized, { ordering }) },
                ];
            }
            return [200, { results: blockTypesRandomized }];
        });
        mock.onGet(lineEndpoint).reply(async function(config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [200, { results: sorted(lineTypes, { ordering }) }];
            }
            return [200, { results: lineTypes }];
        });
        mock.onGet(annotationsEndpoint).reply(async function(config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [
                    200,
                    { results: sorted(annotationTypes, { ordering }) },
                ];
            }
            return [200, { results: annotationTypes }];
        });
        mock.onGet(partEndpoint).reply(async function(config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [200, { results: sorted(partTypes, { ordering }) }];
            }
            return [200, { results: partTypes }];
        });
        mock.onGet(charactersEndpointA).reply(async function(config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [200, { results: sorted(characters, { ordering }) }];
            }
            return [200, { results: characters }];
        });
        mock.onGet(charactersEndpointB).reply(async function(config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [
                    200,
                    { results: sorted(charactersRandomized, { ordering }) },
                ];
            }
            return [200, { results: charactersRandomized }];
        });
        mock.onGet(charCountA).reply(async function() {
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { count: 128000 }];
        });
        mock.onGet(charCountB).reply(async function() {
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { count: 1729 }];
        });
        mock.onGet(partsEndpoint).reply(async function() {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { results: parts }];
        });
        // mock scripts
        mock.onGet(scriptsEndpoint).reply(async function() {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [
                200,
                { results: scripts.map((script) => ({ name: script })) },
            ];
        });
        // mock document tags
        mock.onGet(documentTagsEndpoint).reply(async function() {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { results: tags }];
        });
        // mock edit document
        mock.onPut(documentEndpoint).reply(async function(config) {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            if (config?.data) {
                // mock return updated document
                const { params } = JSON.parse(config.data);
                const {
                    name,
                    project,
                    main_script,
                    read_direction,
                    line_offset,
                    tags,
                } = params;
                return [
                    200,
                    {
                        ...doc,
                        name,
                        project,
                        main_script,
                        read_direction,
                        line_offset,
                        tags,
                    },
                ];
            }
            return [500];
        });

        // mock create document tag
        mock.onPost(documentTagsEndpoint).reply(async function(config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (config?.data) {
                // mock creating a new tag with increment pk
                const { params } = JSON.parse(config.data);
                const { name, color } = params;
                const newTag = Math.max(...newDocumentTagPks) + 1;
                newDocumentTagPks.push(newTag);
                return [200, { name, color, pk: newTag }];
            }
            return [500];
        });

        // mock delete document (throw an error for test environment)
        mock.onDelete(documentEndpoint).reply(async function() {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [
                400,
                {
                    message:
                        "This is just a test environment, so you cannot delete a document.",
                },
            ];
        });
    },
});

export const DocumentDashboardPage = Template.bind({});
DocumentDashboardPage.parameters = {
    layout: "fullscreen",
};
DocumentDashboardPage.args = {
    id: 1,
};
