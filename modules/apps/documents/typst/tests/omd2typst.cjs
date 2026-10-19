// Run the installed plugin's actual WASM converter and PDF export path in a
// disposable vault. Obsidian classes/filesystem indexing are test doubles;
// this does not claim live Electron discovery or watcher acceptance.
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const cp = require('node:child_process'), assert = require('node:assert/strict');
const [plugin, root] = process.argv.slice(2);
if (!plugin || !root) throw Error('Usage: node tests/omd2typst.cjs PLUGIN_MAIN DISPOSABLE_VAULT');
class TFile { constructor(p) { this.path=p; this.extension=path.extname(p).slice(1); this.parent={path:path.dirname(p)}; } }
class FileSystemAdapter {
  getBasePath() { return root; }
  async writeBinary(p,b) { fs.writeFileSync(path.join(root,p),Buffer.from(b)); }
}
const obsidian = new Proxy({TFile, FileSystemAdapter, Notice:class {}}, {get:(o,k)=>o[k]??class {}});
const sandbox = {require:n=>n==='obsidian'?obsidian:require(n),module:{exports:{}},console,TextDecoder,TextEncoder,WebAssembly,Uint8Array,Date,setTimeout,clearTimeout,process,Buffer};
vm.runInNewContext(fs.readFileSync(plugin,'utf8')+'\nmodule.exports.test={renderToTypst,exportNote,parseTemplateLanguages};',sandbox);
(async()=>{
 const api=sandbox.module.exports.test;
 const note='letters/representative.md', template='3-misc/phoenix-typst/omd2typst/phoenix-letter.typ';
 fs.mkdirSync(path.join(root,'letters'),{recursive:true});
 const fixture=fs.readFileSync(path.join(__dirname,'german-letter.md'),'utf8');
 const paragraph='Die Sozialversicherungsbeitragsberechnung und die Krankenversicherungsbeitragspflicht verlangen eine nachvollziehbare Verhältnismäßigkeitsprüfung. Die Verwaltungsverfahrensvorschriften sichern die Sachverhaltsaufklärung. Die Lebenshaltungskostenentwicklung bleibt zu berücksichtigen.\n\n';
 const markdown=fixture.replace('Mit freundlichen Grüßen',Array.from({length:7},(_,i)=>`## Prüfung ${i+1}\n\n${paragraph.repeat(3)}`).join('')+'Mit freundlichen Grüßen');
 fs.writeFileSync(path.join(root,note),markdown);
 const adapter=new FileSystemAdapter();
 const app={vault:{adapter,read:async f=>fs.readFileSync(path.join(root,f.path),'utf8'),getAbstractFileByPath:p=>fs.existsSync(path.join(root,p))?new TFile(p):null},metadataCache:{getFirstLinkpathDest:()=>null}};
 const entry={name:'phoenix-letter',path:template,languages:['de','en']};
 assert.deepEqual(Array.from(api.parseTemplateLanguages(fs.readFileSync(path.join(root,template),'utf8'))),['de','en']);
 await api.exportNote(new TFile(note),'pdf',entry,{outputMode:'same-folder',defaultLanguage:'de'},app,{});
 const pdf=path.join(root,'letters/representative.pdf');
 const extract=()=>cp.execFileSync('pdftotext',['-layout',pdf,'-'],{encoding:'utf8'});
 const text=extract();
 const info=cp.execFileSync('pdfinfo',[pdf],{encoding:'utf8'});
 assert(!text.includes('PRIVATE_SENTINEL')); assert(!info.includes('PRIVATE_SENTINEL'));
 assert(text.includes('Erika Beispiel') && text.includes('Sozialgericht Musterstadt'));
 const pages=Number(info.match(/Pages:\s+(\d+)/)[1]); assert(pages>=3);
 for(let i=1;i<=pages;i++) assert(text.includes(`Seite ${i} von ${pages}`));
 assert(/Verhältnis[-‐\u00ad]\s*\nmäßigkeitsprüfung/u.test(text),'Expected German compound-word hyphenation');
 // Source edits are read again by Typst on the next export, without plugin cache.
 const target=path.join(root,template), original=fs.readFileSync(target,'utf8');
 fs.writeFileSync(target,original.replace('    doc,','    [ADAPTER-RELOAD-PROBE #doc],'));
 await api.exportNote(new TFile(note),'pdf',entry,{outputMode:'same-folder',defaultLanguage:'de'},app,{});
 assert(extract().includes('ADAPTER-RELOAD-PROBE'));
 fs.writeFileSync(target,original);
 await api.exportNote(new TFile(note),'pdf',entry,{outputMode:'same-folder',defaultLanguage:'de'},app,{});
 console.log(`PASS: actual Omd2Typst converter/export, ${pages} pages, metadata allowlist, hyphenation, adapter reload; ${pdf}`);
})().catch(e=>{console.error(e);process.exitCode=1;});
