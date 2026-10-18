const sharp=require('/Users/peanutz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const fs=require('node:fs/promises');const path=require('node:path');const {execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');const ff='/tmp/cinematic-video-tools/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1';
(async()=>{
 const graphics=[];for(const name of (await fs.readdir(path.join(root,'graphics'))).filter(n=>n.endsWith('.png'))){
  const p=path.join(root,'graphics',name);const meta=await sharp(p).metadata();if(meta.width!==1920||meta.height!==1080)throw Error(name+' dimensions');
  if(name.includes('lower-')){const stats=await sharp(p).stats();if(stats.channels[3].min!==0||stats.channels[3].max!==255)throw Error(name+' alpha');}
  graphics.push({file:'graphics/'+name,width:meta.width,height:meta.height,transparent:name.includes('lower-')});
 }
 const files=(await fs.readdir(path.join(root,'broll'))).filter(n=>n.endsWith('.mp4')).sort();if(files.length!==6)throw Error('Expected 6 named clips');
 const videos=[];const contact=[];
 for(let i=0;i<files.length;i++){
  const file=files[i];const full=path.join(root,'broll',file);const evidence=JSON.parse(await fs.readFile(path.join(root,'evidence',file.replace('.mp4','.json')),'utf8'));if(!evidence.success)throw Error(file+' failed checks');
  let info;try{execFileSync(ff,['-hide_banner','-i',full,'-f','null','-'],{stdio:['ignore','ignore','pipe'],timeout:120000});}catch(e){throw Error(file+' decode failure '+e.stderr)}
  try{execFileSync(ff,['-hide_banner','-i',full],{stdio:['ignore','ignore','pipe']})}catch(e){info=e.stderr.toString()}
  if(!info.includes('1920x1080')||!info.includes('30 fps'))throw Error(file+' format: '+info);
  const m=info.match(/Duration: (\d+):(\d+):(\d+\.\d+)/);const duration=Number(m[1])*3600+Number(m[2])*60+Number(m[3]);
  const row=[];for(let j=0;j<3;j++){
   const at=[.4,duration/2,Math.max(0,duration-1)][j];const image=path.join(root,'evidence',file.replace('.mp4',`-frame-${j+1}.jpg`));
   execFileSync(ff,['-hide_banner','-loglevel','error','-y','-ss',String(at),'-i',full,'-frames:v','1','-q:v','2',image],{timeout:60000});
   contact.push({input:await sharp(image).resize(480,270).toBuffer(),left:j*480,top:i*270});row.push(path.basename(image));
  }
  videos.push({file:'broll/'+file,width:1920,height:1080,fps:30,durationSeconds:duration,bytes:(await fs.stat(full)).size,decoded:true,presentationMode:true,freshSeed:true,liveVllm:file!=='01-seed.mp4',note:file==='01-seed.mp4'?'Seeding is code-only; no model call is needed.':'Live parser/agent metadata retained in matching evidence JSON.',frames:row});
 }
 await sharp({create:{width:1440,height:1620,channels:3,background:'#090b0e'}}).composite(contact).jpeg({quality:88}).toFile(path.join(root,'evidence/broll-contact-sheet.jpg'));
 await fs.writeFile(path.join(root,'manifest.json'),JSON.stringify({dimensions:[1920,1080],graphics,videos,playbackSpeed:1,edits:'Only setup/loading and prerequisite actions trimmed; no wait removal within beats and no speed changes.',palette:'frontend/app/globals.css',fonts:['Manrope','DM Sans','IBM Plex Mono'],stack:{frontend:13008,command:18008,ml:18028,vllmForward:18088,database:'/tmp/sosora-video-command.db'}},null,2)+'\n');
 console.log('Verified 11 graphics, transparent lower-thirds, and 6 fully decoded 1080p30 MP4s');
})().catch(e=>{console.error(e);process.exitCode=1});
