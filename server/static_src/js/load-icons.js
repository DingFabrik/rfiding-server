import { LogIn } from "lucide";
import replaceElement from "lucide/dist/esm/replaceElement.js";

// this is the same as the typical lucide config ...
const config = {
  // ... except that this is required as we are skipping the function which 
  // sets its default value
  nameAttr: "icon",
};

class LucideIcon extends HTMLElement {
  connectedCallback() {
    replaceElement(this, config);
  }
}

customElements.define("lucide-icon", LucideIcon);
// use as <lucide-icon data-lucide="log-in" {...anyAttrs}></lucide-icon>