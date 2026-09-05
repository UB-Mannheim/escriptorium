<template>
    <div class="escr-downloads">
        <p
            v-if="loading"
            class="text-muted"
            v-translate
        >
            Loading...
        </p>
        <p
            v-else-if="error"
            class="text-danger"
        >
            {{ $gettext("Could not load downloads") }}: {{ error }}
        </p>
        <p
            v-else-if="!items.length"
            class="text-muted"
            v-translate
        >
            No downloads yet. Exports and archives you queue will show up here.
        </p>
        <table
            v-else
            class="table table-sm"
        >
            <thead>
                <tr>
                    <th v-translate>Label</th>
                    <th v-translate>Type</th>
                    <th class="text-right" v-translate>
                        Size
                    </th>
                    <th v-translate>Created</th>
                    <th v-translate>Expires</th>
                    <th class="text-right" v-translate>
                        Downloads
                    </th>
                    <th />
                </tr>
            </thead>
            <tbody>
                <tr
                    v-for="item in items"
                    :key="item.fingerprint"
                    :class="{ 'text-muted': item.is_expired }"
                >
                    <td>
                        <div>{{ item.label }}</div>
                        <small class="text-muted">
                            <code>{{ item.fingerprint.slice(0, 12) }}</code>
                        </small>
                    </td>
                    <td>
                        <small>{{ shortMime(item.mime_type) }}</small>
                    </td>
                    <td class="text-right">
                        {{ formatSize(item.file_size) }}
                    </td>
                    <td>
                        <small>{{ formatDate(item.created_at) }}</small>
                    </td>
                    <td>
                        <small>
                            <span v-if="!item.expires_at" v-translate>Never</span>
                            <span
                                v-else
                                :class="{ 'text-danger': item.is_expired }"
                            >
                                {{ formatDate(item.expires_at) }}
                            </span>
                        </small>
                    </td>
                    <td class="text-right">
                        {{ item.accessed_count || 0 }}
                    </td>
                    <td class="text-right">
                        <a
                            v-if="!item.is_expired"
                            :href="item.file_url"
                            class="btn btn-sm btn-primary mr-1"
                            download
                            v-translate
                        >
                            Download
                        </a>
                        <button
                            type="button"
                            class="btn btn-sm btn-outline-danger"
                            @click="onDelete(item)"
                            v-translate
                        >
                            Delete
                        </button>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>
<script>
import axios from "axios";
import { SCRIPT_NAME } from "../../../src/scriptname.js";

export default {
    name: "EscrDownloads",
    data() {
        return {
            items: [],
            loading: true,
            error: null,
        };
    },
    created() {
        this.fetch();
    },
    methods: {
        async fetch() {
            this.loading = true;
            this.error = null;
            try {
                // walk every api page or old rows stay hidden
                const items = [];
                let url = SCRIPT_NAME + "/api/downloads/";
                while (url) {
                    const r = await axios.get(url);
                    items.push(...(r.data.results || r.data || []));
                    url = r.data.next || null;
                }
                this.items = items;
            } catch (e) {
                this.error = e.message || String(e);
            } finally {
                this.loading = false;
            }
        },
        async onDelete(item) {
            const label = this.$gettext('Delete "%{label}"? This cannot be undone.');
            if (!confirm(this.$gettextInterpolate(label, { label: item.label }))) {
                return;
            }
            try {
                await axios.delete(SCRIPT_NAME + `/api/downloads/${item.fingerprint}/`);
                this.items = this.items.filter(
                    (x) => x.fingerprint !== item.fingerprint,
                );
            } catch (e) {
                this.error = e.message || String(e);
            }
        },
        formatSize(bytes) {
            if (!bytes && bytes !== 0) return "";
            const units = ["B", "KB", "MB", "GB", "TB"];
            let i = 0;
            let n = bytes;
            while (n >= 1024 && i < units.length - 1) {
                n /= 1024;
                i += 1;
            }
            return `${n.toFixed(n >= 100 || i === 0 ? 0 : 1)} ${units[i]}`;
        },
        formatDate(iso) {
            if (!iso) return "";
            const d = new Date(iso);
            return d.toLocaleString();
        },
        shortMime(m) {
            if (!m) return "";
            if (m === "application/zip") return "ZIP";
            if (m === "application/gzip") return "TAR.GZ";
            if (m === "application/json") return "JSON";
            return m;
        },
    },
};
</script>
