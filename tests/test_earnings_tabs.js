'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const tabs=require('../Dashboard/earnings-tabs.js');
function setup(url='http://localhost/earnings-detail.html?ticker=TEST') {
    const panels={quarter:{hidden:false},compare:{hidden:true}};
    const buttons=['quarter','compare'].map(name=>({
        dataset:{earningsTab:name},attrs:{'aria-controls':name},handlers:{},
        setAttribute(key,value){this.attrs[key]=value;},getAttribute(key){return this.attrs[key];},
        addEventListener(key,handler){this.handlers[key]=handler;},focus(){this.focused=true;}
    }));
    const browser={location:{href:url},handlers:{},addEventListener(key,handler){this.handlers[key]=handler;}};
    const history=[];
    browser.history={pushState(_a,_b,next){history.push(next);browser.location.href=next;}};
    const root={querySelectorAll:()=>buttons,getElementById:id=>panels[id]};
    const changes=[];
    const state=tabs.init({root,browser,onChange:next=>changes.push(next)});
    return {buttons,panels,browser,history,changes,state};
}
test('ordinary visits and invalid tab values open the quarterly report',()=>{
    for (const suffix of ['', '&tab=unknown']) {
        const h=setup('http://localhost/earnings-detail.html?ticker=TEST'+suffix);
        assert.equal(h.state.current,'quarter');assert.equal(h.panels.quarter.hidden,false);assert.equal(h.panels.compare.hidden,true);
        assert.equal(h.buttons[0].attrs['aria-selected'],'true');assert.equal(h.buttons[1].tabIndex,-1);assert.equal(h.history.length,0);
    }
});
test('comparison is opt-in and can be linked directly',()=>{
    const h=setup('http://localhost/earnings-detail.html?ticker=TEST&tab=compare');
    assert.equal(h.state.current,'compare');assert.equal(h.panels.quarter.hidden,true);assert.equal(h.panels.compare.hidden,false);
});
test('clicks swap panels without reloading and preserve fiscal selection',()=>{
    const h=setup('http://localhost/earnings-detail.html?ticker=TEST&period=2026-03-31&revision=abc#ec-audit');
    h.buttons[1].handlers.click();assert.equal(h.panels.compare.hidden,false);assert.equal(h.panels.quarter.hidden,true);
    let url=new URL(h.browser.location.href);assert.equal(url.searchParams.get('tab'),'compare');assert.equal(url.searchParams.get('period'),'2026-03-31');assert.equal(url.hash,'');
    h.buttons[0].handlers.click();url=new URL(h.browser.location.href);assert.equal(url.searchParams.has('tab'),false);assert.equal(url.searchParams.get('revision'),'abc');assert.equal(h.panels.quarter.hidden,false);
});
test('browser back restores visible panel and selected tab',()=>{
    const h=setup();h.buttons[1].handlers.click();h.browser.location.href='http://localhost/earnings-detail.html?ticker=TEST';h.browser.handlers.popstate();
    assert.equal(h.state.current,'quarter');assert.equal(h.buttons[1].attrs['aria-selected'],'false');assert.equal(h.buttons[0].tabIndex,0);
});
test('arrow, home and end keys move focus with selection',()=>{
    const h=setup();let prevented=0;const key=(index,key)=>h.buttons[index].handlers.keydown({key,preventDefault(){prevented++;}});
    key(0,'ArrowRight');assert.equal(h.state.current,'compare');assert.equal(h.buttons[1].focused,true);
    key(1,'Home');assert.equal(h.state.current,'quarter');key(0,'End');assert.equal(h.state.current,'compare');key(1,'ArrowLeft');assert.equal(h.state.current,'quarter');
    assert.equal(prevented,4);key(0,'Tab');assert.equal(prevented,4);
});
