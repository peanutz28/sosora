const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
const vm=require('node:vm');
test('A acknowledges once when idle, ignores typing, modifiers, repeats and busy agents',()=>{
  const source=fs.readFileSync(require('node:path').join(__dirname,'../components/shell/AppShell.tsx'),'utf8');
  const effect=source.slice(source.indexOf('  useEffect(() => {'),source.indexOf('  useEffect(() => {',source.indexOf('  useEffect(() => {')+1));
  let handler, calls=0;
  class HTMLElement {}
  const run=(busy=false,agentWorking=false)=>vm.runInNewContext(ts.transpileModule(effect,{compilerOptions:{target:ts.ScriptTarget.ES2020}}).outputText,{useEffect:fn=>fn(),window:{addEventListener:(_,fn)=>handler=fn},HTMLElement,busy,agentWorking,acknowledge:()=>calls++,setPresentation:()=>{},setIntelOpen:()=>{}});
  run();
  const event={key:'A',preventDefault(){}};
  handler(event); assert.equal(calls,1);
  for(const extra of [{repeat:true},{ctrlKey:true},{metaKey:true},{altKey:true},{target:Object.assign(new HTMLElement(),{tagName:'INPUT'})},{target:Object.assign(new HTMLElement(),{isContentEditable:true})}]) handler({...event,...extra});
  assert.equal(calls,1);
  run(true); handler(event); run(false,true); handler(event); assert.equal(calls,1);
});
