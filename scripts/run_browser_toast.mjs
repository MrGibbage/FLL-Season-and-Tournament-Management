// Chrome DevTools pipe transport: no npm packages, browser downloads, or server.
import {spawn} from 'node:child_process';
import {writeFile} from 'node:fs/promises';
import {StringDecoder} from 'node:string_decoder';
const [executable, profile, url, output, instructionsUrl] = process.argv.slice(2);
const child = spawn(executable, ['--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--host-resolver-rules=MAP * ~NOTFOUND','--remote-debugging-pipe','--user-data-dir='+profile],{stdio:['ignore','ignore','pipe','pipe','pipe'],windowsHide:true});
let id=0, buffer='', stderr='', session;
const decoder=new StringDecoder('utf8');
const waiting=new Map();
child.on('exit',()=>{for(const entry of waiting.values()){clearTimeout(entry.timer);entry.reject(Error('Browser exited before responding'));}waiting.clear();});
child.stderr.on('data',chunk=>stderr+=chunk.toString());
child.stdio[4].on('data',chunk=>{
  buffer+=decoder.write(chunk);let end;
  while((end=buffer.indexOf('\0'))>=0){const raw=buffer.slice(0,end);buffer=buffer.slice(end+1);if(!raw)continue;const message=JSON.parse(raw);if(message.id){const entry=waiting.get(message.id);if(entry){waiting.delete(message.id);clearTimeout(entry.timer);message.error?entry.reject(Error(JSON.stringify(message.error))):entry.resolve(message.result);}}}
});
function rpc(method,params={},sessionId){return new Promise((resolve,reject)=>{const request=++id;const timer=setTimeout(()=>{waiting.delete(request);reject(Error('Timed out: '+method));},90000);waiting.set(request,{resolve,reject,timer});child.stdio[3].write(JSON.stringify({id:request,method,params,...(sessionId?{sessionId}:{} )})+'\0');});}
try{
  await rpc('Browser.getVersion');
  const {targetId}=await rpc('Target.createTarget',{url:'about:blank'});
  session=(await rpc('Target.attachToTarget',{targetId,flatten:true})).sessionId;
  await rpc('Page.enable',{},session);await rpc('Runtime.enable',{},session);
  await rpc('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false},session);
  await rpc('Page.navigate',{url},session);
  // Real browser time is essential: virtual-time budgets can expire while
  // File.arrayBuffer() is still waiting for the browser's file IO thread.
  const expression=`new Promise(resolve=>{let n=0;const poll=()=>{if(window.browserToastTestResults)return resolve(window.browserToastTestResults);if(document.documentElement.dataset.testResult==='fail'){try{return resolve(JSON.parse(document.getElementById('test-results').textContent));}catch{}}if(n++>1200)return resolve({failed:1,fatal:'Suite timed out',progress:document.getElementById('test-results')?.textContent});setTimeout(poll,50);};poll();})`;
  // Wait for the navigation to commit before evaluating in the document.
  let report;
  for(let tries=0;tries<10;tries++)try{const evaluated=await rpc('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true},session);if(evaluated.exceptionDetails)throw Error(JSON.stringify(evaluated.exceptionDetails));report=evaluated.result.value;break;}catch(e){if(tries===9)throw e;await new Promise(r=>setTimeout(r,100));}
  await writeFile(output,JSON.stringify(report,null,2));
  await rpc('Runtime.evaluate',{expression:`ToastApp.loadFiles(TEST_DATA.fixtures[0].files.map(f=>new File([Uint8Array.from(atob(f.base64),c=>c.charCodeAt(0))],f.name)))`,awaitPromise:true},session);
  for(const [label,width,height,mobile] of [['desktop',1280,1000,false],['mobile',390,844,true]]){
    await rpc('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile},session);
    const shot=await rpc('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},session);
    await writeFile(output.replace(/\.json$/,'-'+label+'.png'),Buffer.from(shot.data,'base64'));
  }
  await rpc('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false},session);
  await rpc('Runtime.evaluate',{expression:`document.getElementById('preview-script').click();document.getElementById('expand-preview').click();`},session);
  const expanded=await rpc('Page.captureScreenshot',{format:'png',captureBeyondViewport:false},session);
  await writeFile(output.replace(/\.json$/,'-expanded.png'),Buffer.from(expanded.data,'base64'));
  if(instructionsUrl){
    await rpc('Page.navigate',{url:instructionsUrl},session);await new Promise(resolve=>setTimeout(resolve,200));
    for(const [label,width,height,mobile] of [['instructions',1280,1000,false],['instructions-mobile',390,844,true]]){
      await rpc('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile},session);
      const shot=await rpc('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},session);
      await writeFile(output.replace(/\.json$/,'-'+label+'.png'),Buffer.from(shot.data,'base64'));
    }
  }
  console.log(JSON.stringify({passed:report.passed,failed:report.failed,total:report.total,fatal:report.fatal}));
  process.exitCode=report.failed?1:0;
}catch(error){console.error(error.stack);process.exitCode=1;}
finally{
  await writeFile(output+'.stderr.log',stderr);
  try{await rpc('Browser.close');}catch{}
  child.kill();
}
