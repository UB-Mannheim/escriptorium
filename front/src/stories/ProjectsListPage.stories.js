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
        slug: "0-project-name",
        name: "Project Name",
        owner: "Ryuichi Sakamoto",
        updated_at: "2022-08-09",
        documents_count: 10,
        tags: {
            tags: tags.slice(0, 7),
        },
    },
    {
        slug: "1-second-project",
        name: "Second Project",
        owner: "Haruomi Hosono",
        updated_at: "2023-01-31",
        documents_count: 100,
        tags: {
            tags: [tags[5], ...tags.slice(7, 9)],
        },
    },
    {
        slug: "2-a-third-project",
        name: "A Third Project",
        owner: "Yukihiro Takahashi",
        updated_at: "2022-01-09",
        documents_count: 50,
        tags: {
            tags: [tags[7], tags[9], tags[10]],
        },
    },
];

const sorted = (items, { sort, dir }) => {
    const alphabeticSort = (key) => (a, b) => {
        return a[key].toString().localeCompare(b[key].toString());
    };
    const numericSort = (key) => (a, b) => {
        return a[key] - b[key];
    };
    if (dir === 0) {
        return [...items].sort(alphabeticSort("slug"));
    } else {
        let sorted = [...items];
        if (sort === "documents_count") {
            sorted.sort(numericSort(sort));
        } else if (sort) {
            sorted.sort(alphabeticSort(sort));
        }
        if (dir === -1) {
            sorted.reverse();
        }
        return sorted;
    }
};

const filteredByTag = (items, tags, operator) => {
    if (tags) {
        console.log(tags);
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

const PageTemplate = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { ProjectsList },
    template: "<ProjectsList v-bind=\"$props\" />",
    setup() {
        // mock projects list
        mock.onGet(projectsEndpoint).reply(function(config) {
            if (Object.keys(config.params).length) {
                const { sort, dir, tags, tags_op } = config.params;
                return [
                    200,
                    {
                        projects: sorted(
                            filteredByTag(projects, tags, tags_op),
                            {
                                sort,
                                dir,
                            },
                        ),
                    },
                ];
            } else {
                return [200, { projects }];
            }
        });
        // mock tags list
        mock.onGet(projectsTagsEndpoint).reply(200, { tags });
        // mock create project
        mock.onPost(projectsEndpoint).reply(200, { projects });
    },
});
export const ProjectsListPage = PageTemplate.bind({});
ProjectsListPage.args = {
    user: {
        first_name: "John",
    },
};
