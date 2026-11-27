// Offline validation of original and derived CycloneDX 1.5 evidence.
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';

const require = createRequire(new URL('../plugins/codex-console/package.json', import.meta.url));
const Ajv = require('ajv');
const addFormats = require('ajv-formats');
const { fullFormats } = require('ajv-formats/dist/formats');
const sha = b => createHash('sha256').update(b).digest('hex');
const dir = fileURLToPath(new URL('./schemas/cyclonedx-1.5/', import.meta.url));
const out = fileURLToPath(new URL('../dependency-audit/', import.meta.url));
const ajv = new Ajv({ strict: false, allErrors: true, validateFormats: true });
addFormats(ajv);
ajv.addFormat('iri-reference', fullFormats['uri-reference']);
ajv.addFormat('idn-email', fullFormats.email);
const schemas = {};
for (const name of ['spdx.schema.json', 'jsf-0.82.schema.json', 'bom-1.5.schema.json']) {
  const bytes = fs.readFileSync(path.join(dir,name));
  schemas[name] = sha(bytes);
  ajv.addSchema(JSON.parse(bytes));
}
const validate = ajv.getSchema('http://cyclonedx.org/schema/bom-1.5.schema.json');
assert.equal(typeof validate,'function');
assert.equal(validate({bomFormat:'CycloneDX',specVersion:'1.5',version:1}),true);
assert.equal(validate({bomFormat:'CycloneDX',specVersion:'9.9',version:1}),false);
assert.equal(validate({bomFormat:'CycloneDX',specVersion:'1.5',version:1,unexpected:true}),false);
const results = {};
for (const name of ['npm-sbom.cdx.json','npm-sbom.derived.cdx.json']) {
  const b = fs.readFileSync(path.join(out,name));
  assert.ok(b.length <= 16*1024*1024);
  const pass = validate(JSON.parse(b));
  results[name] = {sha256:sha(b),schemaValid:pass,errors:(validate.errors||[]).slice(0,50).map(x=>({keyword:x.keyword,schemaPath:x.schemaPath}))};
}
const report = {schema:'CycloneDX 1.5',schemas,formatScope:'ASCII URI/email subset for IRI/idn-email; no network',results};
fs.writeFileSync(path.join(out,'sbom-schema-report.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log('D22_SBOM_SCHEMA '+JSON.stringify(report));
assert.equal(results['npm-sbom.derived.cdx.json'].schemaValid,true,'derived SBOM schema validation failed');
