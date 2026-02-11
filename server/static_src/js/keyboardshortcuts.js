const isMac = navigator.platform.toUpperCase().includes('MAC');

document.addEventListener('keydown', (event) => {
const isModifierPressed = isMac ? event.metaKey : event.ctrlKey;
  if (event.metaKey && event.key === 'k') {
    event.preventDefault();
    const searchModal = new bootstrap.Modal(document.getElementById('searchUniversalModal'));
    searchModal.show();
  }
});