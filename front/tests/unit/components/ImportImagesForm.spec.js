import { shallowMount, createLocalVue } from "@vue/test-utils";
import Vuex, { Store } from "vuex";
import ImportImagesForm from "../../../vue/components/ImportModal/ImportImagesForm.vue";

const localVue = createLocalVue();
localVue.use(Vuex);

// The previous attempt at this fix read Dropzone.prototype.defaultOptions, which
// does not exist in the bundled build. Unit testing the handler in isolation did
// not catch it because the failure was in data(), at component init. Mount the
// component so that path is actually executed.
describe("ImportImagesForm", () => {
    let store;

    beforeEach(() => {
        store = new Store({
            modules: {
                document: { namespaced: true, state: { id: 115 } },
                forms: {
                    namespaced: true,
                    actions: { handleGenericInput: jest.fn() },
                },
            },
        });
    });

    const mountForm = () =>
        shallowMount(ImportImagesForm, {
            localVue,
            store,
            propsData: { invalid: {}, onImportComplete: jest.fn() },
            stubs: { ImageDropzone: true, UploadIcon: true },
        });

    it("builds its dropzone options without throwing", () => {
        expect(() => mountForm()).not.toThrow();
    });

    it("passes a thumbnail handler to dropzone", () => {
        const wrapper = mountForm();

        expect(typeof wrapper.vm.dropzoneOptions.thumbnail).toBe("function");
    });

    it("still accepts tiff, which is why the handler is needed", () => {
        const wrapper = mountForm();

        expect(wrapper.vm.dropzoneOptions.acceptedFiles).toContain("image/tiff");
    });

    it("targets the parts endpoint for the current document", () => {
        const wrapper = mountForm();

        expect(wrapper.vm.imageUploadURL).toBe("/api/documents/115/parts/");
    });
});
