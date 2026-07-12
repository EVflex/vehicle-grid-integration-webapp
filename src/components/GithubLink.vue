<template>
    <a :href="link" class="dark-link">
        <i class="bi icon-space" :class="icon"></i> {{ text }}
    </a>
</template>

<script>
    export default {
        props: { "text": String,
                 "link": String, 
                 "icon": { "type": String, default: "bi-github" },
        }
    }
</script>