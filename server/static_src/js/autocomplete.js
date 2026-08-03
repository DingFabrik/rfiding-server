const DEFAULTS = {
  threshold: 2,
  maximumItems: 5,
  highlightTyped: true,
  highlightClass: 'text-primary',
  label: 'label',
  value: 'value',
  showValue: false,
  showValueBeforeLabel: false,
};

let autocompleteCounter = 0;

class Autocomplete {
  constructor(field, options) {
    this.field = field;
    this.options = Object.assign({}, DEFAULTS, options);

    const anchorName = `--autocomplete-${++autocompleteCounter}`;
    field.style.setProperty('anchor-name', anchorName);

    this.menu = ce(`<ul class="dropdown menu w-full rounded-box bg-base-100 shadow-lg" popover style="position-anchor:${anchorName}"></ul>`);
    if (this.options.dropdownClass)
      this.menu.classList.add(this.options.dropdownClass);

    insertAfter(this.menu, field);

    field.addEventListener('click', (e) => {
      if (this.createItems() === 0) {
        e.stopPropagation();
        this.hide();
      }
    });

    field.addEventListener('input', () => {
      if (this.options.onInput)
        this.options.onInput(this.field.value);
      this.renderIfNeeded();
    });

    field.addEventListener('keydown', (e) => {
      if (e.keyCode === 27) {
        this.hide();
        return;
      }
      if (e.keyCode === 40) {
        this.menu.querySelector('.autocomplete-item')?.focus();
        return;
      }
    });
  }

  show() {
    if (!this.menu.matches(':popover-open'))
      this.menu.showPopover();
  }

  hide() {
    if (this.menu.matches(':popover-open'))
      this.menu.hidePopover();
  }

  setData(data) {
    this.options.data = data;
    this.renderIfNeeded();
  }

  renderIfNeeded() {
    if (this.createItems() > 0)
      this.show();
    else
      this.field.click();
  }

  createItem(lookup, item) {
    let label;
    if (this.options.highlightTyped) {
      const idx = removeDiacritics(item.label)
          .toLowerCase()
          .indexOf(removeDiacritics(lookup).toLowerCase());
      const className = Array.isArray(this.options.highlightClass) ? this.options.highlightClass.join(' ')
        : (typeof this.options.highlightClass == 'string' ? this.options.highlightClass : '');
      label = item.label.substring(0, idx)
        + `<span class="${className}">${item.label.substring(idx, idx + lookup.length)}</span>`
        + item.label.substring(idx + lookup.length, item.label.length);
    } else {
      label = item.label;
    }

    if (this.options.showValue) {
      if (this.options.showValueBeforeLabel) {
        label = `${item.value} ${label}`;
      } else {
        label += ` ${item.value}`;
      }
    }

    const li = ce(`<li></li>`);
    const button = ce(`<button type="button" class="autocomplete-item" data-label="${item.label}" data-value="${item.value}">${label}</button>`);
    li.appendChild(button);
    return li;
  }

  createItems() {
    const lookup = this.field.value;
    if (lookup.length < this.options.threshold) {
      this.hide();
      return 0;
    }

    this.menu.innerHTML = '';

    const keys = Object.keys(this.options.data);

    let count = 0;
    for (let i = 0; i < keys.length; i++) {
      const key = keys[i];
      const entry = this.options.data[key];
      const item = {
          label: this.options.label ? entry[this.options.label] : key,
          value: this.options.value ? entry[this.options.value] : entry
      };

      if (removeDiacritics(item.label).toLowerCase().indexOf(removeDiacritics(lookup).toLowerCase()) >= 0) {
        this.menu.appendChild(this.createItem(lookup, item));
        if (this.options.maximumItems > 0 && ++count >= this.options.maximumItems)
          break;
      }
    }

    this.menu.querySelectorAll('.autocomplete-item').forEach((item) => {
      item.addEventListener('click', (e) => {
        let dataLabel = e.currentTarget.getAttribute('data-label');
        let dataValue = e.currentTarget.getAttribute('data-value');

        this.field.value = dataLabel;

        if (this.options.onSelectItem) {
          this.options.onSelectItem({
            value: dataValue,
            label: dataLabel
          });
        }

        this.hide();
      })
    });

    return this.menu.childNodes.length;
  }
}

/**
 * @param html
 * @returns {Node}
 */
function ce(html) {
  let div = document.createElement('div');
  div.innerHTML = html;
  return div.firstChild;
}

/**
 * @param elem
 * @param refElem
 * @returns {*}
 */
function insertAfter(elem, refElem) {
  return refElem.parentNode.insertBefore(elem, refElem.nextSibling);
}

const COMBINING_DIACRITICS = new RegExp('[' + String.fromCharCode(0x0300) + '-' + String.fromCharCode(0x036f) + ']', 'g');

/**
 * @param {String} str
 * @returns {String}
 */
function removeDiacritics(str) {
  return str
      .normalize('NFD')
      .replace(COMBINING_DIACRITICS, '');
}

export { Autocomplete };
