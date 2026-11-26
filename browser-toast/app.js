'use strict';
(() => {
  const $=id=>document.getElementById(id);
  let revision=0, result=null, diagnostic=null, busy=false, retainedHandles=null, hasSelection=false, pickerBlocked=false;
  function updateRefresh() {
    $('refresh').hidden=!hasSelection;$('refresh').disabled=busy;
    $('refresh-help').hidden=!hasSelection;
    $('refresh-help').textContent=retainedHandles?'After saving changes in Excel, click Check again to read the latest files.':'This selection cannot be refreshed directly. Check again will ask you to select the saved files so TOAST reads your latest changes.';
  }
  const outputButtons=['download-script','download-summary','preview-script','preview-summary'];
  let previousOverflow='';
  function expandPreview(expanded) {
    const wasExpanded=$('preview').classList.contains('expanded');
    if(expanded&&!wasExpanded)previousOverflow=document.body.style.overflow;
    $('preview').classList.toggle('expanded',expanded);
    document.body.style.overflow=expanded?'hidden':wasExpanded?previousOverflow:document.body.style.overflow;
    $('expand-preview').textContent=expanded?'Return to TOAST':'Expand preview';
    $('expand-preview').setAttribute('aria-pressed',String(expanded));
  }
  function closePreview() {expandPreview(false);$('preview').hidden=true;$('preview-frame').removeAttribute('srcdoc');}
  function clearView() {
    closePreview();
    result=null;diagnostic=null;
    for(const id of ['review','documents','failure','preview','ready'])$(id).hidden=true;
    $('preview-frame').removeAttribute('srcdoc');
    $('approve').value='';$('review-warnings').checked=false;
    outputButtons.forEach(id=>$(id).disabled=true);
  }
  function permitted() {
    return !busy&&Boolean(result?.outputs)&&!result.validation.errors.length&&(!result.validation.warnings.length||$('review-warnings').checked)&&(!result.validation.missing.length||$('approve').value==='YES');
  }
  function updateGate() {
    const ready=permitted();outputButtons.forEach(id=>$(id).disabled=!ready);
    $('ready').hidden=!ready;
    $('document-gate').textContent=ready?'Both documents are ready.':result?.validation.errors.length?'Correct the errors before generating documents.':'Review the warnings and approve any intentional award omissions to unlock your documents.';
    if(!ready)closePreview();
  }
  function notice(id,items) {
    $(id).hidden=!items.length;const list=$(id).querySelector('ul');list.replaceChildren();
    for(const item of items){const li=document.createElement('li');const issue=id==='errors'?result?.validation.inputIssues.find(issue=>issue.message===item):null;if(issue){const title=document.createElement('strong');title.textContent=issue.location;const text=document.createElement('div');text.textContent=issue.instruction;li.append(title,text);}else li.textContent=item;list.append(li);}
  }
  function download(name,content,type='text/html;charset=utf-8') {
    const url=URL.createObjectURL(new Blob([content],{type}));
    const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),30000);
  }
  function report() {
    if(diagnostic)download('toast-diagnostic-report.json',JSON.stringify({...diagnostic,review:{warningsAcknowledged:$('review-warnings').checked,awardOmissionsApproved:Boolean(result?.validation.missing.length)&&$('approve').value==='YES',documentsAvailable:permitted()}},null,2),'application/json');
  }
  async function loadFiles(selection,handles=null) {
    const files=Array.from(selection), current=++revision;clearView();busy=true;retainedHandles=handles;hasSelection=files.length>0;updateRefresh();$('file-list').replaceChildren();
    $('status').textContent='Reading and checking your saved workbooks…';$('dropzone').setAttribute('aria-busy','true');
    for(const file of files){const li=document.createElement('li');li.textContent=file.name+' · '+(file.size/1024).toFixed(0)+' KB';$('file-list').append(li);}
    diagnostic={version:Toast.VERSION,createdAt:new Date().toISOString(),browser:navigator.userAgent,protocol:location.protocol,files:files.map(f=>({name:f.name,bytes:f.size,lastModified:new Date(f.lastModified).toISOString()})),errors:[],warnings:[],missingAwards:[]};
    const attemptReport=diagnostic;
    try {
      if(!files.length)throw Error('No files selected. Choose your saved OJS workbook(s).');
      if(files.length>3)throw Error('Select one or two OJS workbooks and, if needed, one configuration JSON file.');
      if(files.some(f=>!/\.(xlsm|xlsx|json)$/i.test(f.name)))throw Error('Supported files are .xlsm, .xlsx, and tournament configuration .json.');
      if(files.some(f=>f.name.startsWith('~$')))throw Error('An Excel temporary lock file was selected. Choose the actual OJS workbook instead.');
      if(files.filter(f=>/\.json$/i.test(f.name)).length>1)throw Error('Select only one tournament configuration JSON file.');
      if(files.some(f=>!f.size||f.size>Toast.LIMITS.fileBytes))throw Error('Files must not be empty and must be smaller than 25 MB.');
      const inputs=[];let legacy=null;
      for(const file of files) {
        if(/\.json$/i.test(file.name))legacy=Toast.parseJson(await file.text());
        else inputs.push({name:file.name,bytes:new Uint8Array(await file.arrayBuffer())});
      }
      await new Promise(resolve=>setTimeout(resolve,0));
      if(current!==revision)return;
      const analyzed=Toast.analyze(inputs,legacy);
      if(current!==revision)return;
      result=analyzed;
      Object.assign(attemptReport,{tournament:result.config.INFO.tournament_long_name,usingDivisions:result.config.INFO.using_divisions,elapsedMs:result.elapsedMs,calculationChecks:result.validation.calculationChecks,errors:result.validation.errors,inputIssues:result.validation.inputIssues,calculationIssues:result.validation.calculationIssues,warnings:result.validation.warnings,missingAwards:result.validation.missing,outputsPrepared:Boolean(result.outputs),outputs:result.names,workbooks:result.books.map(b=>({filename:b.name,parseMs:Math.round(b.ms),tables:Object.keys(b.tables)}))});
      diagnostic=attemptReport;
      $('review').hidden=false;$('tournament').textContent=result.config.INFO.tournament_long_name;
      $('facts').replaceChildren();
      for(const value of [result.config.INFO.using_divisions?'Division '+result.config.INFO.ojs_files.map(e=>e.division.slice(1)).join(' & '):'Single division',result.validation.groups.reduce((n,g)=>n+g.roster.length,0)+' teams',result.validation.calculationChecks+' calculation checks',result.elapsedMs+' ms']){const span=document.createElement('span');span.className='fact';span.textContent=value;$('facts').append(span);}
      notice('errors',result.validation.errors);notice('warnings',result.validation.warnings);notice('omissions',result.validation.missing);
      $('errors').querySelector('h3').textContent=`${result.validation.errors.length} ${result.validation.errors.length===1?'issue':'issues'} to fix in the OJS`;
      $('error-next-step').textContent=result.validation.inputIssues.length?'Fix the score entries above first. Then recalculate and save in Excel, and click Check again. Dependent totals and rankings will be checked after the scores are valid.':'Recalculate and save in Excel after making corrections, then click Check again.';
      $('documents').hidden=!result.outputs;
      $('status').textContent=result.validation.errors.length?`${result.validation.errors.length} issue(s) need correction. See the review below.`:'Your workbooks have been checked. Review the tournament below.';
    } catch(error) {
      if(current!==revision)return;
      result=null;diagnostic=attemptReport;diagnostic.errors=[error.message];
      $('failure').hidden=false;$('failure-message').textContent=error.message;
      $('status').textContent='The selected files could not be processed.';
    } finally {
      if(current===revision){busy=false;$('dropzone').removeAttribute('aria-busy');updateGate();updateRefresh();}
    }
  }
  async function loadHandles(handles) {
    if(!handles.length)return;
    const current=++revision;clearView();busy=true;retainedHandles=handles;hasSelection=true;updateRefresh();updateGate();
    $('file-list').replaceChildren();for(const handle of handles){const li=document.createElement('li');li.textContent=handle.name;$('file-list').append(li);}
    $('status').textContent='Reading the latest saved files…';
    try {
      const files=await Promise.all(handles.map(handle=>handle.getFile()));
      if(current!==revision)return;
      await loadFiles(files,handles);
    } catch(error) {
      if(current!==revision)return;
      busy=false;diagnostic={version:Toast.VERSION,createdAt:new Date().toISOString(),files:handles.map(h=>({name:h.name})),errors:['Could not reopen the selected files. Save and close them in Excel, then try Check again. If a file was moved or access was revoked, use Choose files. ('+error.name+')']};
      $('failure').hidden=false;$('failure-message').textContent=diagnostic.errors[0];$('status').textContent='The latest files could not be read.';updateRefresh();updateGate();
    }
  }
  async function chooseFiles() {
    if(!window.showOpenFilePicker||pickerBlocked){$('files').click();return;}
    const current=revision;
    try {
      const handles=await window.showOpenFilePicker({id:'toast-ojs',multiple:true,...(retainedHandles?.length?{startIn:retainedHandles[0]}:{}),types:[{description:'OJS workbooks and tournament configuration',accept:{'application/vnd.ms-excel.sheet.macroEnabled.12':['.xlsm'],'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':['.xlsx'],'application/json':['.json']}}]});
      if(current===revision)await loadHandles(handles);
    } catch(error) {
      if(error.name==='AbortError'||current!==revision)return;
      // Some managed browsers expose the API but block local-file pickers.
      pickerBlocked=true;$('status').textContent='Use the file selector to choose your OJS files.';$('files').click();
    }
  }
  $('choose-files').onclick=chooseFiles;
  $('refresh').onclick=()=>retainedHandles?loadHandles(retainedHandles):chooseFiles();
  $('files').addEventListener('change',event=>{const files=Array.from(event.target.files);event.target.value='';if(files.length)loadFiles(files);});
  for(const type of ['dragenter','dragover'])$('dropzone').addEventListener(type,event=>{event.preventDefault();$('dropzone').classList.add('dragging');});
  $('dropzone').addEventListener('dragleave',()=>$('dropzone').classList.remove('dragging'));
  $('dropzone').addEventListener('drop',event=>{
    event.preventDefault();$('dropzone').classList.remove('dragging');
    const files=Array.from(event.dataTransfer.files),items=Array.from(event.dataTransfer.items||[]).filter(item=>item.kind==='file');
    // Capture handle promises during the drop event; the drag data store closes
    // after yielding. Never keep and rerun an old File snapshot after Excel saves.
    if(items.length&&items.every(item=>typeof item.getAsFileSystemHandle==='function')) {
      const current=++revision,handles=items.map(item=>item.getAsFileSystemHandle());
      clearView();busy=true;hasSelection=true;retainedHandles=null;updateGate();updateRefresh();$('status').textContent='Reading your selected files…';
      Promise.all(handles).then(h=>{if(current!==revision)return;return h.every(handle=>handle?.kind==='file')?loadHandles(h):loadFiles(files);}).catch(()=>{if(current===revision)loadFiles(files);});
    }else loadFiles(files);
  });
  window.addEventListener('dragover',event=>event.preventDefault());window.addEventListener('drop',event=>event.preventDefault());
  $('approve').addEventListener('input',updateGate);$('review-warnings').addEventListener('change',updateGate);
  for(const kind of ['script','summary']) {
    $('download-'+kind).onclick=()=>{if(permitted())download(result.names[kind],result.outputs[kind]);};
    $('preview-'+kind).onclick=()=>{if(permitted()){$('preview-title').textContent=kind==='script'?'Closing ceremony preview':'Tournament summary preview';$('preview-frame').srcdoc=result.outputs[kind];$('preview').hidden=false;$('preview').scrollIntoView({behavior:'smooth',block:'start'});}};
  }
  $('expand-preview').onclick=()=>{if(permitted()&&!$('preview').hidden)expandPreview(!$('preview').classList.contains('expanded'));};
  $('close-preview').onclick=()=>{closePreview();$('preview-script').focus();};
  $('report').onclick=report;$('failure-report').onclick=report;
  $('reset').onclick=()=>{revision++;busy=false;retainedHandles=null;hasSelection=false;clearView();updateRefresh();$('file-list').replaceChildren();$('files').value='';$('status').textContent='Choose your files to begin.';$('dropzone').removeAttribute('aria-busy');$('choose-files').focus();};
  $('version').textContent=Toast.VERSION;
  // The same entry point handles file picking, drag and drop, and integration tests.
  window.ToastApp=Object.freeze({loadFiles,getReport:()=>diagnostic?structuredClone(diagnostic):null,canDownload:permitted});
})();
