/* TOAST browser engine. Read-only Open XML reader; no network requests. */
'use strict';
(() => {
const VERSION = '1.0.4';
const LIMITS = Object.freeze({fileBytes:25*1024*1024, unpackedBytes:100*1024*1024, entries:3000, tableCells:200000});
const own = (o,k) => Object.prototype.hasOwnProperty.call(o,k);
function parseJson(text) {
  return JSON.parse(text, (key,value) => {
    if (['__proto__','prototype','constructor'].includes(key)) throw Error('Unsupported configuration property: '+key);
    return value;
  });
}
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
  const start = performance.now();
  if(bytes.length>LIMITS.fileBytes)throw Error(name+': workbook exceeds the 25 MB limit.');
  // Validate ZIP entry sizes before allocating inflated data. Only XML parts
  // are inflated; macros and other executable workbook content are ignored.
  let expanded=0, entries=0;
  const zip = fflate.unzipSync(bytes,{filter:file=>{
    expanded+=file.originalSize;entries++;
    if(expanded>LIMITS.unpackedBytes||entries>LIMITS.entries)throw Error('Workbook is too large after decompression.');
    return file.name.endsWith('.xml')||file.name.endsWith('.rels');
  }});
  if (!zip['xl/workbook.xml']) throw Error('Not an unencrypted Open XML workbook');
  const strings = zip['xl/sharedStrings.xml'] ? elements(xml(zip['xl/sharedStrings.xml']), 'si').map(n => elements(n, 't').map(t => t.textContent).join('')) : [];
  const rels = relationships(zip, 'xl/workbook.xml'), sheets = Object.create(null), tables = Object.create(null);
  let formulaCount = 0, missingCaches = 0;
  for (const sheet of elements(xml(zip['xl/workbook.xml']), 'sheet')) {
    const path = rels.get(sheet.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships', 'id'));
    if (!zip[path]) throw Error('Missing worksheet part: ' + path);
    const doc = xml(zip[path]), cells = Object.create(null);
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
      cells[c.getAttribute('r')] = value;
    }
    const sheetName = sheet.getAttribute('name');
    if(own(sheets,sheetName))throw Error('Duplicate worksheet name: '+sheetName);
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
      if(c0<1||r0<1||c1<c0||r1<r0||c1>16384||r1>1048576||(c1-c0+1)*(r1-r0+1)>LIMITS.tableCells)throw Error('Invalid or excessive table range: '+ref);
      const column = n => { let s = ''; while (n) { n--; s = String.fromCharCode(65 + n % 26) + s; n = Math.floor(n / 26); } return s; };
      const rows = [];
      for (let r = r0; r <= r1; r++) rows.push(Array.from({length: c1 - c0 + 1}, (_, i) => {const v=cells[column(c0 + i) + r]??null;return typeof v==='string'?v.trim()||null:v;}));
      const headers = rows.shift().map(v=>v===null?'None':String(v));
      if (new Set(headers).size !== headers.length) throw Error('Duplicate headers in ' + table.getAttribute('name'));
      const tableName=table.getAttribute('name');
      if(own(tables,tableName))throw Error('Duplicate named table: '+tableName);
      tables[tableName] = {sheet: sheetName, ref, headers, rows};
    }
  }
  const hidden = sheets._TOAST_Config;
  let embedded = null;
  if (hidden) {
    const c = hidden.cells;
    if (c.A1 !== 'TOAST_CONFIG' || c.B1 !== 1 || !Number.isInteger(c.B4) || c.B4 < 1 || c.B4 > 1000) throw Error('Invalid embedded configuration');
    let payload = '';
    for (let i = 0; i < c.B4; i++) { if (typeof c['A' + (i + 5)] !== 'string') throw Error('Missing configuration chunk'); payload += c['A' + (i + 5)]; }
    embedded = {division: c.B2 || '', identity: c.B3, config: parseJson(payload)};
    if (!['', 'D1', 'D2'].includes(embedded.division)) throw Error('Invalid division');
    if(typeof embedded.identity!=='string'||!embedded.identity)throw Error('Missing embedded tournament identity');
    if(!object(embedded.config)||!object(embedded.config.INFO)||!Array.isArray(embedded.config.AWARDS))throw Error('Invalid embedded configuration: INFO and AWARDS are required.');
  }
  return {name, tables, sheets, embedded, formulaCount, missingCaches, ms: performance.now() - start};
}
const numeric = v => (typeof v === 'number' || typeof v === 'string' && /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(v.trim())) && Number.isFinite(Number(v)) ? Number(v) : NaN;
const ranks = (values, ascending = false) => values.map(v => 1 + values.filter(x => ascending ? x < v : x > v).length);
const close = (a, b) => Number.isFinite(numeric(a)) && Math.abs(numeric(a) - b) <= Math.max(1e-8, 1e-9 * Math.max(Math.abs(numeric(a)), Math.abs(b)));
function rowsOf(book, name) {
  const t = book.tables[name]; if (!t) throw Error('Missing named table: ' + name);
  return t.rows.map(row => Object.fromEntries(t.headers.map((h, i) => [h, row[i]])));
}
const TABLES = {
  OfficialTeamList:['Team and Program Information',['Team #','Team Name']],
  TournamentData:['Results and Rankings',['Team #','Team Name','Award','Advance?','Max Robot Game Score','Robot Game Rank','Core Values Rank','Innovation Project Rank','Robot Design Rank',"Champion's Score","Champion's Rank"]],
  RobotGameScores:['Robot Game Scores',['Team #',...Array.from({length:3},(_,i)=>`Robot Game ${i+1} Score`)]],
  InnovationProjectResults:['Innovation Project Input',['Team #','Team Name','Identify - Define','Identify - Research (CV)','Design - Plan','Design - Teamwork (CV)','Create - Innovation (CV)','Create - Model','Iterate - Sharing','Iterate - Improvement','Communicate - Impact (CV)','Communicate - Fun (CV)','Innovation Project Score','Innovation Project Rank']],
  RobotDesignResults:['Robot Design Input',['Team #','Team Name','Identify - Strategy','Identify - Research (CV)','Design - Ideas (CV)','Design - Building/Coding','Create - Attachments','Create - Code/ Sensors','Iterate - Testing','Iterate - Improvements (CV)','Communicate - Impact (CV)','Communicate - Fun (CV)','Robot Design Score','Robot Design Rank']],
  CoreValuesResults:['Core Values Input',['Team #',...Array.from({length:3},(_,i)=>`Gracious Professionalism ${i+1}`),'Gracious Professionalism Total','Gracious Professionalism Score','Core Values Score','Core Values Rank']]
};
const object = v => v!==null&&typeof v==='object'&&!Array.isArray(v);
const count = v => Number.isSafeInteger(v)&&v>=0;
function checkConfig(config) {
  if(!object(config)||!object(config.INFO)||!Array.isArray(config.AWARDS))throw Error('Configuration must contain INFO and an AWARDS list. Regenerate the tournament with MAESTRO.');
  const info=config.INFO;
  if(typeof info.using_divisions!=='boolean')throw Error('INFO.using_divisions must be true or false.');
  if(typeof info.tournament_long_name!=='string'||!info.tournament_long_name.trim())throw Error('Missing tournament name in INFO.tournament_long_name.');
  if(!Array.isArray(info.ojs_files)||!info.ojs_files.length||info.ojs_files.length>2)throw Error('INFO.ojs_files must list one or two OJS workbooks.');
  const codes=new Set(), filenames=new Set();
  info.ojs_files=info.ojs_files.map((raw,i)=>{
    const filename=typeof raw==='string'?raw:raw?.filename;
    let division=typeof raw==='string'?(info.using_divisions?'D'+(i+1):''):raw?.division||raw?.div||'';
    division=String(division).trim().toUpperCase();if(division&&!division.startsWith('D'))division='D'+division;
    if(typeof filename!=='string'||!filename.trim()||/[\\/]/.test(filename))throw Error('OJS filenames must be filenames without folder paths.');
    if(filenames.has(filename.toLowerCase()))throw Error('Duplicate OJS filename: '+filename);filenames.add(filename.toLowerCase());
    if(info.using_divisions ? !['D1','D2'].includes(division)||codes.has(division) : division!==''||info.ojs_files.length!==1)throw Error('Use distinct D1/D2 entries for division tournaments, or one workbook without a division.');
    codes.add(division);return {filename,division};
  });
  if(info.robot_game_max_score!==undefined&&(!Number.isSafeInteger(info.robot_game_max_score)||info.robot_game_max_score<=0))throw Error('INFO.robot_game_max_score must be a positive integer.');
  if(info.ceremony!==undefined&&(!object(info.ceremony)||Object.values(info.ceremony).some(v=>typeof v!=='string')))throw Error('Ceremony announcements must be text.');
  const ids=new Set(), tags=new Set();
  for(const award of config.AWARDS) {
    if(!object(award)||typeof award.ID!=='string'||!award.ID||typeof award.Name!=='string'||!award.Name.trim())throw Error('Each award needs an ID and Name.');
    if(ids.has(award.ID))throw Error('Duplicate award ID: '+award.ID);ids.add(award.ID);
    if(typeof award.DivAwd!=='boolean')throw Error(award.Name+': DivAwd must be true or false.');
    const fields=info.using_divisions&&award.DivAwd?[['D1_count','ScriptTagD1'],['D2_count','ScriptTagD2']]:[['TournCount','ScriptTagNoDiv']];
    for(const [key,tag] of fields) {
      const n=award[key]===undefined?0:award[key];if(!count(n))throw Error(award.Name+': '+key+' must be a nonnegative integer.');
      if(n&&(typeof award[tag]!=='string'||!/^\w+$/.test(award[tag])))throw Error(award.Name+': missing or invalid '+tag+'.');
      if(n&&tags.has(award[tag]))throw Error('Duplicate script tag: '+award[tag]);if(n)tags.add(award[tag]);
      if(award.ID!=='P_AWD_RG'&&(!Array.isArray(award.Labels)||award.Labels.length<n||award.Labels.some(l=>typeof l!=='string'||!l.trim())||new Set(award.Labels.slice(0,n)).size!==n))throw Error(award.Name+': provide a distinct nonempty label for every allocated award.');
    }
    if(info.using_divisions&&award.ID==='P_AWD_RG'&&!award.DivAwd&&(award.TournCount||0)>0)throw Error('Robot Game awards must be allocated per division.');
  }
  return config;
}
const canonical = v => JSON.stringify(v,(_,value)=>object(value)?Object.fromEntries(Object.keys(value).sort().map(k=>[k,value[k]])):value);
function configuration(books, legacy) {
  if(!books.length)throw Error('Select your saved OJS workbook(s).');
  if(books.length>2)throw Error('Select only one tournament: one or two OJS files.');
  if(new Set(books.map(b=>b.name.toLowerCase())).size!==books.length)throw Error('Duplicate selected filename.');
  const records = books.filter(b => b.embedded).sort((a, b) => a.embedded.division.localeCompare(b.embedded.division));
  if (!records.length) {
    if (!legacy) throw Error('No embedded configuration. Select legacy tournament_config.json as well.');
    const config=checkConfig(structuredClone(legacy));
    if(books.length!==config.INFO.ojs_files.length||config.INFO.ojs_files.some(e=>!books.some(b=>b.name===e.filename)))throw Error('Selected filenames do not match the legacy configuration.');
    for(const kind of ['script','summary']) {
      const requested=config.INFO[kind+'_template'];
      if(requested&&![kind+'_template.html.jinja',kind+'_template-'+(config.INFO.using_divisions?'with-divisions':'without-divisions')+'.html.jinja'].includes(requested))throw Error('Custom legacy ceremony templates require Python TOAST. This browser version includes the standard templates.');
    }
    return {config, warnings: ['Legacy configuration loaded. Built-in ceremony templates will be used.']};
  }
  if (records.length !== books.length) throw Error('Selected files mix embedded and legacy workbooks');
  const divisions = records.map(b => b.embedded.division), warnings = [];
  if (new Set(divisions).size !== records.length || (divisions.includes('') && records.length > 1)) throw Error('Duplicate or mixed division identities');
  if (new Set(records.map(b => b.embedded.identity)).size !== 1) throw Error('Files belong to different tournaments');
  const config = checkConfig(structuredClone(records[0].embedded.config)), info = config.INFO;
  if (info.using_divisions !== Boolean(divisions[0])) throw Error('Division metadata disagrees with configuration');
  if (JSON.stringify(info.ojs_files.map(e => e.division).sort()) !== JSON.stringify([...divisions].sort())) throw Error('Missing or unexpected division');
  for (const b of records.slice(1)) if (canonical(b.embedded.config) !== canonical(records[0].embedded.config)) warnings.push('Configuration differs; using ' + records[0].name);
  if(legacy)warnings.push('Embedded configuration takes precedence over the selected JSON file.');
  info.ojs_files = records.map(b => ({division: b.embedded.division, filename: b.name}));
  return {config, warnings};
}
function validate(books, config) {
  checkConfig(config);
  const errors = [], warnings = [], missing = [], groups = [], inputIssues = [], calculationIssues = [], allIds = new Set(); let calculationChecks = 0;
  const info = config.INFO, maximum = info.robot_game_max_score ?? 530;
  if (typeof info.using_divisions !== 'boolean' || !Array.isArray(config.AWARDS) || !Number.isInteger(maximum) || maximum <= 0) throw Error('Invalid configuration schema');
  for (const entry of info.ojs_files) {
    const book = books.find(b => b.name === entry.filename); if (!book) throw Error('Missing workbook: ' + entry.filename);
    try {
      for(const [name,[sheet,columns]] of Object.entries(TABLES)) {
        const t=book.tables[name];if(!t)throw Error('Missing named table: '+name);
        if(t.sheet!==sheet)throw Error(name+': expected worksheet '+sheet);
        if(new Set(t.headers).size!==t.headers.length)throw Error(name+': duplicate column headers');
        for(const col of columns)if(!t.headers.includes(col))throw Error(name+': missing column '+col);
      }
      const roster = rowsOf(book, 'OfficialTeamList'), ids = roster.map(r => numeric(r['Team #']));
      if (!ids.length || ids.some(n => !Number.isInteger(n) || n <= 0) || new Set(ids).size !== ids.length || roster.some(r => !r['Team Name'])) throw Error('Invalid roster');
      for (const id of ids) { if (allIds.has(id)) errors.push('Team appears in more than one division: ' + id); allIds.add(id); }
      const table = name => {
        const rows = rowsOf(book, name), byId = new Map(rows.map(r => [numeric(r['Team #']), r]));
        if (rows.length !== ids.length || byId.size !== ids.length || ids.some(id => !byId.has(id))) throw Error(name + ': team numbers do not match roster');
        return ids.map(id => byId.get(id));
      };
      const rr = table('TournamentData'), ip = table('InnovationProjectResults'), rd = table('RobotDesignResults'), cv = table('CoreValuesResults'), rg = table('RobotGameScores');
      const judgesLabels=config.AWARDS.find(a=>a.ID==='J_AWD_Judges')?.Labels||[];
      const selections=rr.map(r=>r.Award).filter(Boolean);
      for(const label of new Set(selections))if(!judgesLabels.includes(label)&&selections.filter(x=>x===label).length>1)errors.push(book.name+': duplicate award '+label);
      const gpColumns = [1,2,3].map(i => 'Gracious Professionalism ' + i), rgColumns = [1,2,3].map(i => 'Robot Game ' + i + ' Score');
      let invalidScores=false;
      const division=entry.division?'Division '+entry.division.slice(1):'Tournament';
      for (const [rows, columns, allowed, tableName, rule] of [[rg, rgColumns, n => Number.isInteger(n) && n >= 0 && n <= maximum, 'RobotGameScores', `a whole number from 0 to ${maximum}`], [ip, TABLES.InnovationProjectResults[1].slice(2,12), n => Number.isInteger(n) && n >= 0 && n <= 4, 'InnovationProjectResults', 'a whole number from 0 to 4'], [rd, TABLES.RobotDesignResults[1].slice(2,12), n => Number.isInteger(n) && n >= 0 && n <= 4, 'RobotDesignResults', 'a whole number from 0 to 4'], [cv, gpColumns, n => [0,2,3,4].includes(n), 'CoreValuesResults', '0, 2, 3, or 4']]) {
        for (const row of rows) for (const col of columns) if (!allowed(numeric(row[col]))) {
          invalidScores=true;
          const t=book.tables[tableName], start=/^([A-Z]+)(\d+)/.exec(t.ref);
          let column=Array.from(start[1]).reduce((n,c)=>n*26+c.charCodeAt(0)-64,0)+t.headers.indexOf(col), letters='';
          while(column){column--;letters=String.fromCharCode(65+column%26)+letters;column=Math.floor(column/26);}
          const sourceRow=t.rows.findIndex(r=>numeric(r[t.headers.indexOf('Team #')])===numeric(row['Team #']));
          const cell=letters+(Number(start[2])+1+sourceRow);
          const blank=row[col]===null||row[col]===undefined||row[col]==='';
          const location=`${division} · ${t.sheet} · Cell ${cell}`;
          const instruction=`Team ${row['Team #']}${row['Team Name']?' — '+row['Team Name']:''}: “${col}” ${blank?'is blank':'has an invalid value'}. Enter ${rule}.`;
          const message=location+'\n'+instruction;
          inputIssues.push({file:book.name,division:entry.division,sheet:t.sheet,cell,team:row['Team #'],field:col,value:row[col],location,instruction,message});
          errors.push(message);
        }
      }
      // A bad input invalidates downstream totals and ranks for the workbook.
      // Check them on the next run, after the director fixes the input values.
      if(!invalidScores) {
      const sum = (row, columns) => columns.reduce((s, col) => s + numeric(row[col]), 0);
      // Python slices after setting Team # as the index, removing that column.
      const ips = ip.map(r => sum(r, TABLES.InnovationProjectResults[1].slice(2,12))), rds = rd.map(r => sum(r, TABLES.RobotDesignResults[1].slice(2,12))), gps = cv.map(r => sum(r, gpColumns));
      const cvs = cv.map((_, i) => gps[i] + sum(ip[i], Object.keys(ip[i]).filter(k => k.includes('(CV)'))) + sum(rd[i], Object.keys(rd[i]).filter(k => k.includes('(CV)'))));
      const robots = rg.map(r => rgColumns.map(c => numeric(r[c])).sort((a,b) => b-a).reduce((s,n,i) => s + n * [1,.0001,.0000001][i], 0));
      const robotRanks = ranks(robots), champ = [...robotRanks];
      const checks = [[cv, 'Gracious Professionalism Total', gps], [cv, 'Gracious Professionalism Score', gps], [rr, 'Max Robot Game Score', robots], [rr, 'Robot Game Rank', robotRanks]];
      for (const [name, rows, scores] of [['Innovation Project',ip,ips],['Robot Design',rd,rds],['Core Values',cv,cvs]]) {
        const ranking = ranks(scores); ranking.forEach((n,i) => champ[i] += n);
        checks.push([rows,name+' Score',scores],[rows,name+' Rank',ranking],[rr,name+' Rank',ranking]);
      }
      checks.push([rr,"Champion's Score",champ],[rr,"Champion's Rank",ranks(champ,true)]);
      const before=calculationIssues.length;
      for (const [rows,col,values] of checks) for (let i=0;i<rows.length;i++) { calculationChecks++; if (!close(rows[i][col],values[i])) calculationIssues.push({file:book.name,team:ids[i],column:col,saved:rows[i][col],expected:values[i]}); }
      if(calculationIssues.length>before)errors.push(`${division}: saved totals or rankings are out of date. Recalculate and save this OJS workbook in Excel, then select the files again. If the issue remains, check the workbook formulas. Calculation details are in the diagnostic report.`);
      }
      const allocation = info[info.using_divisions ? 'advancing_count_'+entry.division.toLowerCase() : 'advancing_count'];
      if (!Number.isInteger(allocation) || allocation < 0 || allocation > rr.length || rr.filter(r=>r['Advance?']==='Yes').length !== allocation) errors.push(book.name+': advancement allocation mismatch');
      if (rr.some(r => !['',null,'Yes','No','Alt'].includes(r['Advance?']))) errors.push(book.name+': invalid Advance? selection');
      const alternates = rr.filter(r=>r['Advance?']==='Alt').length;
      if (alternates > 1) errors.push(book.name+': more than one alternate');
      else if (allocation && !alternates) warnings.push(book.name+': no alternate selected');
      groups.push({entry,book,roster,rr,invalidScores,known:new Set()});
    } catch(e) { errors.push(book.name+': '+e.message); }
  }
  for (const award of config.AWARDS) {
    const labels = award.Labels || [];
    if (award.ID === 'P_AWD_RG') {
      for (const g of groups) {
        if(g.invalidScores)continue;
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
  return {errors,warnings,missing,groups,inputIssues,calculationIssues,calculationChecks};
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
  const data={season_year:info.season_year||'',ceremony,tournament_name:escapeHtml((info.tournament_long_name||'')+' - '+label),using_divisions:Number(info.using_divisions),dual_emcee:dual,awards_config:config.AWARDS,bg_color_0:dual?'lightblue':'transparent',bg_color_1:dual?'yellow':'transparent',ja_count:0,judges_missing_count:0};
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
  return Object.fromEntries(['script','summary'].map(kind=>{
    const name=kind+'_template-'+(info.using_divisions?'with-divisions':'without-divisions')+'.html.jinja';
    for(const variable of TOAST_ASSETS.required[name])if(!own(data,variable))throw Error('Missing template variable: '+variable+'. Check award script tags in the tournament configuration.');
    return [kind,env.renderString(TOAST_ASSETS.templates[name],data)];
  }));
}
function outputNames(config) {
  let stem=config.INFO.ojs_files[0].filename.replace(/\.[^.]+$/,'');
  if(config.INFO.ojs_files.length>1)stem=stem.replace(/[-_ ]?(?:D|div)[12]$/i,'');
  return {script:stem+'-closing-ceremony.html',summary:stem+'-summary.html'};
}
function processBooks(books,legacy=null) {
  const {config,warnings}=configuration(books,legacy), validation=validate(books,config);
  validation.warnings.unshift(...warnings);
  let outputs=null;
  if(!validation.errors.length)try{outputs=renderOutputs(config,validation);}catch(e){validation.errors.push('Ceremony templates: '+e.message);}
  return {config,validation,outputs,names:outputNames(config)};
}
function analyze(inputs,legacy=null) {
  const start=performance.now();
  const books=inputs.map(f=>{if(f.name.startsWith('~$'))throw Error('Select the OJS workbook, not an Excel temporary lock file.');return readWorkbook(f.bytes,f.name);});
  const result=processBooks(books,legacy);
  return {...result,books,elapsedMs:Math.round(performance.now()-start)};
}
window.Toast=Object.freeze({VERSION,LIMITS,TABLES,parseJson,readWorkbook,checkConfig,configuration,validate,renderOutputs,processBooks,analyze,outputNames,ranks,numeric,escapeHtml});
})();
