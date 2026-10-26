import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import '@flaticon/flaticon-uicons/css/regular/rounded.css'
import './assets/styles.css'
import './assets/trace.css'

createApp(App).use(createPinia()).use(router).mount('#app')
