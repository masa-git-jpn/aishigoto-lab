import { chromium } from 'playwright';
const b = await chromium.launch({ executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args:['--no-sandbox'] });
for (const [file, name, w, h] of [
  ['icon.html','x-icon',400,400],
  ['header.html','x-header',1500,500],
]) {
  const p = await b.newPage({ viewport:{width:w,height:h}, deviceScaleFactor:1 });
  await p.goto('file:///root/site/brand/'+file, { waitUntil:'networkidle' });
  await p.screenshot({ path:`/root/site/brand/${name}.png` });
  await p.close();
}
await b.close(); console.log('rendered');
