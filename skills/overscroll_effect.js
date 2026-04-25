/**
 * overscroll.js
 * A high-fidelity implementation of the "rubber-band" overscroll effect.
 * Ported/Inspired by mobile OS physics (iOS/EverythingMe).
 */

const OverscrollEffect = (() => {
    const FRICTION = 0.45;    // Resistance when pulling past limits
    const RECOVERY = 1.2;     // Duration of the bounce back
    const EASE = "elastic.out(1, 0.5)";

    function init(selector) {
        const element = document.querySelector(selector);
        if (!element) return;

        let currentY = 0;
        let isOverpulling = false;
        let pullStart = 0;

        // Reset transform on start
        gsap.set(element, { y: 0 });

        const onWheel = (e) => {
            const isAtTop = element.scrollTop <= 0;
            const isAtBottom = element.scrollTop + element.clientHeight >= element.scrollHeight - 1;

            if ((isAtTop && e.deltaY < 0) || (isAtBottom && e.deltaY > 0)) {
                // Prevent default scrolling to handle custom pull
                if (e.cancelable) e.preventDefault();

                currentY -= e.deltaY * FRICTION;
                
                // Limit the pull distance (max 150px)
                currentY = Math.max(-150, Math.min(150, currentY));

                gsap.to(element, {
                    y: currentY,
                    duration: 0.1,
                    ease: "power2.out",
                    overwrite: "auto"
                });

                isOverpulling = true;
                
                // Clear any existing recovery timeout
                clearTimeout(element._recoveryTimer);
                element._recoveryTimer = setTimeout(recover, 150);
            }
        };

        const recover = () => {
            if (!isOverpulling) return;
            
            currentY = 0;
            isOverpulling = false;

            gsap.to(element, {
                y: 0,
                duration: RECOVERY,
                ease: EASE,
                overwrite: "auto"
            });
        };

        // Touch support
        let lastTouchY = 0;
        const onTouchStart = (e) => {
            lastTouchY = e.touches[0].clientY;
        };

        const onTouchMove = (e) => {
            const touchY = e.touches[0].clientY;
            const deltaY = lastTouchY - touchY;
            lastTouchY = touchY;

            const isAtTop = element.scrollTop <= 0;
            const isAtBottom = element.scrollTop + element.clientHeight >= element.scrollHeight - 1;

            if ((isAtTop && deltaY < 0) || (isAtBottom && deltaY > 0)) {
                if (e.cancelable) e.preventDefault();
                currentY -= deltaY * FRICTION;
                currentY = Math.max(-150, Math.min(150, currentY));
                gsap.set(element, { y: currentY });
                isOverpulling = true;
            }
        };

        element.addEventListener('wheel', onWheel, { passive: false });
        element.addEventListener('touchstart', onTouchStart, { passive: true });
        element.addEventListener('touchmove', onTouchMove, { passive: false });
        element.addEventListener('touchend', recover);
    }

    return { init };
})();

// Auto-initialize for EmoMirror scenes
window.addEventListener('DOMContentLoaded', () => {
    // Wait for GSAP
    if (window.gsap) {
        OverscrollEffect.init('.scene.active');
        OverscrollEffect.init('.review-grid');
    }
});
