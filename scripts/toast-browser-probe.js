/* Feasibility probe, not a replacement for TOAST. No network requests. */
'use strict';
const $ = id => document.getElementById(id);
const textOf = (node, name) => node.getElementsByTagNameNS('*', name)[0]?.textContent ?? '';
const elements = (node, name) => Array.from(node.getElementsByTagNameNS('*', name));
const xml = bytes => {
  const doc = new DOMParser().parseFromString(fflate.strFromU8(bytes), 'application/xml');
  if (elements(doc, 'parsererror').length) throw Error('Invalid workbook XML');
  return doc;
};
const resolvePart = (base, target) => {
  const parts = target.startsWith('/') ? [] : base.split('/').slice(0, -1);
  for (const p of target.split('/')) { if (p === '..') parts.pop(); else if (p && p !== '.') parts.push(p); }
  return parts.join('/');
};
function relationships(zip, part) {
  const bits = part.split('/'), name = bits.pop();
  const key = [...bits, '_rels', name + '.rels'].join('/');
  return new Map(zip[key] ? elements(xml(zip[key]), 'Relationship').map(r => [r.getAttribute('Id'), resolvePart(part, r.getAttribute('Target'))]) : []);
}
function readWorkbook(bytes, name) {
  const start = performance.now(), zip = fflate.unzipSync(bytes);
  if (!zip['xl/workbook.xml']) throw Error('Not an unencrypted Open XML workbook');
  const strings = zip['xl/sharedStrings.xml'] ? elements(xml(zip['xl/sharedStrings.xml']), 'si').map(n => elements(n, 't').map(t => t.textContent).join('')) : [];
  const rels = relationships(zip, 'xl/workbook.xml'), sheets = {}, tables = {};
  let formulaCount = 0, missingCaches = 0;
  for (const sheet of elements(xml(zip['xl/workbook.xml']), 'sheet')) {
    const path = rels.get(sheet.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships', 'id'));
    if (!zip[path]) throw Error('Missing worksheet part: ' + path);
    const doc = xml(zip[path]), cells = {};
    for (const c of elements(doc, 'c')) {
      const type = c.getAttribute('t'), v = textOf(c, 'v'), formula = elements(c, 'f').length > 0;
      if (formula) { formulaCount++; if (!elements(c, 'v').length || v === '') missingCaches++; }
      let value = null;
      if (type === 's') value = strings[Number(v)];
      else if (type === 'inlineStr') value = elements(c, 't').map(t => t.textContent).join('');
      else if (type === 'b') value = v === '1';
      else if (type === 'e') value = v;
      else if (type === 'str') value = v || null;
      else if (v !== '') value = Number(v);
      if (typeof value === 'string') value = value.trim() || null;
      cells[c.getAttribute('r')] = value;
    }
    const sheetName = sheet.getAttribute('name');
    sheets[sheetName] = {cells, state: sheet.getAttribute('state') || 'visible'};
    const sheetRels = relationships(zip, path);
    for (const part of elements(doc, 'tablePart')) {
      const tablePath = sheetRels.get(part.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships', 'id'));
      if (!zip[tablePath]) throw Error('Missing table definition');
      const table = xml(zip[tablePath]).documentElement, ref = table.getAttribute('ref');
      const [a, b] = ref.split(':'), decode = s => {
        const m = /^([A-Z]+)(\d+)$/.exec(s); if (!m) throw Error('Invalid table range');
        return [Array.from(m[1]).reduce((n, c) => n * 26 + c.charCodeAt(0) - 64, 0), Number(m[2])];
      };
      const [c0, r0] = decode(a), [c1, r1] = decode(b || a);
      const column = n => { let s = ''; while (n) { n--; s = String.fromCharCode(65 + n % 26) + s; n = Math.floor(n / 26); } return s; };
      const rows = [];
      for (let r = r0; r <= r1; r++) rows.push(Array.from({length: c1 - c0 + 1}, (_, i) => cells[column(c0 + i) + r] ?? null));
      const headers = rows.shift().map(String);
      if (new Set(headers).size !== headers.length) throw Error('Duplicate headers in ' + table.getAttribute('name'));
      tables[table.getAttribute('name')] = {sheet: sheetName, ref, headers, rows};
    }
  }
  const hidden = sheets._TOAST_Config;
  let embedded = null;
  if (hidden) {
    const c = hidden.cells;
    if (c.A1 !== 'TOAST_CONFIG' || c.B1 !== 1 || !Number.isInteger(c.B4) || c.B4 < 1 || c.B4 > 1000) throw Error('Invalid embedded configuration');
    let payload = '';
    for (let i = 0; i < c.B4; i++) { if (typeof c['A' + (i + 5)] !== 'string') throw Error('Missing configuration chunk'); payload += c['A' + (i + 5)]; }
    embedded = {division: c.B2 || '', identity: c.B3, config: JSON.parse(payload)};
    if (!['', 'D1', 'D2'].includes(embedded.division)) throw Error('Invalid division');
  }
  return {name, tables, sheets, embedded, formulaCount, missingCaches, ms: performance.now() - start};
}
const numeric = v => (typeof v === 'number' || typeof v === 'string' && v.trim() !== '') && Number.isFinite(Number(v)) ? Number(v) : NaN;
const ranks = (values, ascending = false) => values.map(v => 1 + values.filter(x => ascending ? x < v : x > v).length);
const close = (a, b) => Number.isFinite(numeric(a)) && Math.abs(numeric(a) - b) <= Math.max(1e-8, 1e-9 * Math.max(Math.abs(numeric(a)), Math.abs(b)));
function rowsOf(book, name) {
  const t = book.tables[name]; if (!t) throw Error('Missing named table: ' + name);
  return t.rows.map(row => Object.fromEntries(t.headers.map((h, i) => [h, row[i]])));
}
function configuration(books, legacy) {
  const records = books.filter(b => b.embedded).sort((a, b) => a.embedded.division.localeCompare(b.embedded.division));
  if (!records.length) { if (!legacy) throw Error('No embedded configuration. Select legacy tournament_config.json as well.'); return {config: structuredClone(legacy), warnings: []}; }
  if (records.length !== books.length) throw Error('Selected files mix embedded and legacy workbooks');
  const divisions = records.map(b => b.embedded.division), warnings = [];
  if (new Set(divisions).size !== records.length || (divisions.includes('') && records.length > 1)) throw Error('Duplicate or mixed division identities');
  if (new Set(records.map(b => b.embedded.identity)).size !== 1) throw Error('Files belong to different tournaments');
  const config = structuredClone(records[0].embedded.config), info = config.INFO;
  if (info.using_divisions !== Boolean(divisions[0])) throw Error('Division metadata disagrees with configuration');
  if (JSON.stringify(info.ojs_files.map(e => e.division).sort()) !== JSON.stringify([...divisions].sort())) throw Error('Missing or unexpected division');
  for (const b of records.slice(1)) if (JSON.stringify(b.embedded.config) !== JSON.stringify(records[0].embedded.config)) warnings.push('Configuration differs; using ' + records[0].name);
  info.ojs_files = records.map(b => ({division: b.embedded.division, filename: b.name}));
  return {config, warnings};
}
function validate(books, config) {
  const errors = [], warnings = [], missing = [], groups = [], allIds = new Set(); let calculationChecks = 0;
  const info = config.INFO, maximum = info.robot_game_max_score ?? 530;
  if (typeof info.using_divisions !== 'boolean' || !Array.isArray(config.AWARDS) || !Number.isInteger(maximum) || maximum <= 0) throw Error('Invalid configuration schema');
  for (const entry of info.ojs_files) {
    const book = books.find(b => b.name === entry.filename); if (!book) throw Error('Missing workbook: ' + entry.filename);
    try {
      const roster = rowsOf(book, 'OfficialTeamList'), ids = roster.map(r => numeric(r['Team #']));
      if (!ids.length || ids.some(n => !Number.isInteger(n) || n <= 0) || new Set(ids).size !== ids.length || roster.some(r => !r['Team Name'])) throw Error('Invalid roster');
      for (const id of ids) { if (allIds.has(id)) errors.push('Team appears in more than one division: ' + id); allIds.add(id); }
      const table = name => {
        const rows = rowsOf(book, name), byId = new Map(rows.map(r => [numeric(r['Team #']), r]));
        if (rows.length !== ids.length || byId.size !== ids.length || ids.some(id => !byId.has(id))) throw Error(name + ': team numbers do not match roster');
        return ids.map(id => byId.get(id));
      };
      const rr = table('TournamentData'), ip = table('InnovationProjectResults'), rd = table('RobotDesignResults'), cv = table('CoreValuesResults'), rg = table('RobotGameScores');
      const gpColumns = [1,2,3].map(i => 'Gracious Professionalism ' + i), rgColumns = [1,2,3].map(i => 'Robot Game ' + i + ' Score');
      for (const [rows, columns, allowed, label] of [[rg, rgColumns, n => Number.isInteger(n) && n >= 0 && n <= maximum, 'Robot Game'], [ip, book.tables.InnovationProjectResults.headers.slice(3,13), n => Number.isInteger(n) && n >= 0 && n <= 4, 'Innovation'], [rd, book.tables.RobotDesignResults.headers.slice(3,13), n => Number.isInteger(n) && n >= 0 && n <= 4, 'Robot Design'], [cv, gpColumns, n => [0,2,3,4].includes(n), 'Core Values']]) {
        for (const row of rows) for (const col of columns) if (!allowed(numeric(row[col]))) errors.push(`${book.name}: ${label}, team ${row['Team #']}: invalid ${col}`);
      }
      const sum = (row, columns) => columns.reduce((s, col) => s + numeric(row[col]), 0);
      // Python slices after setting Team # as the index, removing that column.
      const ips = ip.map(r => sum(r, book.tables.InnovationProjectResults.headers.slice(3,13))), rds = rd.map(r => sum(r, book.tables.RobotDesignResults.headers.slice(3,13))), gps = cv.map(r => sum(r, gpColumns));
      const cvs = cv.map((_, i) => gps[i] + sum(ip[i], Object.keys(ip[i]).filter(k => k.includes('(CV)'))) + sum(rd[i], Object.keys(rd[i]).filter(k => k.includes('(CV)'))));
      const robots = rg.map(r => rgColumns.map(c => numeric(r[c])).sort((a,b) => b-a).reduce((s,n,i) => s + n * [1,.0001,.0000001][i], 0));
      const robotRanks = ranks(robots), champ = [...robotRanks];
      const checks = [[cv, 'Gracious Professionalism Total', gps], [cv, 'Gracious Professionalism Score', gps], [rr, 'Max Robot Game Score', robots], [rr, 'Robot Game Rank', robotRanks]];
      for (const [name, rows, scores] of [['Innovation Project',ip,ips],['Robot Design',rd,rds],['Core Values',cv,cvs]]) {
        const ranking = ranks(scores); ranking.forEach((n,i) => champ[i] += n);
        checks.push([rows,name+' Score',scores],[rows,name+' Rank',ranking],[rr,name+' Rank',ranking]);
      }
      checks.push([rr,"Champion's Score",champ],[rr,"Champion's Rank",ranks(champ,true)]);
      for (const [rows,col,values] of checks) for (let i=0;i<rows.length;i++) { calculationChecks++; if (!close(rows[i][col],values[i])) errors.push(`${book.name}: team ${ids[i]}, ${col}: saved calculation missing or incorrect`); }
      const allocation = info[info.using_divisions ? 'advancing_count_'+entry.division.toLowerCase() : 'advancing_count'];
      if (!Number.isInteger(allocation) || allocation < 0 || allocation > rr.length || rr.filter(r=>r['Advance?']==='Yes').length !== allocation) errors.push(book.name+': advancement allocation mismatch');
      if (rr.some(r => !['',null,'Yes','No','Alt'].includes(r['Advance?']))) errors.push(book.name+': invalid Advance? selection');
      const alternates = rr.filter(r=>r['Advance?']==='Alt').length;
      if (alternates > 1) errors.push(book.name+': more than one alternate');
      else if (allocation && !alternates) warnings.push(book.name+': no alternate selected');
      groups.push({entry,book,roster,rr,known:new Set()});
    } catch(e) { errors.push(book.name+': '+e.message); }
  }
  for (const award of config.AWARDS) {
    const labels = award.Labels || [];
    if (award.ID === 'P_AWD_RG') {
      for (const g of groups) {
        const count = info.using_divisions && award.DivAwd ? award[g.entry.division+'_count'] || 0 : award.TournCount || 0;
        const selected = g.rr.map(r=>numeric(r['Robot Game Rank'])).filter(n=>n>=1&&n<=count);
        if (selected.length !== count || new Set(selected).size !== selected.length) errors.push(g.book.name+': Robot Game award ranks tied or missing');
      }
      continue;
    }
    if (award.ID === 'J_AWD_Judges') {
      groups.forEach(g=>labels.forEach(l=>g.known.add(l)));
      const count = award.TournCount || 0, selected = groups.flatMap(g=>g.rr).filter(r=>labels.includes(r.Award)).length;
      if (selected > count) errors.push('Judges awards exceed allocation');
      if (selected < count) missing.push(`Judges Awards: ${selected} of ${count} selected`);
      continue;
    }
    const scopes = info.using_divisions && award.DivAwd ? groups.map(g=>({gs:[g],count:award[g.entry.division+'_count']||0})) : [{gs:groups,count:award.TournCount||0}];
    for (const {gs,count} of scopes) {
      if (!Number.isInteger(count) || count < 0 || labels.length < count) { errors.push(award.Name+': invalid allocation'); continue; }
      for (const label of labels.slice(0,count)) {
        gs.forEach(g=>g.known.add(label)); const n = gs.flatMap(g=>g.rr).filter(r=>r.Award===label).length;
        if (!n) missing.push((gs.length===1 ? gs[0].entry.division+' ' : '')+label);
        else if (n>1) errors.push(label+': duplicate winners');
      }
    }
  }
  for (const g of groups) for (const r of g.rr) if (r.Award && !g.known.has(r.Award)) errors.push(g.book.name+': unknown or unallocated award '+r.Award);
  return {errors,warnings,missing,groups,calculationChecks};
}
const escapeHtml = s => String(s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#x27;'}[c]));
function renderOutputs(config, validation) {
  const info=config.INFO, groups=[...validation.groups].sort((a,b)=>a.entry.division.localeCompare(b.entry.division));
  const dual=groups.some(g=>{const v=g.book.sheets['Team and Program Information'].cells.F2; return v===true || typeof v==='number'&&v!==0 || typeof v==='string'&&['TRUE','YES','1'].includes(v.toUpperCase());});
  let color=0;
  const paragraph = text => '<p>'+(dual ? `<span class="highlight${color}">${text}</span>` : text)+'</p>';
  const wrap = text => {const p=paragraph(text); if(dual)color=1-color;return p;};
  const teamList = rows => rows.map(r=>wrap(`Team ${Number(r['Team #'])}, ${escapeHtml(r['Team Name'])}`)).join('\n');
  let label='';
  if(info.using_divisions) label=(groups.length>1?'Divisions ':'Division ')+groups.map(g=>g.entry.division.slice(1)).join(' & ');
  else label=info.division_label||'Single Division';
  const ceremony={program_season_name:'',sponsor_acknowledgement:'We want to thank all of our sponsors for supporting this tournament.',coach_nomination_announcement:'',advancement_announcement:'Congratulations to the teams advancing to the next event!',rubric_instructions:'[insert how teams receive their rubrics here]',program_website:'www.firstinspires.org',...info.ceremony};
  ceremony.program_season_name ||= info.season_name||'current';
  const data={season_year:info.season_year||'',ceremony,tournament_name:(info.tournament_long_name||'')+' - '+label,using_divisions:Number(info.using_divisions),dual_emcee:dual,awards_config:config.AWARDS,bg_color_0:dual?'lightblue':'transparent',bg_color_1:dual?'yellow':'transparent',ja_count:0,judges_missing_count:0};
  for(const g of groups) data[info.using_divisions?'team_list_'+g.entry.division:'team_list']=teamList(g.roster);
  for(const g of groups) {
    const suffix=info.using_divisions?'_'+g.entry.division:'';
    // Preserve Python's collection order: it affects emcee color alternation.
    if(info.using_divisions) {
      data['ALT'+suffix]=teamList(g.rr.filter(r=>r['Advance?']==='Alt'));
      data['ADV'+suffix]=teamList(g.rr.filter(r=>r['Advance?']==='Yes'));
    } else {
      data['ADV']=teamList(g.rr.filter(r=>r['Advance?']==='Yes'));
      data['ALT']=teamList(g.rr.filter(r=>r['Advance?']==='Alt'));
    }
  }
  const winner = (r,label,division='',score=false) => wrap((division?escapeHtml(division)+' ':'')+(label?escapeHtml(label)+': ':'')+`Team ${Number(r['Team #'])}, ${escapeHtml(r['Team Name'])}`+(score?' with a score of '+Math.trunc(r['Max Robot Game Score']):''));
  for(const award of config.AWARDS) {
    const scopes=info.using_divisions&&award.DivAwd ? groups.map(g=>({gs:[g],count:award[g.entry.division+'_count']||0,tag:award['ScriptTag'+g.entry.division],division:'Division '+g.entry.division.slice(1)})) : [{gs:groups,count:award.TournCount||0,tag:award.ScriptTagNoDiv,division:''}];
    for(const s of scopes) {
      if(!s.count||!s.tag)continue;
      const rows=s.gs.flatMap(g=>g.rr); let winners=[];
      if(award.ID==='P_AWD_RG') {
        winners=rows.filter(r=>r['Robot Game Rank']>=1&&r['Robot Game Rank']<=s.count).sort((a,b)=>a['Robot Game Rank']-b['Robot Game Rank']);
        data[s.tag]=[...winners].reverse().map(r=>{const n=r['Robot Game Rank'];return winner(r,({1:'1st',2:'2nd',3:'3rd'}[n]||n+'th')+' Place',s.division,true);}).join('\n');
      } else if(award.ID==='J_AWD_Judges') {
        winners=rows.filter(r=>(award.Labels||[]).includes(r.Award));
        const lines=[...winners].reverse().map(r=>winner(r,'Judges Award'));
        data.judges_missing_count=Math.max(0,s.count-winners.length);
        for(let i=0;i<data.judges_missing_count;i++)lines.push(wrap('Judges Award: NONE'));
        data[s.tag]=lines.join('\n'); data.ja_count=winners.length; data.ja_go_goes=winners.length===1?'The judges award goes to:':'The judges awards go to:';
      } else {
        const labels=(award.Labels||[]).slice(0,s.count); winners=rows.filter(r=>labels.includes(r.Award));
        data[s.tag]=[...labels].reverse().map(l=>{const r=winners.find(r=>r.Award===l);return r?winner(r,l,s.division):wrap((s.division?escapeHtml(s.division)+' ':'')+escapeHtml(l)+': NONE');}).join('\n');
      }
      if(award.ID==='J_AWD_IP' && !('ip_this_these' in data) && info.using_divisions&&award.DivAwd)data.ip_this_these=winners.length===1?'this team':'these teams';
      if(award.ID==='J_AWD_RD' && !('rd_this_these' in data) && info.using_divisions&&award.DivAwd)data.rd_this_these=winners.length===1?'this team':'these teams';
    }
  }
  for(const key of ['team_list_D1','team_list_D2','div1_list','div2_list','team_list','ALT','ALT_D1','ALT_D2','ADV','ADV_D1','ADV_D2','ip_this_these','rd_this_these','ja_go_goes','J_AWD_BT'])data[key]??='';
  data.div1_list=data.team_list_D1;data.div2_list=data.team_list_D2;
  for(const a of config.AWARDS)for(const k of ['ScriptTagD1','ScriptTagD2','ScriptTagNoDiv'])if(a[k])data[a[k]]??='';
  const env=new nunjucks.Environment(null,{autoescape:false,throwOnUndefined:true});
  return Object.fromEntries(['script','summary'].map(kind=>[kind,env.renderString(PROBE.templates[kind+'_template-'+(info.using_divisions?'with-divisions':'without-divisions')+'.html.jinja'],data)]));
}
function save(name, content, type='text/html') {
  const url=URL.createObjectURL(new Blob([content],{type})), a=document.createElement('a'); a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);
}
const normalizeHtml = s => s.replace(/\r\n/g,'\n').trim();
async function digest(value) {const bytes=new TextEncoder().encode(JSON.stringify(value));return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');}
async function analyze(inputs, legacy=null, reference=null) {
  const start=performance.now(), books=inputs.map(f=>readWorkbook(f.bytes,f.name));
  const {config,warnings}=configuration(books,legacy), validation=validate(books,config);
  let outputs=null, renderError=null;
  try { outputs=renderOutputs(config,validation); } catch(e) {renderError=e.message;}
  const parity=[];
  if(reference) {
    for(const book of books) {
      const expected=reference.tables[book.name];
      if(expected)for(const [name,table] of Object.entries(expected))parity.push({check:book.name+' / '+name,pass:JSON.stringify(book.tables[name])===JSON.stringify(table)});
    }
    for(const kind of ['script','summary']) if(reference.outputs?.[kind]) {
      const actual=normalizeHtml(outputs?.[kind]||''), expected=normalizeHtml(reference.outputs[kind]);
      const entry={check:kind+' HTML matches Python TOAST',pass:actual===expected};
      if(!entry.pass){let i=0;while(i<Math.min(actual.length,expected.length)&&actual[i]===expected[i])i++;entry.firstDifference={offset:i,actual:actual.slice(Math.max(0,i-80),i+200),expected:expected.slice(Math.max(0,i-80),i+200)};}
      parity.push(entry);
    }
    if(reference.expected)for(const [key,value] of Object.entries(reference.expected))parity.push({check:'Validation '+key,pass:validation[key].length===value});
  }
  return {books,config,validation,outputs,report:{version:PROBE.version,environment:{userAgent:navigator.userAgent,protocol:location.protocol,online:navigator.onLine},tournament:config.INFO.tournament_long_name,usingDivisions:config.INFO.using_divisions,elapsedMs:Math.round(performance.now()-start),files:books.map(b=>({name:b.name,parseMs:Math.round(b.ms),tables:Object.keys(b.tables),configurationState:b.sheets._TOAST_Config?.state||'legacy JSON',formulaCount:b.formulaCount,missingCaches:b.missingCaches})),calculationChecks:validation.calculationChecks,errors:validation.errors,warnings:[...warnings,...validation.warnings],missingAwards:validation.missing,renderError,parity,outputHashes:outputs?{script:await digest(outputs.script),summary:await digest(outputs.summary)}:null}};
}
function show(result) {
  window.lastProbe=result;
  $('report').textContent=JSON.stringify(result.report,null,2);
  const failures=result.report.parity.filter(p=>!p.pass).length;
  $('status').textContent=`${result.report.tournament}: ${result.books.length} workbook(s), ${result.report.calculationChecks} saved-calculation checks, ${result.report.errors.length} data errors, ${failures} comparison failures. ${result.report.elapsedMs} ms.`;
  $('downloads').replaceChildren();
  if(result.outputs && !result.validation.errors.length) {
    for(const kind of ['script','summary']) {const button=document.createElement('button');button.textContent='Download '+kind;button.onclick=()=>{
      if(result.validation.missing.length && prompt('Missing awards will appear as NONE. Type YES to approve:')!=='YES')return;
      const first=result.books[0].name.replace(/\.[^.]+$/,'');const stem=result.books.length>1?first.replace(/[-_ ]?(?:D|div)[12]$/i,''):first;
      save(stem+(kind==='script'?'-closing-ceremony':'-summary')+'.html',result.outputs[kind]);
    };$('downloads').append(button);}
  }
}
async function runSamples() {
  $('status').textContent='Running built-in workbook and Python comparison tests…';
  const results=[];
  for(const fixture of PROBE.fixtures) {
    try {
      const inputs=fixture.files.map(f=>({name:f.name,bytes:Uint8Array.from(atob(f.base64),c=>c.charCodeAt(0))}));
      const result=await analyze(inputs,fixture.legacy,fixture.reference);results.push({name:fixture.name,...result.report});show(result);
    }catch(e){results.push({name:fixture.name,fatal:e.stack||e.message});}
  }
  // Negative cases exercise browser logic without changing source workbooks.
  const assertions=[];const assert=(check,pass)=>assertions.push({check,pass});
  assert('Minimum ranks preserve ties',JSON.stringify(ranks([10,10,5]))==='[1,1,3]');
  assert('Ascending Champion ranks preserve ties',JSON.stringify(ranks([2,2,4],true))==='[1,1,3]');
  assert('Booleans and blanks are not scores',Number.isNaN(numeric(true))&&Number.isNaN(numeric(null))&&Number.isNaN(numeric('')));
  assert('Escaping handles team names',escapeHtml('A & <B> "C"')==='A &amp; &lt;B&gt; &quot;C&quot;');
  assert('Template missing variables fail',(()=>{try{new nunjucks.Environment(null,{throwOnUndefined:true}).renderString('{{ missing }}',{});return false;}catch{return true;}})());
  if(window.lastProbe) {
    const original=window.lastProbe, clone=()=>structuredClone(original.books), config=original.config;
    let books=clone(), t=books[0].tables.TournamentData, index=t.headers.indexOf("Champion's Score");t.rows[0][index]=999999;
    assert('Stale saved calculations rejected',validate(books,config).errors.some(e=>e.includes("Champion's Score")));
    books=clone();t=books[0].tables.TournamentData;index=t.headers.indexOf('Advance?');t.rows[0][index]='Maybe';
    assert('Invalid advancement selection rejected',validate(books,config).errors.some(e=>e.includes('Advance?')));
    assert('Missing division rejected',(()=>{try{configuration(original.books.length>1?original.books.slice(0,1):[...original.books,...original.books],null);return false;}catch{return true;}})());
    books=clone();books.forEach((b,i)=>b.name='renamed-'+i+'.xlsm');
    assert('Renamed workbooks resolved by embedded identity',configuration(books,null).config.INFO.ojs_files.every((e,i)=>e.filename===books[i].name));
    books=clone();books.push(structuredClone(books[0]));
    assert('Duplicate division rejected',(()=>{try{configuration(books,null);return false;}catch{return true;}})());
    books=clone();delete books[0].tables.OfficialTeamList;
    assert('Missing roster table rejected',validate(books,config).errors.some(e=>e.includes('Missing named table')));
    books=clone();t=books[0].tables.RobotGameScores;index=t.headers.indexOf('Robot Game 1 Score');t.rows[0][index]=true;
    assert('Boolean workbook score rejected',validate(books,config).errors.some(e=>e.includes('invalid Robot Game')));
    books=clone();t=books[0].tables.TournamentData;index=t.headers.indexOf('Award');
    const awarded=t.rows.find(row=>row[index] && !(config.AWARDS.find(a=>a.ID==='J_AWD_Judges')?.Labels||[]).includes(row[index]));
    if(awarded) {
      const label=awarded[index], other=t.rows.find(row=>row!==awarded);other[index]=label;
      assert('Duplicate judged award rejected',validate(books,config).errors.some(e=>e.includes('duplicate winners')));
      books=clone();t=books[0].tables.TournamentData;index=t.headers.indexOf('Award');for(const row of t.rows)if(row[index]===label)row[index]=null;
      const omitted=validate(books,config);
      assert('Missing winner requires approval and renders NONE',omitted.missing.length>original.validation.missing.length && renderOutputs(config,omitted).script.includes('NONE'));
    }
    const dual=PROBE.fixtures[0];
    if(dual.files.length>1) {
      books=dual.files.map(f=>readWorkbook(Uint8Array.from(atob(f.base64),c=>c.charCodeAt(0)),f.name));books[1].embedded.identity='different tournament';
      assert('Mixed tournaments rejected',(()=>{try{configuration(books,null);return false;}catch{return true;}})());
    }
  }
  const summary={version:PROBE.version,environment:{userAgent:navigator.userAgent,protocol:location.protocol,online:navigator.onLine},fixtures:results,assertions};
  summary.pass=results.every(r=>!r.fatal&&!r.renderError&&r.parity.length&&r.parity.every(p=>p.pass))&&assertions.every(a=>a.pass);
  window.probeSummary=summary;$('report').textContent=JSON.stringify(summary,null,2);$('status').textContent=summary.pass?'PASS — workbook extraction, Python output comparisons, and negative checks passed.':'FAIL — inspect the report below.';
  document.documentElement.dataset.probeResult=summary.pass?'pass':'fail';
}
$('samples').onclick=()=>runSamples().catch(e=>{$('status').textContent=e.message;});
$('files').onchange=async event=>{
  try {
    const files=Array.from(event.target.files), inputs=[];let legacy=null;
    for(const f of files)if(/\.json$/i.test(f.name))legacy=JSON.parse(await f.text());else inputs.push({name:f.name,bytes:new Uint8Array(await f.arrayBuffer())});
    show(await analyze(inputs,legacy));
  }catch(e){$('status').textContent='Cannot analyze: '+e.message;$('report').textContent=e.stack;}
};
$('export').onclick=()=>save('toast-browser-test-report.json',JSON.stringify(window.probeSummary||window.lastProbe?.report||{},null,2),'application/json');
if(location.search.includes('selftest'))runSamples().catch(e=>{$('report').textContent=e.stack;document.documentElement.dataset.probeResult='fail';});
