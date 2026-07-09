<template>
    <div class="escr-downloads">
        <p
            v-if="loading"
            class="text-muted"
        >
            Loading...
        </p>
        <p
            v-else-if="error"
            class="text-danger"
        >
            Could not load downloads: {{ error }}
        </p>
        <table
            v-else-if="items.length"
            class="table table-sm"
        >
            <thead>
                <tr>
                    <th>Label</th>
                    <th>Type</th>
                    <th class="text-right">
                        Size
                    </th>
                    <th>Created</th>
                    <th>Expires</th>
                    <th class="text-right">
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
                            <span v-if="!item.expires_at">Never</span>
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
                        >
                            Download
                        </a>
                        <button
                            type="button"
                            class="btn btn-sm btn-outline-danger"
                            @click="onDelete(item)"
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
                const r = await axios.get("/api/downloads/");
                this.items = r.data.results || r.data || [];
            } catch (e) {
                this.error = e.message || String(e);
            } finally {
                this.loading = false;
            }
        },
        async onDelete(item) {
            if (!confirm(`Delete "${item.label}"? This cannot be undone.`)) {
                return;
            }
            try {
                await axios.delete(`/api/downloads/${item.fingerprint}/`);
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
