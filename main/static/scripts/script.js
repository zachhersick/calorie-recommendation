
// Small enhancement: ensure body fills viewport height on mobile chrome address bar changes
(function () {
    const setVH = () => document.documentElement.style.setProperty('--vh', window.innerHeight * 0.01 + 'px');
    setVH();
    window.addEventListener('resize', setVH, { passive: true });
})();
