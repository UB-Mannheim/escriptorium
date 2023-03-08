import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import ProjectDashboard from "../../vue/pages/Project/Project.vue";
import { ManyTags } from "./Tags.stories";
import {
    annotationTypes,
    blockTypes,
    characters,
    lineTypes,
    partTypes,
    sorted,
    tags,
} from "./util";

export default {
    title: "Pages/Project Dashboard",
    component: ProjectDashboard,
};

const project = {
    id: 1,
    name: "Project name that is really really long",
    guidelines: "",
    tags: ManyTags.args.tags,
};

const documents = [
    {
        pk: 0,
        name: "Document Name 1",
        tags: tags.slice(7, 10),
        parts_count: 10,
        updated_at: "2022-04-22T19:47:56.943325Z",
    },
    {
        pk: 1,
        name: "My Document",
        tags: tags.slice(3, 11),
        parts_count: 50,
        updated_at: "2022-01-12T19:47:56.943325Z",
    },
    {
        pk: 2,
        name: "My Other Document",
        tags: tags.slice(1, 3),
        parts_count: 100,
        updated_at: "2022-01-12T12:47:56.943325Z",
    },
    {
        pk: 3,
        name: "My Friend's Document",
        tags: tags.slice(2, 6),
        parts_count: 150,
        updated_at: "2022-09-08T19:47:56.943325Z",
    },
    {
        pk: 4,
        name: "A New Document",
        tags: tags.slice(4, 7),
        parts_count: 2,
        updated_at: "2022-04-04T19:47:56.943325Z",
    },
    {
        pk: 5,
        name: "The Book of Documents",
        tags: [],
        parts_count: 15,
        updated_at: "2022-02-14T19:47:56.943325Z",
    },
    {
        pk: 6,
        name: "A Document From A Book",
        tags: tags.slice(9, 11),
        parts_count: 200,
        updated_at: "2022-08-22T19:47:56.943325Z",
    },
    {
        pk: 7,
        name: "My PDF Conversion",
        tags: tags.slice(7, 11),
        parts_count: 50,
        updated_at: "2022-03-13T19:47:56.943325Z",
    },
    {
        pk: 8,
        name: "My Transcribed Manuscript",
        tags: tags.slice(1, 4),
        parts_count: 55,
        updated_at: "2022-02-02T19:47:56.943325Z",
    },
    {
        pk: 9,
        name: "An Ancient Text",
        tags: tags.slice(5, 8),
        parts_count: 72,
        updated_at: "2023-02-12T19:47:56.943325Z",
    },
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
