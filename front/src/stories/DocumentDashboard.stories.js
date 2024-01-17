import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { Server } from "mock-socket";
import DocumentDashboard from "../../vue/pages/Document/Document.vue";
import GlobalNavigation from "../../vue/components/GlobalNavigation/GlobalNavigation.vue";
import {
    annotationTypes,
    blockTypes,
    characters,
    charactersRandomized,
    groups,
    lineTypes,
    models,
    partTypes,
    scripts,
    sorted,
    tags,
    textualWitnesses,
    transcriptions,
    users,
    userGroups,
    tasks,
    currentUser,
} from "./util";

export default {
    title: "Pages/Document Dashboard",
    component: DocumentDashboard,
    parameters: {
        // mock dropzone image upload api endpoint
        mockData: [
            {
                url: "/api/documents/1/parts",
                method: "POST",
                status: 201,
            },
        ],
    },
};

const doc = {
    line_offset: 0,
    main_script: "Arabic",
    name: "My Document",
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
    valid_block_types: blockTypes,
};

const metadata = [
    {
        pk: 1,
        key: {
            name: "example_key",
        },
        value: "value1",
    },
    {
        pk: 2,
        key: {
            name: "key2",
        },
        value: "example 2",
    },
];

const parts = [
    {
        title: "Element 2 - name_of_image.jpg",
        image: {
            thumbnails: {
                card:
                    // eslint-disable-next-line max-len
                    "https://gitlab.com/scripta/escriptorium/uploads/3cb1ea61edef4606848a2891b05a931c/1.png",
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
                    "https://gitlab.com/scripta/escriptorium/uploads/4334a28c59987228d2d498fe10a6784f/2.png",
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
                    "https://gitlab.com/scripta/escriptorium/uploads/e9f2fe1a19c4ff9892d045fe501304d1/3.png",
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
                    "https://gitlab.com/scripta/escriptorium/uploads/668ab44cd09e3dc0799df39dbba82449/4.png",
            },
        },
        updated_at: "2022-07-08T13:40:40.970483Z",
    },
];

const newPk = Math.max(...tags.map((tag) => tag.pk)) + 1;
const newDocumentTagPks = [newPk];

const newMetaPk = Math.max(...metadata.map((m) => m.pk)) + 1;
const newDocumentMetaPks = [newMetaPk];

const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { DocumentDashboard, GlobalNavigation },
    // mimic the real-world django template
    template: `
    <div class="escr-body escr-vue-enabled">
        <div id="vue-global-nav">
            <GlobalNavigation isAuthenticated="true" />
        </div>
        <main>
            <section>
                <div>
                    <DocumentDashboard v-bind="$props" />
                </div>
            </section>
        </main>
    </div>`,
    setup() {
        // setup websocket mocks for tasks
        const scheme = location.protocol === "https:" ? "wss:" : "ws:";
        const mockSocketURL = `${scheme}//${window.location.host}/ws/notif/`;
        // wrap in try/catch in case reloaded with mock socket still open
        try {
            const mockServer = new Server(mockSocketURL);
            // close after 30 minutes
            setTimeout(() => {
                mockServer.stop(() => console.log("websocket close"));
            }, 1800000);
        } catch (err) {
            console.log(err);
        }

        // setup mocks for API requests
        const mock = new MockAdapter(axios);
        const currentUserEndpoint = "/users/current";
        const documentEndpoint = new RegExp(/\/documents\/\d+$/);
        const documentMetadataEndpoint = new RegExp(
            /\/documents\/\d+\/metadata$/,
        );
        const documentMetadatumEndpoint = new RegExp(
            /\/documents\/\d+\/metadata\/\d+$/,
        );
        const documentModelsEndpoint = new RegExp(/\/models$/);
        const documentTagsEndpoint = new RegExp(/\/projects\/\d+\/tags$/);
        const scriptsEndpoint = "/scripts";
        const partsEndpoint = new RegExp(/\/documents\/\d+\/parts$/);
        const blockEndpointA = new RegExp(
            /\/documents\/\d+\/transcriptions\/\d+\/types\/block$/,
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
        const groupsEndpoint = "/groups";
        const shareEndpoint = new RegExp(/\/documents\/\d+\/share$/);
        const witnessesEndpoint = "/textual-witnesses";
        const tasksEndpoint = "/tasks";
        // mock document response
        mock.onGet(documentEndpoint).reply(async function () {
            // wait for 100-300 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, doc];
        });
        // mock ontology
        mock.onGet(blockEndpointA).reply(async function (config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [200, { results: sorted(blockTypes, { ordering }) }];
            }
            return [200, { results: blockTypes }];
        });
        mock.onGet(lineEndpoint).reply(async function (config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [200, { results: sorted(lineTypes, { ordering }) }];
            }
            return [200, { results: lineTypes }];
        });
        mock.onGet(annotationsEndpoint).reply(async function (config) {
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
        mock.onGet(partEndpoint).reply(async function (config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [200, { results: sorted(partTypes, { ordering }) }];
            }
            return [200, { results: partTypes }];
        });
        mock.onGet(charactersEndpointA).reply(async function (config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [200, sorted(characters, { ordering })];
            }
            return [200, characters];
        });
        mock.onGet(charactersEndpointB).reply(async function (config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [200, sorted(charactersRandomized, { ordering })];
            }
            return [200, charactersRandomized];
        });
        mock.onGet(charCountA).reply(async function () {
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { count: 128000 }];
        });
        mock.onGet(charCountB).reply(async function () {
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { count: 1729 }];
        });
        mock.onGet(partsEndpoint).reply(async function () {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { results: parts }];
        });
        // mock scripts
        mock.onGet(scriptsEndpoint).reply(async function () {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [
                200,
                { results: scripts.map((script) => ({ name: script })) },
            ];
        });
        // mock document tags
        mock.onGet(documentTagsEndpoint).reply(async function () {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { results: tags }];
        });
        // mock edit document
        mock.onPut(documentEndpoint).reply(async function (config) {
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
        mock.onPost(documentTagsEndpoint).reply(async function (config) {
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
        mock.onDelete(documentEndpoint).reply(async function () {
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

        // mock retrieve document metadata
        mock.onGet(documentMetadataEndpoint).reply(async function () {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { results: metadata }];
        });
        // mock create document metadata
        mock.onPost(documentMetadataEndpoint).reply(async function (config) {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            if (config?.data) {
                // mock creating a new metadatum with increment pk
                const { params } = JSON.parse(config.data);
                const { key, value } = params;
                const newMeta = Math.max(...newDocumentMetaPks) + 1;
                newDocumentMetaPks.push(newMeta);
                return [201, { key, value, pk: newMeta }];
            }
            return [400];
        });
        // mock update document metadatum
        mock.onPut(documentMetadatumEndpoint).reply(async function (config) {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            if (config?.data) {
                const { params } = JSON.parse(config.data);
                const { pk, key, value } = params;
                return [200, { pk, key, value }];
            }
            return [400];
        });
        // mock delete document metadatum
        mock.onDelete(documentMetadatumEndpoint).reply(async function () {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [204];
        });
        // mock get document models
        mock.onGet(documentModelsEndpoint).reply(async function () {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { results: models }];
        });
        // mock groups
        mock.onGet(groupsEndpoint).reply(async function () {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { results: userGroups }];
        });
        // mock share
        mock.onPost(shareEndpoint).reply(async function (config) {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            if (config?.data) {
                const { params } = JSON.parse(config.data);
                const { group, user } = params;
                if (
                    group &&
                    !doc.shared_with_groups.some(
                        (grp) => grp.pk.toString() === group.toString(),
                    )
                ) {
                    doc.shared_with_groups.push(
                        userGroups.find(
                            (grp) => grp.pk.toString() === group.toString(),
                        ),
                    );
                }
                if (user) {
                    doc.shared_with_users.push({ username: user });
                }
                // return the entire document with the shared_with_users
                // or shared_with_groups updated
                return [200, doc];
            }
            return [400];
        });
        // mock get textual witnesses
        mock.onGet(witnessesEndpoint).reply(async function () {
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { results: textualWitnesses }];
        });
        // mock get tasks
        mock.onGet(tasksEndpoint).reply(async function () {
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { results: tasks }];
        });

        // mock queuing or canceling tasks (always just throw error for now)
        const taskActionResponse = async function () {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [
                400,
                {
                    message:
                        "This is just a test environment, so you cannot queue or cancel tasks",
                },
            ];
        };
        [
            new RegExp(/\/documents\/\d+\/segment$/),
            new RegExp(/\/documents\/\d+\/transcribe$/),
            new RegExp(/\/documents\/\d+\/align$/),
            new RegExp(/\/documents\/\d+\/export$/),
            new RegExp(/\/documents\/\d+\/import$/),
            new RegExp(/\/documents\/\d+\/cancel_tasks$/),
        ].forEach((endpoint) =>
            mock.onPost(endpoint).reply(taskActionResponse),
        );

        // mock get current user
        mock.onGet(currentUserEndpoint).reply(async function () {
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, currentUser];
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
