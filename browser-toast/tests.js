/* Runs only in the generated private test harness, never in TOAST.html. */
'use strict';
(async()=>{
  const results=[], parsed=[];
  const realTimeout=window.setTimeout.bind(window);
  // Blob download cleanup should not consume Chrome's virtual-time budget
  // between asynchronous File reads in the headless integration tests.
  window.setTimeout=(fn,ms,...args)=>realTimeout(fn,ms===30000?0:ms,...args);
  const progress=name=>{document.getElementById('test-results').textContent=JSON.stringify({running:name,passed:results.filter(r=>r.pass).length,failed:results.filter(r=>!r.pass).length,results});};
  const test=(name,fn)=>{try{const value=fn();if(value===false)throw Error('Assertion failed');results.push({name,pass:true});}catch(e){results.push({name,pass:false,error:e.stack||e.message});}};
  const asyncTest=async(name,fn)=>{progress(name);try{const value=await fn();if(value===false)throw Error('Assertion failed');results.push({name,pass:true});}catch(e){results.push({name,pass:false,error:e.stack||e.message});}};
  const assert=(condition,message='Assertion failed')=>{if(!condition)throw Error(message);};
  const rejects=(fn,pattern)=>{let error=null;try{fn();}catch(e){error=e;}assert(error,'Expected rejection');if(pattern)assert(pattern.test(error.message),error.message);};
  const decode=f=>({name:f.name,bytes:Uint8Array.from(atob(f.base64),c=>c.charCodeAt(0))});
  const clone=v=>structuredClone(v);
  const normalize=s=>s.replace(/\r\n/g,'\n').trim();
  const changed=(books,table,column,value,row=0,index=0)=>{const t=books[index].tables[table];t.rows[row][t.headers.indexOf(column)]=value;};
  for(const fixture of TEST_DATA.fixtures) {
    const inputs=fixture.files.map(decode), books=inputs.map(f=>Toast.readWorkbook(f.bytes,f.name));
    parsed.push({fixture,inputs,books,result:Toast.processBooks(books)});
    for(const book of books)for(const [name,expected] of Object.entries(fixture.reference.tables[book.name]))test(fixture.name+' / table '+name,()=>JSON.stringify(book.tables[name])===JSON.stringify(expected));
    const actual=parsed.at(-1).result;
    for(const kind of ['script','summary'])test(fixture.name+' / Python '+kind+' parity',()=>normalize(actual.outputs[kind])===normalize(fixture.reference.outputs[kind]));
    test(fixture.name+' / no validation errors',()=>actual.validation.errors.length===0);
    test(fixture.name+' / expected warnings',()=>actual.validation.warnings.length===fixture.reference.expected.warnings);
    test(fixture.name+' / expected omissions',()=>actual.validation.missing.length===fixture.reference.expected.missing);
  }
  const original=parsed[0], single=parsed[1], config=original.result.config;
  for(const [table,column] of [['RobotGameScores','Robot Game 1 Score'],['InnovationProjectResults','Iterate - Improvement'],['RobotDesignResults','Iterate - Improvements (CV)'],['CoreValuesResults','Gracious Professionalism 1']])test('Root cause: one missing '+table+' score produces one actionable error',()=>{
    const books=clone(original.books);changed(books,table,column,null);
    const r=Toast.validate(books,clone(config));
    assert(r.errors.length===1,JSON.stringify(r.errors));assert(r.inputIssues.length===1);assert(r.calculationIssues.length===0);
    const issue=r.inputIssues[0];assert(issue.cell.match(/^[A-Z]+\d+$/));assert(issue.sheet===books[0].tables[table].sheet);assert(issue.field===column);assert(issue.instruction.includes('is blank'));assert(!r.errors[0].includes('.xlsm'));
    const raw=books[0].tables[table], start=Number(raw.ref.match(/\d+/)[0]);assert(issue.cell.endsWith(String(start+1)));
  });
  test('Root cause: independent bad inputs are all shown',()=>{const b=clone(original.books);changed(b,'InnovationProjectResults','Iterate - Improvement',null);changed(b,'RobotDesignResults','Iterate - Improvements (CV)',null,1,1);const r=Toast.validate(b,clone(config));assert(r.errors.length===2&&r.inputIssues.length===2);});
  test('Root cause: independent other-division calculation issue remains visible',()=>{const b=clone(original.books);changed(b,'InnovationProjectResults','Iterate - Improvement',null);changed(b,'TournamentData',"Champion's Score",99999,0,1);const r=Toast.validate(b,clone(config));assert(r.errors.length===2);assert(r.calculationIssues.some(i=>i.column==="Champion's Score"));});
  test('Stale calculations grouped with full report details',()=>{const b=clone(original.books);changed(b,'TournamentData',"Champion's Score",99999);changed(b,'TournamentData',"Champion's Rank",99999);const r=Toast.validate(b,clone(config));assert(r.errors.length===1&&r.calculationIssues.length===2);assert(r.errors[0].includes('Recalculate and save'));});
  for(const scenario of TEST_DATA.oracle) {
    test('Python oracle: '+scenario.name,()=>{
      const books=clone(original.books);changed(books,scenario.table,scenario.column,scenario.value,scenario.row,scenario.book);
      const actual=Toast.validate(books,clone(config));
      assert(Boolean(actual.errors.length)===scenario.blocked,'Blocking outcome differs from Python: '+JSON.stringify(actual.errors));
      assert(Boolean(actual.missing.length)===scenario.missing,'Missing-award outcome differs from Python');
      assert(Boolean(actual.warnings.length)===scenario.warning,'Warning outcome differs from Python');
    });
  }
  const configError=(name,mutate)=>test('Configuration: '+name,()=>{const c=clone(config);mutate(c);rejects(()=>Toast.checkConfig(c));});
  configError('missing INFO',c=>delete c.INFO);
  configError('missing AWARDS',c=>delete c.AWARDS);
  configError('AWARDS is not a list',c=>c.AWARDS={});
  configError('missing name',c=>delete c.INFO.tournament_long_name);
  configError('nonboolean using_divisions',c=>c.INFO.using_divisions=1);
  configError('empty OJS list',c=>c.INFO.ojs_files=[]);
  configError('OJS list wrong type',c=>c.INFO.ojs_files='bad');
  configError('missing filename',c=>delete c.INFO.ojs_files[0].filename);
  configError('absolute filename',c=>c.INFO.ojs_files[0].filename='C:/bad.xlsm');
  configError('duplicate filename',c=>c.INFO.ojs_files[1].filename=c.INFO.ojs_files[0].filename);
  configError('duplicate division',c=>c.INFO.ojs_files[1].division='D1');
  configError('invalid division',c=>c.INFO.ojs_files[0].division='D3');
  configError('nondivision with two books',c=>c.INFO.using_divisions=false);
  configError('duplicate award ID',c=>c.AWARDS.push(clone(c.AWARDS[0])));
  configError('missing award ID',c=>delete c.AWARDS[0].ID);
  configError('missing award Name',c=>delete c.AWARDS[0].Name);
  configError('nonboolean DivAwd',c=>c.AWARDS[0].DivAwd='true');
  for(const value of [-1,1.5,true,'2',null])configError('invalid award allocation '+JSON.stringify(value),c=>{const a=c.AWARDS.find(a=>a.DivAwd);a.D1_count=value;});
  configError('missing script tag',c=>{const a=c.AWARDS.find(a=>a.DivAwd&&a.D1_count);delete a.ScriptTagD1;});
  configError('duplicate script tag',c=>{const a=c.AWARDS.filter(a=>a.DivAwd&&a.D1_count);a[1].ScriptTagD1=a[0].ScriptTagD1;});
  configError('missing labels',c=>{const a=c.AWARDS.find(a=>a.DivAwd&&a.ID!=='P_AWD_RG');a.Labels=[];});
  configError('empty label',c=>{const a=c.AWARDS.find(a=>a.DivAwd&&a.ID!=='P_AWD_RG');a.Labels[0]=' ';});
  configError('duplicate labels',c=>{const a=c.AWARDS.find(a=>a.DivAwd&&a.ID!=='P_AWD_RG');a.D1_count=2;a.Labels=['Winner','Winner'];});
  configError('shared robot game awards',c=>{const a=c.AWARDS.find(a=>a.ID==='P_AWD_RG');a.DivAwd=false;a.TournCount=1;a.ScriptTagNoDiv='P_AWD_RG';});
  for(const value of [0,-1,2.5,true,'530'])configError('invalid maximum score '+value,c=>c.INFO.robot_game_max_score=value);
  configError('nontext announcement',c=>c.INFO.ceremony.sponsor_acknowledgement={html:'bad'});
  test('JSON prototype properties rejected',()=>rejects(()=>Toast.parseJson('{"__proto__":{"polluted":true}}')));
  test('Malformed JSON rejected',()=>rejects(()=>Toast.parseJson('{')));
  test('No selected books rejected',()=>rejects(()=>Toast.configuration([],null)));
  test('Missing division rejected',()=>rejects(()=>Toast.configuration(original.books.slice(0,1),null)));
  test('Duplicate division rejected',()=>rejects(()=>Toast.configuration([original.books[0],original.books[0]],null)));
  test('Mixed tournaments rejected',()=>{const b=clone(original.books);b[1].embedded.identity='other';rejects(()=>Toast.configuration(b,null));});
  test('Mixed embedded and legacy rejected',()=>{const b=clone(original.books);b[1].embedded=null;rejects(()=>Toast.configuration(b,null));});
  test('Different config warns and D1 wins even in reverse order',()=>{const b=clone(original.books).reverse();b[0].embedded.config.INFO.ceremony.program_season_name='different';const r=Toast.configuration(b,null);assert(r.warnings.length===1);assert(r.config.INFO.ceremony.program_season_name===config.INFO.ceremony.program_season_name);});
  test('Config object key order does not create a false warning',()=>{const b=clone(original.books);b[1].embedded.config=Object.fromEntries(Object.entries(b[1].embedded.config).reverse());assert(Toast.configuration(b,null).warnings.length===0);});
  test('Renaming workbooks preserves identification',()=>{const b=clone(original.books);b.forEach((book,i)=>book.name='renamed'+i+'.xlsm');const r=Toast.configuration(b,null);assert(r.config.INFO.ojs_files.every(e=>e.filename.startsWith('renamed')));});
  test('Sole D2 supported when configured as sole division',()=>{const b=clone(original.books[1]);b.embedded.config.INFO.ojs_files=[b.embedded.config.INFO.ojs_files[1]];assert(Toast.configuration([b],null).config.INFO.ojs_files[0].division==='D2');});
  test('Legacy JSON fallback',()=>{const b=clone(original.books);b.forEach(book=>book.embedded=null);assert(Toast.processBooks(b,clone(config)).outputs.script);});
  test('Legacy JSON filename mismatch rejected',()=>{const b=clone(original.books);b.forEach(book=>book.embedded=null);b[0].name='wrong.xlsm';rejects(()=>Toast.configuration(b,clone(config)));});
  test('Legacy workbook without JSON rejected',()=>{const b=clone(original.books);b.forEach(book=>book.embedded=null);rejects(()=>Toast.configuration(b,null));});
  test('Custom legacy templates rejected explicitly',()=>{const b=clone(original.books);b.forEach(book=>book.embedded=null);const c=clone(config);c.INFO.script_template='custom.jinja';rejects(()=>Toast.configuration(b,c),/Custom legacy/);});
  for(const [name,[sheet,columns]] of Object.entries(Toast.TABLES)) {
    test('Missing table '+name,()=>{const b=clone(original.books);delete b[0].tables[name];assert(Toast.validate(b,clone(config)).errors.some(e=>e.includes('Missing named table')));});
    test('Wrong worksheet '+name,()=>{const b=clone(original.books);b[0].tables[name].sheet='Wrong';assert(Toast.validate(b,clone(config)).errors.some(e=>e.includes('expected worksheet')));});
    test('Duplicate header '+name,()=>{const b=clone(original.books);b[0].tables[name].headers.push(columns[0]);assert(Toast.validate(b,clone(config)).errors.some(e=>e.includes('duplicate column')));});
    for(const column of columns)test('Missing column '+name+'.'+column,()=>{const b=clone(original.books),t=b[0].tables[name],i=t.headers.indexOf(column);t.headers.splice(i,1);t.rows.forEach(r=>r.splice(i,1));assert(Toast.validate(b,clone(config)).errors.length>0);});
  }
  for(const value of [true,0,-1,1.5,null,'bad'])test('Invalid team identity '+value,()=>{const b=clone(original.books);changed(b,'OfficialTeamList','Team #',value);assert(Toast.validate(b,clone(config)).errors.length>0);});
  test('Duplicate roster team',()=>{const b=clone(original.books),t=b[0].tables.OfficialTeamList;changed(b,'OfficialTeamList','Team #',t.rows[0][t.headers.indexOf('Team #')],1);assert(Toast.validate(b,clone(config)).errors.length>0);});
  test('Cross-division duplicate team',()=>{const b=clone(original.books),id=Toast.processBooks(b).validation.groups[0].roster[0]['Team #'];for(const t of Object.values(b[1].tables)){const i=t.headers.indexOf('Team #');if(i>=0)t.rows[0][i]=id;}assert(Toast.validate(b,clone(config)).errors.some(e=>e.includes('more than one division')));});
  test('Reordered table rows are aligned by team identity',()=>{const b=clone(original.books);for(const t of Object.values(b[0].tables))if(t.headers.includes('Team #')&&t!==b[0].tables.OfficialTeamList)t.rows.reverse();assert(Toast.validate(b,clone(config)).errors.length===0);});
  test('Minimum rank ties',()=>JSON.stringify(Toast.ranks([10,10,5]))==='[1,1,3]');
  test('Ascending rank ties',()=>JSON.stringify(Toast.ranks([2,2,4],true))==='[1,1,3]');
  function boundaryCase(score,robot,maximum=530) {
    const books=clone(original.books),cfg=clone(config);cfg.INFO.robot_game_max_score=maximum;
    for(const award of cfg.AWARDS)for(const key of ['D1_count','D2_count','TournCount'])award[key]=0;
    for(const entry of cfg.INFO.ojs_files)cfg.INFO['advancing_count_'+entry.division.toLowerCase()]=0;
    for(const book of books) {
      const set=(table,column,value)=>{const t=book.tables[table],i=t.headers.indexOf(column);assert(i>=0,column);for(const row of t.rows)row[i]=value;};
      for(const name of ['InnovationProjectResults','RobotDesignResults'])for(const column of Toast.TABLES[name][1].slice(2,12))set(name,column,score);
      for(let i=1;i<=3;i++){set('RobotGameScores',`Robot Game ${i} Score`,robot);set('CoreValuesResults',`Gracious Professionalism ${i}`,score);}
      // Independent boundary expectations: ten rubric inputs per area, five
      // CV inputs per area, three GP scores, and four tied area ranks of 1.
      for(const [table,column,value] of [['InnovationProjectResults','Innovation Project Score',10*score],['InnovationProjectResults','Innovation Project Rank',1],['RobotDesignResults','Robot Design Score',10*score],['RobotDesignResults','Robot Design Rank',1],['CoreValuesResults','Gracious Professionalism Total',3*score],['CoreValuesResults','Gracious Professionalism Score',3*score],['CoreValuesResults','Core Values Score',13*score],['CoreValuesResults','Core Values Rank',1],['TournamentData','Max Robot Game Score',robot+robot*.0001+robot*.0000001],['TournamentData','Robot Game Rank',1],['TournamentData','Innovation Project Rank',1],['TournamentData','Robot Design Rank',1],['TournamentData','Core Values Rank',1],['TournamentData',"Champion's Score",4],['TournamentData',"Champion's Rank",1],['TournamentData','Advance?',null],['TournamentData','Award',null]])set(table,column,value);
    }
    return {books,config:cfg,validation:Toast.validate(books,cfg)};
  }
  for(const [score,robot,max] of [[0,0,530],[4,530,530],[4,600,600]])test(`Valid boundaries: rubric ${score}, robot ${robot}, maximum ${max}`,()=>{const r=boundaryCase(score,robot,max);assert(r.validation.errors.length===0,JSON.stringify(r.validation.errors));assert(r.validation.missing.length===0);const outputs=Toast.renderOutputs(r.config,r.validation);assert(!outputs.summary.includes('<h2>Advancing Teams</h2>'));});
  test('Tied awarded robot ranks block generation',()=>{const r=boundaryCase(4,530);r.config.AWARDS.find(a=>a.ID==='P_AWD_RG').D1_count=1;assert(Toast.validate(r.books,r.config).errors.some(e=>e.includes('ranks tied')));});
  for(const [value,valid] of [[true,false],[null,false],['',false],['bad',false],['2',true],[0,true],[530,true]])test('Strict numeric parsing '+JSON.stringify(value),()=>Number.isFinite(Toast.numeric(value))===valid);
  test('Unicode and HTML team names escape safely',()=>{const b=clone(single.books);for(const t of Object.values(b[0].tables)){const i=t.headers.indexOf('Team Name');if(i>=0)t.rows[0][i]='Équipe <script>BAD</script> & Robotics';}const r=Toast.processBooks(b);assert(r.outputs.script.includes('Équipe &lt;script&gt;BAD&lt;/script&gt; &amp; Robotics'));assert(!r.outputs.script.includes('<script>BAD'));});
  test('Tournament title is escaped',()=>{const b=clone(single.books);b[0].embedded.config.INFO.tournament_long_name='<img src=x onerror=alert(1)>';assert(!Toast.processBooks(b).outputs.script.includes('<img src=x'));});
  test('Missing template tag blocks both outputs',()=>{const b=clone(single.books);const a=b[0].embedded.config.AWARDS.find(a=>a.TournCount&&a.ID==='P_AWD_RG');a.ScriptTagNoDiv='P_AWD_WRONG';const r=Toast.processBooks(b);assert(!r.outputs&&r.validation.errors.some(e=>e.includes('template')));});
  test('Combined filenames remove only trailing division',()=>Toast.outputNames(config).script.endsWith('Dunford-closing-ceremony.html'));
  test('Single filename is preserved',()=>Toast.outputNames(single.result.config).script==='single-division-test-closing-ceremony.html');
  function rewrite(input,edit){const zip=fflate.unzipSync(input.bytes);edit(zip);return fflate.zipSync(zip);}
  function sheetPath(zip,name) {
    const doc=new DOMParser().parseFromString(fflate.strFromU8(zip['xl/workbook.xml']),'application/xml');
    const sheet=Array.from(doc.getElementsByTagNameNS('*','sheet')).find(n=>n.getAttribute('name')===name);
    const rel=new DOMParser().parseFromString(fflate.strFromU8(zip['xl/_rels/workbook.xml.rels']),'application/xml');
    const id=sheet.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships','id');
    const target=Array.from(rel.getElementsByTagNameNS('*','Relationship')).find(n=>n.getAttribute('Id')===id).getAttribute('Target');
    return target.startsWith('/')?target.slice(1):'xl/'+target;
  }
  function replaceCell(zip,sheet,address,value) {
    const path=sheetPath(zip,sheet),doc=new DOMParser().parseFromString(fflate.strFromU8(zip[path]),'application/xml');
    let cell=Array.from(doc.getElementsByTagNameNS('*','c')).find(n=>n.getAttribute('r')===address);
    if(value===undefined){cell?.remove();}
    else {
      if(!cell){const number=address.match(/\d+/)[0];let row=Array.from(doc.getElementsByTagNameNS('*','row')).find(n=>n.getAttribute('r')===number);if(!row){row=doc.createElementNS(doc.documentElement.namespaceURI,'row');row.setAttribute('r',number);doc.getElementsByTagNameNS('*','sheetData')[0].append(row);}cell=doc.createElementNS(doc.documentElement.namespaceURI,'c');cell.setAttribute('r',address);row.append(cell);}
      cell.replaceChildren();cell.setAttribute('t',typeof value==='string'?'inlineStr':'n');
      const child=doc.createElementNS(doc.documentElement.namespaceURI,typeof value==='string'?'is':'v');
      if(typeof value==='string'){const t=doc.createElementNS(doc.documentElement.namespaceURI,'t');t.textContent=value;child.append(t);}else child.textContent=String(value);
      cell.append(child);
    }
    zip[path]=fflate.strToU8(new XMLSerializer().serializeToString(doc));
  }
  test('Truncated ZIP rejected',()=>rejects(()=>Toast.readWorkbook(original.inputs[0].bytes.slice(0,40),'broken.xlsm')));
  test('Nonworkbook ZIP rejected',()=>rejects(()=>Toast.readWorkbook(fflate.zipSync({'hello.txt':new TextEncoder().encode('hello')}),'bad.xlsm')));
  test('Malformed workbook XML rejected',()=>rejects(()=>Toast.readWorkbook(rewrite(original.inputs[0],z=>z['xl/workbook.xml']=fflate.strToU8('<broken>')),'bad.xlsm')));
  test('Unsupported config version rejected',()=>{const bytes=rewrite(original.inputs[0],z=>replaceCell(z,'_TOAST_Config','B1',999));rejects(()=>Toast.readWorkbook(bytes,'bad.xlsm'));});
  test('Empty configuration chunk rejected',()=>{const bytes=rewrite(original.inputs[0],z=>replaceCell(z,'_TOAST_Config','A5',undefined));rejects(()=>Toast.readWorkbook(bytes,'bad.xlsm'));});
  for(const value of [0,-1,1001,2.5,'bad'])test('Invalid configuration chunk count '+value,()=>{const bytes=rewrite(original.inputs[0],z=>replaceCell(z,'_TOAST_Config','B4',value));rejects(()=>Toast.readWorkbook(bytes,'bad.xlsm'));});
  test('Invalid embedded division rejected',()=>rejects(()=>Toast.readWorkbook(rewrite(original.inputs[0],z=>replaceCell(z,'_TOAST_Config','B2','D3')),'bad.xlsm')));
  test('Missing embedded identity rejected',()=>rejects(()=>Toast.readWorkbook(rewrite(original.inputs[0],z=>replaceCell(z,'_TOAST_Config','B3',undefined)),'bad.xlsm')));
  test('Malformed embedded JSON rejected',()=>rejects(()=>Toast.readWorkbook(rewrite(original.inputs[0],z=>replaceCell(z,'_TOAST_Config','A5','{')),'bad.xlsm')));
  test('Missing configuration marker rejected',()=>rejects(()=>Toast.readWorkbook(rewrite(original.inputs[0],z=>replaceCell(z,'_TOAST_Config','A1','WRONG')),'bad.xlsm')));
  test('Multi-chunk Unicode config preserves boundary spaces',()=>{
    const cfg=clone(original.books[0].embedded.config);cfg.INFO.ceremony.sponsor_acknowledgement='Équipe A & B with space';const payload=JSON.stringify(cfg);const at=payload.indexOf('with space')+5;
    const bytes=rewrite(original.inputs[0],z=>{replaceCell(z,'_TOAST_Config','B4',2);replaceCell(z,'_TOAST_Config','A5',payload.slice(0,at));replaceCell(z,'_TOAST_Config','A6',payload.slice(at));});
    assert(Toast.readWorkbook(bytes,'test.xlsm').embedded.config.INFO.ceremony.sponsor_acknowledgement===cfg.INFO.ceremony.sponsor_acknowledgement);
  });
  test('Oversized file rejected',()=>rejects(()=>Toast.readWorkbook(new Uint8Array(Toast.LIMITS.fileBytes+1),'large.xlsm')));
  test('Excessive expanded ZIP rejected',()=>{const big=fflate.zipSync({'huge.xml':new Uint8Array(Toast.LIMITS.unpackedBytes+1)});rejects(()=>Toast.readWorkbook(big,'large.xlsm'));});
  test('Pathological table range rejected',()=>{const bytes=rewrite(original.inputs[0],z=>{const k=Object.keys(z).find(k=>k.startsWith('xl/tables/'));z[k]=fflate.strToU8(fflate.strFromU8(z[k]).replace(/ref="[^"]+"/,'ref="A1:XFD1048576"'));});rejects(()=>Toast.readWorkbook(bytes,'huge.xlsm'));});
  const blobs=[], downloads=[];
  const create=URL.createObjectURL.bind(URL);URL.createObjectURL=blob=>{blobs.push(blob);return create(blob);};
  document.addEventListener('click',event=>{const a=event.target.closest('a[download]');if(a){event.preventDefault();downloads.push(a.download);}},true);
  const files=inputs=>inputs.map(f=>new File([f.bytes],f.name,{lastModified:1700000000000}));
  const load=async inputs=>{await ToastApp.loadFiles(files(inputs));};
  const uiReport=()=>ToastApp.getReport();
  await asyncTest('UI: file input integration',async()=>{const dt=new DataTransfer();files(original.inputs).forEach(f=>dt.items.add(f));const input=document.getElementById('files');input.files=dt.files;input.dispatchEvent(new Event('change',{bubbles:true}));for(let i=0;i<200&&!uiReport()?.tournament;i++)await new Promise(r=>setTimeout(r,10));assert(ToastApp.canDownload());});
  await asyncTest('UI: drop integration',async()=>{const dt=new DataTransfer();files(original.inputs).forEach(f=>dt.items.add(f));document.getElementById('dropzone').dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt}));for(let i=0;i<200&&!uiReport()?.tournament;i++)await new Promise(r=>setTimeout(r,10));assert(ToastApp.canDownload());});
  await asyncTest('UI: both actual download buttons',async()=>{document.getElementById('download-script').click();assert(downloads.at(-1)===original.result.names.script);assert(normalize(await blobs.at(-1).text())===normalize(original.result.outputs.script));document.getElementById('download-summary').click();assert(downloads.at(-1)===original.result.names.summary);assert(normalize(await blobs.at(-1).text())===normalize(original.result.outputs.summary));});
  await asyncTest('UI: sandboxed preview and close',async()=>{document.getElementById('preview-script').click();const frame=document.getElementById('preview-frame');assert(frame.getAttribute('sandbox')==='');assert(frame.srcdoc===original.result.outputs.script);document.getElementById('close-preview').click();assert(!frame.hasAttribute('srcdoc'));});
  await asyncTest('UI: expanded ceremony fills window and returns without losing script',async()=>{
    document.getElementById('preview-script').click();const frame=document.getElementById('preview-frame'),before=frame.srcdoc;
    document.getElementById('expand-preview').click();const preview=document.getElementById('preview');assert(preview.classList.contains('expanded'));assert(getComputedStyle(preview).position==='fixed');assert(document.body.style.overflow==='hidden');assert(document.getElementById('expand-preview').getAttribute('aria-pressed')==='true');assert(frame.srcdoc===before);assert(frame.getAttribute('sandbox')==='');
    document.getElementById('expand-preview').click();assert(!preview.classList.contains('expanded'));assert(document.body.style.overflow!=='hidden');assert(frame.srcdoc===before);document.getElementById('close-preview').click();
  });
  await asyncTest('UI: summary expands and closing restores scrolling',async()=>{
    document.getElementById('preview-summary').click();document.getElementById('expand-preview').click();assert(document.getElementById('preview-frame').srcdoc===original.result.outputs.summary);document.getElementById('close-preview').click();assert(document.getElementById('preview').hidden);assert(!document.getElementById('preview').classList.contains('expanded'));assert(document.body.style.overflow!=='hidden');
  });
  await asyncTest('UI: replacing files closes expanded preview immediately',async()=>{
    document.getElementById('preview-script').click();document.getElementById('expand-preview').click();const pending=ToastApp.loadFiles([new File(['bad'],'bad.xlsm')]);assert(!document.getElementById('preview').classList.contains('expanded'));assert(document.body.style.overflow!=='hidden');assert(!document.getElementById('preview-frame').hasAttribute('srcdoc'));await pending;await load(original.inputs);
  });
  await asyncTest('UI: expansion cannot bypass validation',async()=>{
    await ToastApp.loadFiles([new File(['bad'],'bad.xlsm')]);document.getElementById('expand-preview').click();assert(!document.getElementById('preview').classList.contains('expanded'));await load(original.inputs);
  });
  await asyncTest('UI: latest report after file change',async()=>{await load(single.inputs);document.getElementById('report').click();const report=JSON.parse(await blobs.at(-1).text());assert(report.tournament===single.result.config.INFO.tournament_long_name);assert(report.files.length===1);assert(!('fixtures' in report));});
  const writeAwardOmission=()=>rewrite(single.inputs[0],z=>{
    const table=single.books[0].tables.TournamentData,col=table.headers.indexOf('Award');
    // Find an allocated ordinary award in the first data row; replace that
    // worksheet cell with a blank while preserving every other saved value.
    const row=table.rows.findIndex(r=>r[col]&&!(single.result.config.AWARDS.find(a=>a.ID==='J_AWD_Judges')?.Labels||[]).includes(r[col]));
    const address=(()=>{let n=col+1,s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s+(row+3);})();
    for(const k of Object.keys(z))if(k.startsWith('xl/worksheets/')&&k.endsWith('.xml')){let s=fflate.strFromU8(z[k]);if(s.includes('name="')||!s.includes('tablePart'))continue;/* handled below via sheet name relationship */}
    const workbook=new DOMParser().parseFromString(fflate.strFromU8(z['xl/workbook.xml']),'application/xml');
    const sheet=Array.from(workbook.getElementsByTagName('sheet')).find(n=>n.getAttribute('name')==='Results and Rankings');
    const rel=new DOMParser().parseFromString(fflate.strFromU8(z['xl/_rels/workbook.xml.rels']),'application/xml');
    const target=Array.from(rel.getElementsByTagName('Relationship')).find(n=>n.getAttribute('Id')===sheet.getAttribute('r:id')).getAttribute('Target');
    const path=target.startsWith('/')?target.slice(1):'xl/'+target;
    const s=fflate.strFromU8(z[path]);z[path]=fflate.strToU8(s.replace(new RegExp('<c\\b[^>]*r="'+address+'"[^>]*>[\\s\\S]*?<\\/c>'),''));
  });
  await asyncTest('UI: omission exact YES, preview gate, and approval reset',async()=>{
    const input={name:single.inputs[0].name,bytes:writeAwardOmission()};await load([input]);
    assert(uiReport().missingAwards.length>0,'Mutation did not remove an allocated award');assert(!ToastApp.canDownload());
    const approval=document.getElementById('approve');approval.value='yes';approval.dispatchEvent(new Event('input'));assert(!ToastApp.canDownload());
    approval.value='YES';approval.dispatchEvent(new Event('input'));assert(ToastApp.canDownload());document.getElementById('download-script').click();assert((await blobs.at(-1).text()).includes('NONE'));
    await load([input]);assert(approval.value==='');assert(!ToastApp.canDownload());
  });
  await asyncTest('UI: warning acknowledgement gate',async()=>{
    const warningConfig=clone(original.books[1].embedded.config);warningConfig.INFO.ceremony.program_season_name='Changed';
    const warningInputs=original.inputs.map((f,i)=>i?{name:f.name,bytes:rewrite(f,z=>replaceCell(z,'_TOAST_Config','A5',JSON.stringify(warningConfig)))}:f);
    await load(warningInputs);assert(uiReport().warnings.length>0);assert(!ToastApp.canDownload());
    document.getElementById('review-warnings').checked=true;document.getElementById('review-warnings').dispatchEvent(new Event('change'));assert(ToastApp.canDownload());
    await load(warningInputs);assert(!document.getElementById('review-warnings').checked);assert(!ToastApp.canDownload());
  });
  for(const [name,input] of [['empty file',new File([],'empty.xlsm')],['unsupported type',new File(['x'],'bad.txt')],['invalid zip',new File(['not a zip'],'bad.xlsm')],['Excel lock file',new File(['x'],'~$test.xlsm')],['invalid JSON',new File(['{'],'config.json')]])await asyncTest('UI: '+name+' clears previous outputs',async()=>{await load(original.inputs);await ToastApp.loadFiles([input]);assert(!ToastApp.canDownload());assert(document.getElementById('download-script').disabled);assert(!document.getElementById('failure').hidden);document.getElementById('failure-report').click();const report=JSON.parse(await blobs.at(-1).text());assert(report.errors.length>0);assert(report.files[0].name===input.name);});
  await asyncTest('UI: multiple JSON configurations rejected',async()=>{await ToastApp.loadFiles([new File(['{}'],'a.json'),new File(['{}'],'b.json')]);assert(!ToastApp.canDownload());assert(uiReport().errors[0].includes('one tournament configuration'));});
  await asyncTest('UI: failed replacement immediately removes preview',async()=>{await load(original.inputs);document.getElementById('preview-script').click();const pending=ToastApp.loadFiles([new File(['bad'],'bad.xlsm')]);assert(!document.getElementById('preview-frame').hasAttribute('srcdoc'));await pending;});
  await asyncTest('UI: newer selection wins overlapping reads',async()=>{const slow=new File([original.inputs[0].bytes],'slow.xlsm');slow.arrayBuffer=()=>new Promise(resolve=>setTimeout(()=>resolve(original.inputs[0].bytes.buffer),40));const old=ToastApp.loadFiles([slow]);await load(single.inputs);await old;assert(uiReport().tournament===single.result.config.INFO.tournament_long_name);assert(ToastApp.canDownload());});
  await asyncTest('UI: a deleted judging score shows one location instead of a cascade',async()=>{
    const t=original.books[1].tables.InnovationProjectResults,column=t.headers.indexOf('Iterate - Improvement');
    const row=Math.max(0,t.rows.findIndex(r=>r[t.headers.indexOf('Team #')]===72423));
    const cell=String.fromCharCode(65+column)+(Number(t.ref.match(/\d+/)[0])+1+row);
    const inputs=original.inputs.map((f,i)=>i?{name:f.name,bytes:rewrite(f,z=>replaceCell(z,'Innovation Project Input',cell,undefined))}:f);
    await load(inputs);const report=uiReport();assert(report.errors.length===1);assert(report.inputIssues[0].cell===cell);assert(report.calculationIssues.length===0);
    assert(document.querySelectorAll('#errors li').length===1);assert(document.getElementById('errors').textContent.includes('Division 2'));assert(document.getElementById('errors').textContent.includes('Cell '+cell));assert(!document.getElementById('errors').textContent.includes("Champion's"));assert(!ToastApp.canDownload());
    document.getElementById('report').click();assert(JSON.parse(await blobs.at(-1).text()).inputIssues[0].field==='Iterate - Improvement');
  });
  const waitFor=async fn=>{for(let i=0;i<500;i++){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('UI operation did not finish');};
  const picker=window.showOpenFilePicker;
  await asyncTest('UI: Check again reopens every handle and sees saved corrections',async()=>{
    let selected=original.inputs,reads=0;
    const t=original.books[1].tables.InnovationProjectResults,col=t.headers.indexOf('Iterate - Improvement'),cell=String.fromCharCode(65+col)+(Number(t.ref.match(/\d+/)[0])+1);
    selected=original.inputs.map((f,i)=>i?{name:f.name,bytes:rewrite(f,z=>replaceCell(z,'Innovation Project Input',cell,undefined))}:f);
    const handles=original.inputs.map((f,i)=>({kind:'file',name:f.name,getFile:async()=>{reads++;return files(selected)[i];}}));
    window.showOpenFilePicker=async()=>handles;
    document.getElementById('choose-files').click();await waitFor(()=>reads===2&&uiReport()?.inputIssues?.length===1&&!document.getElementById('refresh').disabled);
    assert(reads===2);assert(!ToastApp.canDownload());assert(document.getElementById('refresh-help').textContent.includes('latest files'));
    selected=original.inputs;document.getElementById('refresh').click();assert(!ToastApp.canDownload());assert(document.getElementById('refresh').disabled);
    await waitFor(()=>uiReport()?.errors?.length===0&&ToastApp.canDownload());assert(reads===4);assert(uiReport().inputIssues.length===0);
    window.showOpenFilePicker=picker;
  });
  await asyncTest('UI: refresh read failure clears old downloads and supports retry',async()=>{
    let fail=false;
    window.showOpenFilePicker=async()=>original.inputs.map(f=>({kind:'file',name:f.name,getFile:async()=>{if(fail)throw new DOMException('Missing','NotFoundError');return files([f])[0];}}));
    document.getElementById('choose-files').click();await new Promise(r=>setTimeout(r,0));await waitFor(()=>ToastApp.canDownload());fail=true;
    document.getElementById('refresh').click();assert(!ToastApp.canDownload());await waitFor(()=>!document.getElementById('failure').hidden);
    assert(uiReport().errors[0].includes('Choose files'));assert(!document.getElementById('refresh').disabled);
    fail=false;document.getElementById('refresh').click();await waitFor(()=>ToastApp.canDownload());window.showOpenFilePicker=picker;
  });
  await asyncTest('UI: canceling Choose files preserves current selection',async()=>{
    const previous=uiReport().createdAt;window.showOpenFilePicker=async()=>{throw new DOMException('Canceled','AbortError');};
    document.getElementById('choose-files').click();await new Promise(r=>setTimeout(r,10));assert(uiReport().createdAt===previous);assert(ToastApp.canDownload());window.showOpenFilePicker=picker;
  });
  await asyncTest('UI: snapshot-only refresh asks for a new selection',async()=>{
    await load(original.inputs);assert(document.getElementById('refresh-help').textContent.includes('select the saved files'));
    let picks=0;window.showOpenFilePicker=async()=>{picks++;throw new DOMException('Canceled','AbortError');};document.getElementById('refresh').click();await new Promise(r=>setTimeout(r,10));assert(picks===1);window.showOpenFilePicker=picker;
  });
  await asyncTest('UI: refresh clears omission approvals',async()=>{
    const selected=[{name:single.inputs[0].name,bytes:writeAwardOmission()}];
    window.showOpenFilePicker=async()=>selected.map(f=>({kind:'file',name:f.name,getFile:async()=>files([f])[0]}));
    document.getElementById('choose-files').click();await waitFor(()=>uiReport()?.missingAwards?.length>0&&!document.getElementById('refresh').disabled);
    const approval=document.getElementById('approve');approval.value='YES';approval.dispatchEvent(new Event('input'));assert(ToastApp.canDownload());
    document.getElementById('refresh').click();assert(approval.value==='');await waitFor(()=>!document.getElementById('refresh').disabled);assert(!ToastApp.canDownload());window.showOpenFilePicker=picker;
  });
  await asyncTest('UI: reset removes state and approvals',async()=>{document.getElementById('reset').click();assert(!ToastApp.canDownload());assert(ToastApp.getReport()===null);assert(document.getElementById('review').hidden);assert(document.getElementById('refresh').hidden);});
  const summary={version:Toast.VERSION,browser:navigator.userAgent,protocol:location.protocol,passed:results.filter(r=>r.pass).length,failed:results.filter(r=>!r.pass).length,total:results.length,results};
  window.browserToastTestResults=summary;document.getElementById('test-results').textContent=JSON.stringify(summary,null,2);document.documentElement.dataset.testResult=summary.failed?'fail':'pass';
  document.title=(summary.failed?'FAIL':'PASS')+' — '+summary.passed+'/'+summary.total+' TOAST tests';
})().catch(error=>{document.getElementById('test-results').textContent=JSON.stringify({failed:1,fatal:error.stack||error.message});document.documentElement.dataset.testResult='fail';});
