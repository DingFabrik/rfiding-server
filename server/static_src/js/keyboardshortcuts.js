const isMac = navigator.platform.toUpperCase().includes('MAC');

document.addEventListener('keydown', (event) => {
const isModifierPressed = isMac ? event.metaKey : event.ctrlKey;
  if (isModifierPressed && event.key === 'k') {
    event.preventDefault();
    openModal('searchUniversalModal');
  }
});
