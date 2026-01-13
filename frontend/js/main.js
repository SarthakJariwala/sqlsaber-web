import "vite/modulepreload-polyfill";
import axios from "axios";

import { createInertiaApp } from "@inertiajs/svelte";
import { mount } from "svelte";


const pages = import.meta.glob("./pages/**/*.svelte", { eager: true });


document.addEventListener("DOMContentLoaded", () => {
	axios.defaults.xsrfCookieName = "csrftoken";
	axios.defaults.xsrfHeaderName = "X-CSRFToken";
	
  createInertiaApp({
    resolve: (name) => {
      const page = pages[`./pages/${name}.svelte`];
      return page;
    },
    setup({ el, App, props }) {
      mount(App, { target: el, props });
    },
  });
  
});
