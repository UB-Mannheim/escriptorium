import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import ProjectDashboard from "../../vue/pages/Project/Project.vue";
import GlobalNavigation from "../../vue/components/GlobalNavigation/GlobalNavigation.vue";
import {
    annotationTypes,
    blockTypes,
    characters,
    filteredByTag,
    groups,
    lineTypes,
    partTypes,
    scripts,
    sorted,
    tags,
    users,
    userGroups,
    currentUser,
} from "./util";

export default {
    title: "Pages/Project Dashboard",
    component: ProjectDashboard,
};

const project = {
    id: 1,
    slug: "project-name-that-is-really-really-long",
    name: "Project name that is really really long",
    guidelines: "",
    tags: tags.slice(3, 8).map((tag) => tag.pk),
    shared_with_groups: groups,
    shared_with_users: users,
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

const newPk = Math.max(...tags.map((tag) => tag.pk)) + 1;
const newTagPks = [newPk];
const newDocumentTagPks = [newPk];

const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { ProjectDashboard, GlobalNavigation },
    // mimic the real-world django template
    template: `
    <div class="escr-body escr-vue-enabled">
        <div id="vue-global-nav">
            <GlobalNavigation isAuthenticated="true" />
        </div>
        <main>
            <section>
                <div>
                    <ProjectDashboard v-bind="$props" />
                </div>
            </section>
        </main>
    </div>`,
    setup() {
        // setup mocks for API requests
        const mock = new MockAdapter(axios);
        const projectEndpoint = new RegExp(/\/projects\/\d+$/);
        const projectDocumentsEndpoint = new RegExp(/\/documents/);
        const documentEndpoint = new RegExp(/\/documents\/\d+$/);
        const blockEndpoint = new RegExp(/\/projects\/\d+\/types\/block$/);
        const lineEndpoint = new RegExp(/\/projects\/\d+\/types\/line$/);
        const annotationsEndpoint = new RegExp(
            /\/projects\/\d+\/types\/annotations$/,
        );
        const partEndpoint = new RegExp(/\/projects\/\d+\/types\/part$/);
        const charactersEndpoint = new RegExp(/\/projects\/\d+\/characters$/);
        const documentTagsEndpoint = new RegExp(/\/projects\/\d+\/tags$/);
        const projectsTagsEndpoint = "/tags/project";
        const scriptsEndpoint = "/scripts";
        const groupsEndpoint = "/groups";
        const shareEndpoint = new RegExp(/\/projects\/\d+\/share$/);
        const currentUserEndpoint = "/users/current";
        // mock project page
        mock.onGet(projectEndpoint).reply(async function () {
            // wait for 100-300 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, project];
        });
        // mock docmuents
        mock.onGet(projectDocumentsEndpoint).reply(async function (config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering, tags } = config.params;
                return [
                    200,
                    {
                        results: sorted(filteredByTag(documents, tags), {
                            ordering,
                        }),
                    },
                ];
            }
            return [200, { results: documents }];
        });
        // mock create document
        mock.onPost(projectDocumentsEndpoint).reply(async function () {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, documents[0]];
        });
        // mock ontology
        mock.onGet(blockEndpoint).reply(async function (config) {
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
        mock.onGet(charactersEndpoint).reply(async function (config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering } = config.params;
                return [200, { results: sorted(characters, { ordering }) }];
            }
            return [200, { results: characters }];
        });
        // mock document tags
        mock.onGet(documentTagsEndpoint).reply(async function () {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { results: tags }];
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
        // mock all-projects tags list
        mock.onGet(projectsTagsEndpoint).reply(200, { results: tags });
        // mock create tag
        mock.onPost(projectsTagsEndpoint).reply(async function (config) {
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (config?.data) {
                // mock creating a new tag with increment pk
                const { params } = JSON.parse(config.data);
                const { name, color } = params;
                const newTag = Math.max(...newTagPks) + 1;
                newTagPks.push(newTag);
                return [200, { name, color, pk: newTag }];
            }
            return [500];
        });
        // mock edit project
        mock.onPut(projectEndpoint).reply(async function (config) {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            if (config?.data) {
                // mock return updated project
                const { params } = JSON.parse(config.data);
                const { name, guidelines, tags } = params;
                return [200, { ...project, name, guidelines, tags }];
            }
            return [500];
        });
        // mock scripts
        mock.onGet(scriptsEndpoint).reply(async function () {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, { results: scripts }];
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
                    !project.shared_with_groups.some(
                        (grp) => grp.pk.toString() === group.toString(),
                    )
                ) {
                    project.shared_with_groups.push(
                        userGroups.find(
                            (grp) => grp.pk.toString() === group.toString(),
                        ),
                    );
                }
                if (user) {
                    project.shared_with_users.push({ username: user });
                }
                // return the entire project with the shared_with_users
                // or shared_with_groups updated
                return [200, project];
            }
            return [400];
        });
        // mock delete project (throw an error, for fun!)
        mock.onDelete(projectEndpoint).reply(async function () {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [
                400,
                {
                    message:
                        "This is just a test environment, so you cannot delete a project.",
                },
            ];
        });
        // mock delete document (throw an error, for fun!)
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
        // mock get current user
        mock.onGet(currentUserEndpoint).reply(async function () {
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, currentUser];
        });
    },
});

export const ProjectDashboardPage = Template.bind({});
ProjectDashboardPage.parameters = {
    layout: "fullscreen",
};
ProjectDashboardPage.args = {
    id: 1,
};
