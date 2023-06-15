<template>
    <svg
        width="30"
        height="30"
        viewBox="3 1 30 30"
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
                fill="#1761B5"
            />
        </g>
        <circle
            cx="14.9998"
            cy="13.0003"
            r="3.33333"
            stroke="white"
            stroke-width="1.25"
        />
        <path
            d="M15 18V19.6667"
            stroke="white"
            stroke-width="1.25"
            stroke-linecap="round"
        />
        <path
            d="M15 6.33301V7.99967"
            stroke="white"
            stroke-width="1.25"
            stroke-linecap="round"
        />
        <path
            d="M10 13L8.33333 13"
            stroke="white"
            stroke-width="1.25"
            stroke-linecap="round"
        />
        <path
            d="M21.6665 13L19.9998 13"
            stroke="white"
            stroke-width="1.25"
            stroke-linecap="round"
        />
        <path
            d="M18.5356 9.46387L19.7142 8.28536"
            stroke="white"
            stroke-width="1.25"
            stroke-linecap="round"
        />
        <path
            d="M10.2861 17.7139L11.4646 16.5354"
            stroke="white"
            stroke-width="1.25"
            stroke-linecap="round"
        />
        <path
            d="M18.5356 16.5361L19.7142 17.7146"
            stroke="white"
            stroke-width="1.25"
            stroke-linecap="round"
        />
        <path
            d="M10.2861 8.28613L11.4646 9.46464"
            stroke="white"
            stroke-width="1.25"
            stroke-linecap="round"
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
                    result="effect1_dropShadow_2119_5158"
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
                    in2="effect1_dropShadow_2119_5158"
                    result="effect2_dropShadow_2119_5158"
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
                    in2="effect2_dropShadow_2119_5158"
                    result="effect3_dropShadow_2119_5158"
                />
                <feBlend
                    mode="normal"
                    in="SourceGraphic"
                    in2="effect3_dropShadow_2119_5158"
                    result="shape"
                />
            </filter>
        </defs>
    </svg>
</template>
<script>
export default {
    name: "EscrLightModeIcon",
}
</script>
