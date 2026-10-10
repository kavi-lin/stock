/* Explicit page tabs: a fresh visit always starts on this quarter's report. */
(function (scope) {
    'use strict';
    function init({root = document, browser = window, onChange = () => {}} = {}) {
        const tabs = [...root.querySelectorAll('[data-earnings-tab]')];
        let current = 'quarter';
        function select(name, {push = false, focus = false} = {}) {
            current = name === 'compare' ? 'compare' : 'quarter';
            for (const tab of tabs) {
                const active = tab.dataset.earningsTab === current;
                tab.setAttribute('aria-selected', String(active));
                tab.tabIndex = active ? 0 : -1;
                root.getElementById(tab.getAttribute('aria-controls')).hidden = !active;
                if (active && focus) tab.focus();
            }
            if (push) {
                const url = new URL(browser.location.href);
                if (current === 'compare') url.searchParams.set('tab', 'compare');
                else url.searchParams.delete('tab');
                url.hash = '';
                if (url.href !== browser.location.href) browser.history.pushState(null, '', url.href);
            }
            onChange(current);
        }
        function fromURL() { select(new URL(browser.location.href).searchParams.get('tab')); }
        tabs.forEach((tab, index) => {
            tab.addEventListener('click', () => select(tab.dataset.earningsTab, {push:true}));
            tab.addEventListener('keydown', event => {
                let target;
                if (event.key === 'ArrowRight') target = (index + 1) % tabs.length;
                else if (event.key === 'ArrowLeft') target = (index + tabs.length - 1) % tabs.length;
                else if (event.key === 'Home') target = 0;
                else if (event.key === 'End') target = tabs.length - 1;
                else return;
                event.preventDefault();
                select(tabs[target].dataset.earningsTab, {push:true, focus:true});
            });
        });
        browser.addEventListener('popstate', fromURL);
        fromURL();
        return {get current() { return current; }};
    }
    scope.EarningsTabs = {init};
    if (typeof module !== 'undefined') module.exports = {init};
})(typeof window !== 'undefined' ? window : globalThis);
