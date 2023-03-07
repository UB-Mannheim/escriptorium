import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import ProjectDashboard from "../../vue/pages/Project/Project.vue";
import {
    annotationTypes,
    blockTypes,
    lineTypes,
    partTypes,
    sorted,
} from "./util";

export default {
    title: "Pages/Project Dashboard",
    component: ProjectDashboard,
};

const project = {
    id: 1,
    name: "Project name that is really really long",
    guidelines: "",
    tags: [],
};

const documents = [
    {
        pk: 0,
        name: "Document Name 1",
        tags: [],
        parts_count: 10,
        updated_at: "2022-04-22T19:47:56.943325Z",
    },
    {
        pk: 1,
        name: "My Document",
        tags: [],
        parts_count: 50,
        updated_at: "2022-01-12T19:47:56.943325Z",
    },
];

const characters = [
    { char: " ", frequency: 2285 },
    { char: "ئ", frequency: 58 },
    { char: "ع", frequency: 1008 },
    { char: "و", frequency: 1858 },
    { char: "ك", frequency: 222 },
    { char: "0", frequency: 3 },
    { char: "1", frequency: 2 },
    { char: "2", frequency: 10 },
    { char: "a", frequency: 15 },
    { char: "b", frequency: 85 },
    { char: "c", frequency: 3 },
    { char: "d", frequency: 6 },
    { char: "e", frequency: 12 },
    { char: "f", frequency: 68 },
    { char: "g", frequency: 2 },
    { char: "h", frequency: 44 },
    { char: "i", frequency: 5 },
    { char: "j", frequency: 7 },
    { char: "k", frequency: 8 },
    { char: "l", frequency: 2 },
    { char: "m", frequency: 89 },
    { char: "n", frequency: 1 },
    { char: "o", frequency: 11 },
    { char: "p", frequency: 22 },
    { char: "q", frequency: 33 },
    { char: "r", frequency: 41 },
    { char: "s", frequency: 64 },
    { char: "t", frequency: 86 },
    { char: "u", frequency: 38 },
    { char: "v", frequency: 86 },
    { char: "w", frequency: 66 },
    { char: "x", frequency: 58 },
    { char: "y", frequency: 65 },
    { char: "z", frequency: 77 },
    { char: "{", frequency: 22 },
    { char: "}", frequency: 1 },
    { char: "ؤ", frequency: 24 },
    { char: "‐", frequency: 56 },
    { char: "'", frequency: 2 },
    { char: ".", frequency: 5 },
    { char: ",", frequency: 33 },
    { char: "/", frequency: 27 },
    { char: "(", frequency: 8 },
    { char: ")", frequency: 8 },
];

const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { ProjectDashboard },
    template: "<ProjectDashboard v-bind=\"$props\" />",
    setup() {
        // setup mocks for API requests
        const mock = new MockAdapter(axios);
        const projectEndpoint = new RegExp(/\/projects\/\d+$/);
        const projectDocumentsEndpoint = new RegExp(
            /\/projects\/\d+\/documents$/,
        );
        const blockEndpoint = new RegExp(/\/projects\/\d+\/types\/block$/);
        const lineEndpoint = new RegExp(/\/projects\/\d+\/types\/line$/);
        const annotationsEndpoint = new RegExp(
            /\/projects\/\d+\/types\/annotations$/,
        );
        const partEndpoint = new RegExp(/\/projects\/\d+\/types\/part$/);
        const charactersEndpoint = new RegExp(/\/projects\/\d+\/characters$/);
        // mock project page
        mock.onGet(projectEndpoint).reply(async function() {
            // wait for 100-300 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, project];
        });
        // mock docmuents
        mock.onGet(projectDocumentsEndpoint).reply(async function(config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [200, { results: sorted(documents, { ordering }) }];
            }
            return [200, { results: documents }];
        });
        // mock ontology
        mock.onGet(blockEndpoint).reply(async function(config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [200, { results: sorted(blockTypes, { ordering }) }];
            }
            return [200, { results: blockTypes }];
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
        mock.onGet(charactersEndpoint).reply(async function(config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [200, { results: sorted(characters, { ordering }) }];
            }
            return [200, { results: characters }];
        });
    },
});

export const ProjectDashboardPage = Template.bind({});
ProjectDashboardPage.args = {
    id: 1,
};
