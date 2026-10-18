// User-requested Playwright capture. Only this isolated stack is mutated.
const {chromium}=require('/Users/peanutz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs/promises');const path=require('node:path');const {execFileSync}=require('node:child_process');
const ROOT=path.resolve(__dirname,'..');const UI='http://127.0.0.1:13008';const API='http://127.0.0.1:18008';
const FFMPEG='/tmp/cinematic-video-tools/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1';
const CHROME='/Users/peanutz/Library/Caches/ms-playwright/chromium-1243/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const beats=['01-seed','02-beacon-hero','03-responder-confirm-A','04-dot-open','05-imagery-offline','06-water-spike'];
const only=process.argv[2];
const assert=(value,msg)=>{if(!value)throw new Error(msg)};
async function main(){
 await fs.mkdir(path.join(ROOT,'broll/raw'),{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:CHROME});
 try {for(const beat of beats.filter(b=>!only||b===only)){
  const context=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1,recordVideo:{dir:path.join(ROOT,'broll/raw'),size:{width:1920,height:1080}}});
  let p;let origin;const errors=[];const responses=[];const timings=[];
  const note={beat,viewport:[1920,1080],presentationMode:true,playbackSpeed:1,sourceFps:25,deliveryFps:30,liveVllm:beat!=='01-seed',liveVllmConfigured:true,sequence:[],responses,timings,errors};
  const startAction=async(key,url,tag)=>{
   const at=(Date.now()-origin)/1000;
   const [response]=await Promise.all([p.waitForResponse(r=>r.request().method()==='POST'&&r.url()===API+url,{timeout:240000}),p.keyboard.press(key)]);
   assert(response.ok(),tag+' HTTP '+response.status());const data=await response.json();
   responses.push({tag,path:url,status:response.status(),data});timings.push({tag,startSeconds:at,endSeconds:(Date.now()-origin)/1000});note.sequence.push(tag);
   await p.waitForFunction(()=>!document.querySelector('.drill-buttons button')?.disabled,{timeout:240000});return data;
  };
  const live=(data,parse=true)=>{
   if(parse)assert(data.parse?.parse_mode==='nemotron_lightning','Radio parse was not live');
   assert(data.agent_runtime?.cached===false,'Agent used cached replay');
   assert(data.agent_runtime?.model_id?.includes('nemotron'),'Missing live Nemotron identity');
   assert(!data.state.events.some(e=>e.kind==='agent_tool_result'&&e.call_id==='fallback'),'Agent hit fallback');
  };
  const cutoff=data=>assert(data.state.incidents.filter(i=>i.reachable===false).map(i=>i.id).join(',')==='SOS-001,SOS-002,SOS-003,SOS-004,SOS-005','Wrong cut-off incident set');
  try{
   const reset=await context.request.post(API+'/api/scenarios/reset');assert(reset.ok(),'Isolated reset failed');
   origin=Date.now();p=await context.newPage();p.on('pageerror',e=>errors.push({type:'pageerror',message:e.message}));p.on('console',m=>{if(m.type()==='error')errors.push({type:'console',message:m.text()})});
   await p.goto(UI,{waitUntil:'domcontentloaded',timeout:120000});
   await p.locator('.drill-buttons').waitFor({timeout:120000});await p.evaluate(()=>document.fonts.ready);
   await p.waitForFunction(()=>document.querySelector('.maplibregl-canvas')&&!document.body.textContent.includes('Loading the map')&&!document.body.textContent.includes('The map style did not load.'),{timeout:120000});
   await p.waitForTimeout(4000);await p.keyboard.press('p');assert(await p.locator('main.presentation').count()===1,'Presentation mode missing');
   assert(await p.getByTestId('hosted-demo-banner').count()===0,'Hosted/cached demo banner must not appear');
   let clipStart;
   if(beat==='01-seed')clipStart=(Date.now()-origin)/1000;
   const seed=await startAction('s','/api/radio/demo/seed','fresh-seed');
   assert(seed.state.incidents.length===9&&seed.state.incidents.every(i=>i.reachable),'Seed must have nine reachable incidents');
   await p.waitForTimeout(4000);
   if(beat!=='01-seed'){
    if(beat==='04-dot-open'){
     const prior=await startAction('b','/api/radio','prerequisite-beacon');live(prior);cutoff(prior);await p.waitForTimeout(4000);
    }
    clipStart=(Date.now()-origin)/1000;await p.waitForTimeout(1800);
    if(beat==='02-beacon-hero'){
     const data=await startAction('b','/api/radio','beacon');live(data);cutoff(data);
    }else if(beat==='03-responder-confirm-A'){
     const data=await startAction('r','/api/radio','ambiguous-responder');live(data);
     assert(data.assessment.needs_human_review,'Responder must ask for review');
     assert(data.state.closures.length===0,'Ambiguous responder must not close roads');
     await p.locator('button[title^="Confirm bridge A:"]').waitFor({state:'visible',timeout:30000});await p.waitForTimeout(4000);
     const [response]=await Promise.all([p.waitForResponse(r=>r.url()===API+'/api/radio/confirm'&&r.request().method()==='POST',{timeout:240000}),p.locator('button[title^="Confirm bridge A:"]').click()]);
     assert(response.ok(),'Confirm failed');const confirmed=await response.json();responses.push({tag:'confirm-A',path:'/api/radio/confirm',status:response.status(),data:confirmed});note.sequence.push('confirm-A');live(confirmed,false);cutoff(confirmed);
    }else if(beat==='04-dot-open'){
     const data=await startAction('d','/api/radio','unverified-DOT-open');live(data);cutoff(data);assert(data.state.closures.length>0,'Unverified open must not reopen bridge');
    }else if(beat==='05-imagery-offline'){
     const toggled=await startAction('i','/api/radio/demo/imagery','imagery-offline');assert(toggled.state.imagery.offline,'Outage not enabled');await p.waitForTimeout(2000);
     const data=await startAction('b','/api/radio','beacon-with-imagery-outage');live(data);cutoff(data);
     assert(data.state.events.some(e=>e.tool==='get_imagery_evidence'&&e.result?.error?.type==='ImageryUnavailable'),'Missing imagery error trace');
     assert(/imagery is unavailable/i.test(data.assessment.summary),'Assessment failed to disclose outage');
    }else if(beat==='06-water-spike'){
     const data=await startAction('w','/api/beacon/beacon-ww-bridge/reading','water-spike');live(data,false);cutoff(data);
    }
   }
   await p.waitForTimeout(6500);assert(await p.locator('main.presentation').count()===1,'Lost presentation mode');
   note.clipStartSeconds=clipStart;note.durationSeconds=(Date.now()-origin)/1000-clipStart;
   await p.screenshot({path:path.join(ROOT,'evidence',beat+'-final.png')});note.finalDOM=await p.locator('body').innerText();
   const rawPath=await p.video().path();await context.close();const rawNamed=path.join(ROOT,'broll/raw',beat+'.webm');await fs.rename(rawPath,rawNamed);
   const output=path.join(ROOT,'broll',beat+'.mp4');
   execFileSync(FFMPEG,['-hide_banner','-loglevel','error','-y','-ss',String(clipStart),'-i',rawNamed,'-t',String(note.durationSeconds),'-an','-c:v','libx264','-preset','medium','-crf','18','-r','30','-pix_fmt','yuv420p','-movflags','+faststart',output],{timeout:240000});
   assert(errors.length===0,'Browser errors occurred: '+JSON.stringify(errors));
   note.deliveryFile='broll/'+beat+'.mp4';note.rawFile='broll/raw/'+beat+'.webm';note.success=true;
   await fs.writeFile(path.join(ROOT,'evidence',beat+'.json'),JSON.stringify(note,null,2)+'\n');
   console.log(JSON.stringify({beat,success:true,seconds:note.durationSeconds}));
  }catch(error){
   note.success=false;note.failure=error.message;
   if(p)await p.screenshot({path:path.join(ROOT,'evidence',beat+'-FAILED.png')}).catch(()=>{});
   await context.close().catch(()=>{});await fs.writeFile(path.join(ROOT,'evidence',beat+'-FAILED.json'),JSON.stringify(note,null,2)+'\n');throw error;
  }
 }}finally{await browser.close()}
}
main().catch(e=>{console.error(e);process.exitCode=1});
