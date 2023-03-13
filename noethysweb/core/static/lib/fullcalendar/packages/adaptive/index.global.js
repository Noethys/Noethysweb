/*!
FullCalendar Adaptive Plugin v6.1.4
Docs & License: https://fullcalendar.io/docs/print
(c) 2023 Adam Shaw
*/
FullCalendar.Adaptive = (function (exports, core, premiumCommonPlugin, internal, preact) {
    'use strict';

    function _interopDefault (e) { return e && e.__esModule ? e : { 'default': e }; }

    var premiumCommonPlugin__default = /*#__PURE__*/_interopDefault(premiumCommonPlugin);

    internal.config.COLLAPSIBLE_WIDTH_THRESHOLD = 1200;
    let contexts = [];
    let undoFuncs = [];
    function contextInit(context) {
        if (!contexts.length) {
            attachGlobalHandlers();
        }
        contexts.push(context);
        context.calendarApi.on('_unmount', () => {
            internal.removeExact(contexts, context);
            if (!contexts.length) {
                removeGlobalHandlers();
            }
        });
    }
    function attachGlobalHandlers() {
        window.addEventListener('beforeprint', handleBeforePrint);
        window.addEventListener('afterprint', handleAfterPrint);
        // // for testing
        // let forPrint = false
        // document.addEventListener('keypress', (ev) => {
        //   if (ev.key === 'p') {
        //     forPrint = !forPrint
        //     if (forPrint) {
        //       handleBeforePrint()
        //     } else {
        //       handleAfterPrint()
        //     }
        //   }
        // })
    }
    function removeGlobalHandlers() {
        window.removeEventListener('beforeprint', handleBeforePrint);
        window.removeEventListener('afterprint', handleAfterPrint);
    }
    function handleBeforePrint() {
        let scrollEls = queryScrollerEls();
        let scrollCoords = queryScrollerCoords(scrollEls);
        for (let context of contexts) {
            context.emitter.trigger('_beforeprint');
        }
        preact.flushSync(() => {
            killHorizontalScrolling(scrollEls, scrollCoords);
            undoFuncs.push(() => restoreScrollerCoords(scrollEls, scrollCoords));
            undoFuncs.push(freezeScrollgridWidths());
        });
    }
    function handleAfterPrint() {
        for (let context of contexts) {
            context.emitter.trigger('_afterprint');
        }
        preact.flushSync(() => {
            while (undoFuncs.length) {
                undoFuncs.shift()();
            }
        });
    }
    // scrollgrid widths
    function freezeScrollgridWidths() {
        let els = internal.findElements(document.body, '.fc-scrollgrid');
        els.forEach(freezeScrollGridWidth);
        return () => els.forEach(unfreezeScrollGridWidth);
    }
    function freezeScrollGridWidth(el) {
        let elWidth = el.getBoundingClientRect().width;
        // along with collapsibleWidth, this is a hack for #5707
        if (!el.classList.contains('fc-scrollgrid-collapsible') || elWidth < internal.config.COLLAPSIBLE_WIDTH_THRESHOLD) {
            el.style.width = elWidth + 'px';
        }
    }
    function unfreezeScrollGridWidth(el) {
        el.style.width = '';
    }
    // scrollers
    // TODO: use scroll normalization!? yes
    function queryScrollerEls() {
        return internal.findElements(document.body, '.fc-scroller-harness > .fc-scroller');
    }
    function queryScrollerCoords(els) {
        return els.map((el) => {
            let computedStyle = window.getComputedStyle(el);
            return {
                scrollLeft: el.scrollLeft,
                scrollTop: el.scrollTop,
                overflowX: computedStyle.overflowX,
                overflowY: computedStyle.overflowY,
                marginBottom: computedStyle.marginBottom,
            };
        });
    }
    function killHorizontalScrolling(els, coords) {
        els.forEach((el, i) => {
            el.style.overflowX = 'visible'; // need to clear X/Y to get true overflow
            el.style.overflowY = 'visible'; // "
            el.style.marginBottom = ''; // for clipping away scrollbar. disable
            el.style.left = -coords[i].scrollLeft + 'px'; // simulate scrollLeft! will be position:relative
        });
    }
    function restoreScrollerCoords(els, coords) {
        els.forEach((el, i) => {
            let c = coords[i];
            el.style.overflowX = c.overflowX;
            el.style.overflowY = c.overflowY;
            el.style.marginBottom = c.marginBottom;
            el.style.left = '';
            el.scrollLeft = c.scrollLeft;
            el.scrollTop = c.scrollTop;
        });
    }

    var css_248z = ".fc .fc-event,.fc .fc-scrollgrid table tr{-moz-column-break-inside:avoid;break-inside:avoid}.fc-media-print{display:block;max-width:100%}.fc-media-print .fc-bg-event,.fc-media-print .fc-non-business,.fc-media-print .fc-timegrid-axis-chunk,.fc-media-print .fc-timegrid-slots,.fc-media-print .fc-timeline-slots{display:none}.fc-media-print .fc-h-event,.fc-media-print .fc-toolbar button,.fc-media-print .fc-v-event{background:#fff!important;color:#000!important}.fc-media-print .fc-event,.fc-media-print .fc-event-main{color:#000!important}.fc-media-print .fc-timegrid-event{margin:.5em 0}";
    internal.injectStyles(css_248z);

    var plugin = core.createPlugin({
        name: '@fullcalendar/adaptive',
        premiumReleaseDate: '2023-02-07',
        deps: [premiumCommonPlugin__default["default"]],
        contextInit,
    });

    core.globalPlugins.push(plugin);

    exports["default"] = plugin;

    Object.defineProperty(exports, '__esModule', { value: true });

    return exports;

})({}, FullCalendar, FullCalendar.PremiumCommon, FullCalendar.Internal, FullCalendar.Preact);
