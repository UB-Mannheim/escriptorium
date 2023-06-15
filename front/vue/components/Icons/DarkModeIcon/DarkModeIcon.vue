<template>
    <svg
        width="64"
        height="30"
        viewBox="-9 1 30 30"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
    >
        <g filter="url(#dropshadow)">
            <rect
                x="4.5"
                y="2.5"
                width="21"
                height="21"
                rx="10.5"
                fill="#212323"
            />
        </g>
        <path
            fill-rule="evenodd"
            clip-rule="evenodd"
            d="M18.9708 15.0903C17.9489 14.9112 16.9298 14.1608 16.3157 13.0145C15.5898 11.6594 15.6419 10.1466 16.3428 9.18597C16.4146 9.08751 16.4933 8.99485 16.5786 8.90876C16.7432 8.74271 16.6957 8.43287 16.4642 8.39505C16.3133 8.37039 16.1599 8.35288 16.0045 8.34288C15.9027 8.33633 15.8 8.33301 15.6965 8.33301C13.1027 8.33301 11 10.4223 11 12.9997C11 15.577 13.1027 17.6663 15.6965 17.6663C17.1725 17.6663 18.4895 16.9898 19.3504 15.9317C19.4483 15.8115 19.5402 15.6864 19.6258 15.5568C19.7478 15.372 19.5786 15.1374 19.3564 15.1304C19.2283 15.1263 19.0995 15.1128 18.9708 15.0903Z"
            stroke="white"
            stroke-width="1.25"
        />
        <defs>
            <filter
                id="dropshadow"
                x="0.5"
                y="0.5"
                width="29"
                height="29"
                filterUnits="userSpaceOnUse"
                color-interpolation-filters="sRGB"
            >
                <feFlood
                    flood-opacity="0"
                    result="BackgroundImageFix"
                />
                <feColorMatrix
                    in="SourceAlpha"
                    type="matrix"
                    values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                    result="hardAlpha"
                />
                <feOffset dy="1" />
                <feGaussianBlur stdDeviation="1.5" />
                <feColorMatrix
                    type="matrix"
                    values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.1 0"
                />
                <feBlend
                    mode="normal"
                    in2="BackgroundImageFix"
                    result="effect1_dropShadow_2119_16508"
                />
                <feColorMatrix
                    in="SourceAlpha"
                    type="matrix"
                    values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                    result="hardAlpha"
                />
                <feOffset dy="1" />
                <feGaussianBlur stdDeviation="1" />
                <feColorMatrix
                    type="matrix"
                    values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.1 0"
                />
                <feBlend
                    mode="normal"
                    in2="effect1_dropShadow_2119_16508"
                    result="effect2_dropShadow_2119_16508"
                />
                <feColorMatrix
                    in="SourceAlpha"
                    type="matrix"
                    values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                    result="hardAlpha"
                />
                <feOffset dy="2" />
                <feGaussianBlur stdDeviation="2" />
                <feColorMatrix
                    type="matrix"
                    values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.1 0"
                />
                <feBlend
                    mode="normal"
                    in2="effect2_dropShadow_2119_16508"
                    result="effect3_dropShadow_2119_16508"
                />
                <feBlend
                    mode="normal"
                    in="SourceGraphic"
                    in2="effect3_dropShadow_2119_16508"
                    result="shape"
                />
            </filter>
        </defs>
    </svg>
</template>
<script>
export default {
    name: "EscrDarkModeIcon",
}
</script>
