import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import ProjectsList from "../../vue/pages/ProjectsList/ProjectsList.vue";
import GlobalNavigation from "../../vue/components/GlobalNavigation/GlobalNavigation.vue";

import { currentUser, filteredByTag, sorted, tags } from "./util";

export default {
    title: "Pages/ProjectsList",
    component: ProjectsList,
    argTypes: {
        onClick: { action: "clicked" },
        onInput: { action: "input" },
        onCancel: { action: "cancel" },
    },
};

// tags and projects for list view
const projects = [
    {
        id: 0,
        slug: "project-name",
        name: "Project Name",
        owner: "Ryuichi Sakamoto",
        updated_at: "2022-08-09T09:01:12.145622Z",
        documents_count: 10,
        tags: tags.slice(0, 7),
    },
    {
        id: 1,
        slug: "second-project",
        name: "Second Project",
        owner: "Haruomi Hosono",
        updated_at: "2023-01-31T12:14:32.004501Z",
        documents_count: 100,
        tags: [tags[5], ...tags.slice(7, 9)],
    },
    {
        id: 2,
        slug: "a-third-project",
        name: "A Third Project",
        owner: "Yukihiro Takahashi",
        updated_at: "2022-01-09T17:24:40.044701Z",
        documents_count: 50,
        tags: [tags[7], tags[9], tags[10]],
    },
];

const newPk = Math.max(...tags.map((tag) => tag.pk)) + 1;
const newTagPks = [newPk];

const PageTemplate = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { ProjectsList, GlobalNavigation },
    // mimic the real-world django template
    template: `
    <div class="escr-body escr-vue-enabled">
        <div id="vue-global-nav">
            <GlobalNavigation isAuthenticated="true" />
        </div>
        <main>
            <section>
                <div>
                    <ProjectsList v-bind="$props" />
                </div>
            </section>
        </main>
    </div>`,
    setup() {
        // setup mocks for API requests
        const mock = new MockAdapter(axios);
        const projectsEndpoint = "/projects";
        const projectsTagsEndpoint = "/tags/project";
        const projectsIdEndpoint = new RegExp(`${projectsEndpoint}/*`);
        const currentUserEndpoint = "/users/current";
        // mock projects list
        mock.onGet(projectsEndpoint).reply(async function (config) {
            // wait for 100-300 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering, tags } = config.params;
                return [
                    200,
                    {
                        results: sorted(filteredByTag(projects, tags), {
                            ordering,
                        }),
                        next: "fake-nextpage",
                    },
                ];
            } else {
                return [200, { results: projects, next: "fake-nextpage" }];
            }
        });
        // mock tags list
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
        });
        // mock create project
        mock.onPost(projectsEndpoint).reply(async function () {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, projects[0]];
        });
        // mock delete project (throw an error, for fun!)
        mock.onDelete(projectsIdEndpoint).reply(async function () {
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
        // send one more dummy project from next page
        mock.onGet("fake-nextpage").reply(async function () {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [
                200,
                {
                    results: [
                        {
                            id: 3,
                            slug: "next-page-project",
                            name: "Fake project from next page",
                            owner: "John Smith",
                            updated_at: "2023-02-20T11:10:01.122122Z",
                            documents_count: 1,
                            tags: [tags[4]],
                        },
                    ],
                    next: null,
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
export const ProjectsListPage = PageTemplate.bind({});
ProjectsListPage.parameters = {
    layout: "fullscreen",
};
ProjectsListPage.args = {
    user: {
        first_name: "John",
    },
};
