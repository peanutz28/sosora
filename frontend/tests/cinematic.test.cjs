const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const Module=require('node:module');
const ts=require('typescript');
function load(file) {
  const name=path.resolve(__dirname,file), mod=new Module(name,module);
  mod.filename=name; mod.paths=Module._nodeModulePaths(path.dirname(name));
  mod._compile(ts.transpileModule(fs.readFileSync(name,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,esModuleInterop:true}}).outputText,name);
  return mod.exports;
}
const {routeStub}=load('../components/map/useLivingRoutes.ts');
const {isolationZone}=load('../components/map/useIsolationZone.ts');
test('broken route ends at the matching physical closure and retains the base side',()=>{
  const route={edge_ids:['bridge:f'],geometry:[[0,0],[1,0],[2,0],[3,0]]};
  assert.deepEqual(routeStub(route,[{id:'bridge:b',geometry:[[1.4,-.1],[1.4,.1]]}]),[[0,0],[1,0],[1.4,0]]);
  assert.deepEqual(routeStub(route,[{id:'other:f',geometry:[[1,0],[2,0]]}]),[]);
});
test('isolation hull includes only verified unreachable coordinates with a 400 m buffer',()=>{
  const incident=(id,lon,lat,reachable,route)=>({id,lon,lat,reachable,route,map_ready:true});
  const zone=isolationZone([incident('a',-82.42,35.62,false),incident('b',-82.41,35.62,false),incident('c',-82.42,35.63,false),incident('unknown',0,0,null),incident('bad',1,1,false,{status:'snap_failed'}),incident('ok',2,2,true)]);
  const ring=zone.features[0].geometry.coordinates[0];
  assert.ok(Math.min(...ring.map(p=>p[0])) < -82.424);
  assert.ok(Math.max(...ring.map(p=>p[1])) > 35.633);
  assert.ok(ring.every(p=>p[0]<-82 && p[1]>35));
  assert.equal(isolationZone([]).features.length,0);
  assert.equal(isolationZone([incident('a',-82.42,35.62,false)]).features.length,1);
});
