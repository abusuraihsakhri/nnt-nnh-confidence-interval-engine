"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { calculate, batchFromCSV, parseCSV } = require("../app.js");

test("NNT benchmark and Python parity", () => {
  const r = calculate({control_events:120, control_total:1000, treatment_events:80, treatment_total:1000},0.95);
  assert.equal(r.measure,"NNT");
  assert.equal(r.number_needed_rounded_up,25);
  assert.ok(Math.abs(r.risk_difference_ci[0] - 0.013718313895640582) < 1e-12);
  assert.ok(Math.abs(r.risk_difference_ci[1] - 0.06644947071003807) < 1e-12);
  assert.equal(r.ci_crosses_zero,false);
});
test("NNH for adverse increase", () => {
  const r = calculate({control_events:80,control_total:1000,treatment_events:120,treatment_total:1000},0.95);
  assert.equal(r.measure,"NNH");
  assert.equal(r.number_needed_rounded_up,25);
});
test("Crossing zero means no finite NNT interval", () => {
  const r = calculate({control_events:11,control_total:100,treatment_events:10,treatment_total:100},0.95);
  assert.equal(r.number_needed_ci,null);
  assert.equal(r.ci_crosses_zero,true);
});
test("Zero difference, zero group risk, complete separation", () => {
  const equal = calculate({control_events:0,control_total:100,treatment_events:0,treatment_total:100});
  assert.equal(equal.measure,"no_difference");
  assert.equal(equal.number_needed,null);
  assert.equal(equal.relative_risk,null);
  const separated = calculate({control_events:100,control_total:100,treatment_events:0,treatment_total:100});
  assert.equal(separated.number_needed,1);
  assert.ok(separated.number_needed_ci);
});
test("Reject invalid counts / unsupported confidence", () => {
  for (const values of [[101,100,0,100],[0,0,0,100],[0,100,-1,100],[.3,100,1,100]]) {
    assert.throws(() => calculate({control_events:values[0],control_total:values[1],treatment_events:values[2],treatment_total:values[3]}));
  }
  assert.throws(() => calculate({control_events:1,control_total:10,treatment_events:0,treatment_total:10}, 0.92));
});
test("Parser handles quoted delimiters and newlines", () => {
  assert.deepEqual(parseCSV('id,events\r\n"A, B",2\r\n"C\nD",3\r\n'),
    [["id","events"],["A, B","2"],["C\nD","3"]]);
  assert.throws(() => parseCSV('id\n"not closed'));
});
test("Batch exports correct results and escapes spreadsheet formulas", () => {
  const csv = 'study_id,control_events,control_total,treatment_events,treatment_total\n"=HYPERLINK(""x"")",12,100,8,100\n';
  const out = batchFromCSV(csv,0.95);
  const rows = parseCSV(out);
  assert.equal(rows.length,2);
  assert.equal(rows[1][0],"'=HYPERLINK(\"x\")");
  const headers=rows[0];
  assert.equal(rows[1][headers.indexOf("number_needed_rounded_up")],"25");
});
test("Invalid batch row fails, no partial CSV", () => {
  assert.throws(() => batchFromCSV("control_events,control_total,treatment_events,treatment_total\n1,0,0,10\n"));
});
