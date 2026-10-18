const {chromium}=require('/Users/peanutz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const sharp=require('/Users/peanutz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const fs=require('node:fs/promises'); const path=require('node:path');
const root=path.resolve(__dirname,'..');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Users/peanutz/Library/Caches/ms-playwright/chromium-1243/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'});
 const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
 const files=(await fs.readdir(path.join(root,'graphics'))).filter(f=>f.endsWith('.svg')).sort(); const qa=[];const thumbs=[];
 for(let i=0;i<files.length;i++){
  const file=files[i]; const svg=await fs.readFile(path.join(root,'graphics',file),'utf8');
  await page.setContent('<html><body style="margin:0">'+svg+'</body></html>'); await page.evaluate(()=>document.fonts.ready);
  const overflow=await page.locator('text').evaluateAll(items=>items.map(t=>({text:t.textContent,box:(b=>({x:b.x,y:b.y,width:b.width,height:b.height}))(t.getBBox())})).filter(t=>t.box.x<72||t.box.x+t.box.width>1848||t.box.y+t.box.height>1056));
  if(overflow.length) throw new Error(file+' overflow '+JSON.stringify(overflow));
  const png=path.join(root,'graphics',file.replace('.svg','.png')); await page.screenshot({path:png,omitBackground:true});
  const metadata=await sharp(png).metadata();qa.push({file,width:metadata.width,height:metadata.height,hasAlpha:metadata.hasAlpha,overflow});
  const thumbnail=await sharp(png).flatten({background:'#090b0e'}).resize(480,270).png().toBuffer(); thumbs.push({input:thumbnail,left:(i%3)*480,top:Math.floor(i/3)*270});
 }
 await sharp({create:{width:1440,height:Math.ceil(files.length/3)*270,channels:3,background:'#090b0e'}}).composite(thumbs).jpeg({quality:90}).toFile(path.join(root,'evidence/graphics-contact-sheet.jpg'));
 await fs.writeFile(path.join(root,'evidence/graphics_qa.json'),JSON.stringify(qa,null,2)+'\n'); await browser.close();console.log('Rendered '+files.length+' PNGs; typography bounds passed');
})().catch(e=>{console.error(e);process.exitCode=1});
