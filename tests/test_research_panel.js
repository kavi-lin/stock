'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function fixture() {
  return {enabled:true, cards:[{id:'claim', revision:'r1', status:'contested', kind:'fact', trigger:'news',
    text:'<img src=x onerror=alert(1)>', tickers:['TEST'], horizon:'one quarter', challenge:'Uncertain',
    evidence_refs:[{evidence_id:'feed',quote:'<script>bad()</script>'},{evidence_id:'page',quote:'Page excerpt'}],
    challenge_refs:[], evidence:[{id:'feed',source:'Feed',url:'javascript:alert(1)',content_type:'feed_excerpt'},
      {id:'page',source:'Primary',url:'https://example.com/release',content_type:'original_page_excerpt'}],
    published_at:'2026-10-05T00:00:00Z', falsifier:'A correction', followup:{condition:'Next release'}}],
    source_health:{}, experiment:{id:'exp',status:'complete'}};
}

async function mount(page, data=fixture()) {
  const nodes = new Map();
  function node() {return {value:'',handlers:{},addEventListener(name,fn){this.handlers[name]=fn;}};}
  const panel = {...node(), querySelector(selector){if(!nodes.has(selector)) nodes.set(selector,node()); return nodes.get(selector);}};
  const requests=[];
  const context={URL,URLSearchParams,location:{pathname:'/'+page,search:'?ticker=TEST'},
    document:{hidden:false,createElement(){return panel;},getElementById(){return {before(){}};}},
    setInterval(){},fetch:async(url,options)=>{requests.push({url,options});return {ok:true,json:async()=>options?{ok:true}:data};}};
  vm.runInNewContext(fs.readFileSync('Dashboard/research-panel.js','utf8'),context);
  await new Promise(resolve=>setImmediate(resolve));
  return {panel,nodes,requests};
}

test('break-news page does not mount research cards',async()=>{
  const h=await mount('break-news.html');
  assert.equal(h.requests.length,0);
});

test('real page entry maps all five lanes and distinguishes source provenance',async()=>{
  for(const [page,lane] of Object.entries({'decisions.html':'invest','earnings.html':'earnings',
    'earnings-detail.html':'earnings','momentum.html':'momentum','graph.html':'nexus'})) {
    const h=await mount(page);
    assert.match(h.requests[0].url,new RegExp('lane='+lane+'&ticker=TEST'));
    const html=h.nodes.get('.rp-grid').innerHTML;
    assert.match(html,/來源摘要/);assert.match(html,/原始網頁片段/);
    assert.match(html,/2026-10-05T00:00:00Z/);
    assert.match(html,/&lt;img/);assert.match(html,/&lt;script&gt;/);
    assert.doesNotMatch(html,/<script>|<img|href="javascript:/);
    assert.match(h.nodes.get('.rp-state').textContent,/六小時觀察已結束/);
  }
});

test('tracking sends the displayed claim revision and no model request',async()=>{
  const h=await mount('decisions.html');
  const button={dataset:{track:'claim'},disabled:false};
  await h.panel.handlers.click({target:{closest(){return button;}}});
  assert.equal(h.requests.length,2);assert.equal(h.requests[1].url,'/api/research/track');
  assert.deepEqual(JSON.parse(h.requests[1].options.body),{claim_id:'claim',revision:'r1'});
  assert.equal(button.textContent,'已追蹤');
});

test('production status supersedes completed trial and exposes estimate',async()=>{
  const data=fixture();data.service={status:'live',worker_pid:123,estimated_tokens_per_call:25000,
    heartbeat_at:'2026-10-05T10:00:00Z',budget:{calls:28}};
  const h=await mount('decisions.html',data);
  assert.match(h.nodes.get('.rp-state').textContent,/正式研究運行中/);
  assert.doesNotMatch(h.nodes.get('.rp-state').textContent,/目前未啟動/);
  assert.match(h.nodes.get('.rp-health').textContent,/25000 token/);
  data.service.status='live_blocked';data.service.blocker='quota';
  const blocked=await mount('decisions.html',data);
  assert.match(blocked.nodes.get('.rp-state').textContent,/暫停新推論/);
  assert.match(blocked.nodes.get('.rp-health').textContent,/暫停原因：quota/);
});
