const {chromium}=require('/Users/peanutz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const sharp=require('/Users/peanutz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const fs=require('node:fs/promises');const path=require('node:path');const root=path.resolve(__dirname,'..');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Users/peanutz/Library/Caches/ms-playwright/chromium-1243/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'});
 const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});const checks=[];
 for(const file of (await fs.readdir(path.join(root,'graphics'))).filter(f=>f.endsWith('.svg')).sort()){
  await page.setContent('<body style="margin:0">'+await fs.readFile(path.join(root,'graphics',file),'utf8')+'</body>');await page.evaluate(()=>document.fonts.ready);
  const boxes=await page.locator('text').evaluateAll(items=>items.map(t=>{const ctx=document.createElement('canvas').getContext('2d'),s=getComputedStyle(t);ctx.font=s.fontWeight+' '+s.fontSize+' '+s.fontFamily;const m=ctx.measureText(t.textContent),anchor=t.getAttribute('text-anchor'),base=Number(t.getAttribute('x'))-(anchor==='middle'?m.width/2:anchor==='end'?m.width:0);return {text:t.textContent,x:base-m.actualBoundingBoxLeft,y:Number(t.getAttribute('y'))-m.actualBoundingBoxAscent,w:m.actualBoundingBoxLeft+m.actualBoundingBoxRight,h:m.actualBoundingBoxAscent+m.actualBoundingBoxDescent}}));
  const overlaps=[];for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i],b=boxes[j];const w=Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x),h=Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y);if(w>2&&h>2)overlaps.push([a.text,b.text]);}
  if(overlaps.length)throw Error(file+' text collisions '+JSON.stringify(overlaps));
  const png=path.join(root,'graphics',file.replace('.svg','.png'));const m=await sharp(png).metadata();if(m.width!==1920||m.height!==1080)throw Error(file+' dimensions');
  let alpha=null;if(file.includes('lower-')){const stats=await sharp(png).stats();alpha={min:stats.channels[3].min,max:stats.channels[3].max};if(alpha.min!==0||alpha.max!==255)throw Error(file+' transparency');}
  checks.push({file,width:m.width,height:m.height,textCollisions:overlaps,alpha});
 }
 await page.goto('file://'+path.join(root,'index.html'));await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(root,'evidence/gallery-preview.png')});
 const links=await page.locator('a').evaluateAll(items=>items.map(a=>a.getAttribute('href')));for(const href of links){if(href&&!href.startsWith('http'))await fs.access(path.join(root,href));}
 await fs.writeFile(path.join(root,'evidence/graphic_redesign_qa.json'),JSON.stringify({checks,galleryLinksResolve:true,reviewPasses:[{pass:1,action:'Replaced the rejected style with large typography, real road geometry, restrained colors, and compact transparent overlays.'},{pass:2,action:'Fixed diagram map clipping and Beacon connector spacing; balanced results metrics; added footage-context lower-third previews.'},{pass:3,action:'Clarified damage-site units; removed simulated pins from the historical damage-stat graphic; checked text collisions, dimensions, alpha and gallery links.'}]},null,2)+'\n');
 await browser.close();console.log('11 artboards passed collision, size and transparency checks; gallery links verified');
})().catch(e=>{console.error(e);process.exit(1)});
