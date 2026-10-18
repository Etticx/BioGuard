import assert from 'node:assert/strict';
import test from 'node:test';
import { parseReport, validateReportDetails, type ReportDetails } from '../src/services/reportContract';
const details: ReportDetails = {site:'Block B',landmark:'Playground drain',extent:'unsure',observed_on:'2026-01-01',notes:'',request_key:'test_key_123'};
test('reports require a usable location and a real observation date',()=>{
  assert.equal(validateReportDetails(details),null);
  for(const change of [{site:' '},{landmark:''},{observed_on:'2026-02-30'},{observed_on:'2099-01-01'},{notes:'x'.repeat(1201)}]){
    assert.equal(typeof validateReportDetails({...details,...change}),'string');
  }
});
test('a report receipt needs a known workflow status and a valid model suggestion',()=>{
  const value={id:'123',reference:'BG-123',status:'submitted',revision:1,site:'Block B',landmark:'Drain',photos:[],prediction:{predicted_species:'Mimosa pudica',common_name:'Touch-me-not',sdp_listed_invasive:true,confidence:0.4,uncertain_identification:true,known_class_scope_only:true,supported_species_count:9}};
  assert.equal(parseReport(value).prediction?.uncertain_identification,true);
  for(const change of [{status:'approved_by_ai'},{revision:0},{prediction:{}}])assert.throws(()=>parseReport({...value,...change}));
});

test('reports remain readable when identification is unavailable',()=>{const value={id:'123',reference:'BG-123',status:'awaiting_verification',revision:2,site:'B',landmark:'Drain',photos:[],prediction:null};assert.equal(parseReport(value).prediction,null);assert.deepEqual(parseReport(value).work_items,[]);});
