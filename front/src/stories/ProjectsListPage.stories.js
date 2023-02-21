import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import EscrNewProjectModal from "../../vue/pages/ProjectsList/NewProjectModal.vue";
import ProjectsList from "../../vue/pages/ProjectsList/ProjectsList.vue";

import { ManyTags } from "./Tags.stories";

export default {
    title: "Pages/ProjectsList",
    component: EscrNewProjectModal,
    argTypes: {
        onClick: { action: "clicked" },
        onInput: { action: "input" },
        onCancel: { action: "cancel" },
    },
};

const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { EscrNewProjectModal },
    template: "<EscrNewProjectModal v-bind=\"$props\" />",
});
export const NewProjectModal = Template.bind({});

// tags and projects for list view

const tags = [
    ...ManyTags.args.tags,
    {
        name: "Tag",
        variant: 4,
    },
    {
        name: "Tag tag",
        variant: 7,
    },
    {
        name: "Other tag",
        variant: 8,
    },
    {
        name: "A tag",
        variant: 6,
    },
];

const projects = [
    {
        id: 0,
        slug: "project-name",
        name: "Project Name",
        owner: "Ryuichi Sakamoto",
        updated_at: "2022-08-09T09:01:12.145622Z",
        documents_count: 10,
        tags: {
            tags: tags.slice(0, 7),
        },
    },
    {
        id: 1,
        slug: "second-project",
        name: "Second Project",
        owner: "Haruomi Hosono",
        updated_at: "2023-01-31T12:14:32.004501Z",
        documents_count: 100,
        tags: {
            tags: [tags[5], ...tags.slice(7, 9)],
        },
    },
    {
        id: 2,
        slug: "a-third-project",
        name: "A Third Project",
        owner: "Yukihiro Takahashi",
        updated_at: "2022-01-09T17:24:40.044701Z",
        documents_count: 50,
        tags: {
            tags: [tags[7], tags[9], tags[10]],
        },
    },
];

const sorted = (items, { ordering }) => {
    const alphabeticSort = (key) => (a, b) => {
        return a[key].toString().localeCompare(b[key].toString());
    };
    const numericSort = (key) => (a, b) => {
        return a[key] - b[key];
    };
    if (!ordering) {
        return [...items].sort(numericSort("id"));
    } else {
        // handle ordering param ("sortfield" = asc, "-sortfield" = desc)
        let sorted = [...items];
        const split = ordering.split("-");
        const sort = split.length == 1 ? split[0] : split[1];
        if (ordering.includes("documents_count")) {
            sorted.sort(numericSort(sort));
        } else {
            sorted.sort(alphabeticSort(sort));
        }
        if (split.length == 2) {
            sorted.reverse();
        }
        return sorted;
    }
};

const filteredByTag = (items, tags, operator) => {
    if (tags) {
        return items.filter((item) => {
            if (operator === "or") {
                return item.tags?.tags?.some((itemTag) =>
                    tags.includes(itemTag.name),
                );
            } else {
                return tags.every((tag) =>
                    item.tags?.tags?.some((itemTag) => itemTag.name === tag),
                );
            }
        });
    }
    return items;
};

// setup mocks for API requests
const mock = new MockAdapter(axios);
const projectsEndpoint = "/projects";
const projectsTagsEndpoint = "/project_tags";
const projectsIdEndpoint = new RegExp(`${projectsEndpoint}/*`);

const PageTemplate = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { ProjectsList },
    template: "<ProjectsList v-bind=\"$props\" />",
    setup() {
        // mock projects list
        mock.onGet(projectsEndpoint).reply(async function(config) {
            // wait for 100-300 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 100;
            await new Promise((r) => setTimeout(r, timeout));
            if (Object.keys(config.params).length) {
                const { ordering, tags, tags_op } = config.params;
                return [
                    200,
                    {
                        results: sorted(
                            filteredByTag(projects, tags, tags_op),
                            {
                                ordering
                            },
                        ),
                        next: "fake-nextpage",
                    },
                ];
            } else {
                return [200, { results: projects, next: "fake-nextpage" }];
            }
        });
        // mock tags list
        mock.onGet(projectsTagsEndpoint).reply(200, { tags });
        // mock create project
        mock.onPost(projectsEndpoint).reply(async function() {
            // wait for 200-400 ms to mimic server-side loading
            const timeout = Math.random() * 200 + 200;
            await new Promise((r) => setTimeout(r, timeout));
            return [200, projects[0]];
        });
        // mock delete project (throw an error, for fun!)
        mock.onDelete(projectsIdEndpoint).reply(async function() {
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
        mock.onGet("fake-nextpage").reply(async function() {
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
                            updated_at: "2023-02-20",
                            documents_count: 1,
                            tags: {
                                tags: [tags[4]],
                            },
                        },
                    ],
                    next: null,
                },
            ];
        });
    },
});
export const ProjectsListPage = PageTemplate.bind({});
ProjectsListPage.args = {
    user: {
        first_name: "John",
    },
};
