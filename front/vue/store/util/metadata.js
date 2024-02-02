/**
 * Helper method that compares the sets of metadata from the state and the form, in order
 * to determine which (if any) metadata should be created, updated, or deleted on the backend.
 *
 * Returns an object with three named arrays:
 * { metadataToCreate, metadataToUpdate, metadataToDelete }.
 */
export const getMetadataCRUD = ({ stateMetadata, formMetadata }) => {
    // metadata without a pk in the form state must be new, so create on the backend
    const metadataToCreate = formMetadata.filter(
        (formMetadatum) => !formMetadatum.pk,
    );

    // loop through state metadata to see if any need to be deleted or updated
    const metadataToDelete = [];
    const metadataToUpdate = [];
    stateMetadata.map((m) => {
        // try to find metadatum from state in the form
        const formMetadatum = formMetadata.find(
            (formMeta) => formMeta.pk === m.pk,
        );
        if (!formMetadatum) {
            // if found in state but not form, that means it was deleted
            metadataToDelete.push(m);
        } else if (
            formMetadatum.key.name !== m.key.name ||
            formMetadatum.value !== m.value
        ) {
            // if found but keyname or value differs, it should be updated
            metadataToUpdate.push(formMetadatum);
        }
    });

    return { metadataToCreate, metadataToUpdate, metadataToDelete };
};
