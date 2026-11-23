(() => {
  const clip = new Audio('/ui-click.wav');
  clip.preload = 'auto';
  const channels = [clip, clip.cloneNode(true), clip.cloneNode(true)];
  let channel = 0;
  let pointerTarget;
  let lastTap = -Infinity;

  function play() {
    const sound = channels[channel];
    channel = (channel + 1) % channels.length;
    sound.currentTime = 0;
    sound.play().catch(() => {});
  }

  function pointer(event) {
    if (!event.isPrimary || event.button !== 0) return;
    pointerTarget = event.target;
    lastTap = performance.now();
    play();
  }
  // Mouse activation happens on press. Touch and pen activate on release.
  window.addEventListener('pointerdown', event => {
    if (event.pointerType === 'mouse') pointer(event);
  }, true);
  window.addEventListener('pointerup', event => {
    if (event.pointerType !== 'mouse') pointer(event);
  }, true);
  window.addEventListener('click', event => {
    if (event.detail === 0 || !pointerTarget) play();
    pointerTarget = null;
  }, true);
  window.addEventListener('pointercancel', () => { pointerTarget = null; }, true);
  // Native select popups may only report a change to the document.
  window.addEventListener('change', event => {
    if (event.target instanceof HTMLSelectElement && performance.now() - lastTap > 180) play();
  }, true);
})();
