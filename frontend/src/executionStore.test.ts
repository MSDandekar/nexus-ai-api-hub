import {
  getExecutionState,
  getFormState,
  startExecution,
  setExecutionSuccess,
  setExecutionError,
  clearExecution,
  setFormValue,
  ensureFormDefaults,
} from './executionStore';

function assert(condition: boolean, msg: string) {
  if (!condition) {
    console.error(`FAIL: ${msg}`);
    throw new Error(`FAIL: ${msg}`);
  }
  console.log(`PASS: ${msg}`);
}

console.log("=== RUNNING EXECUTION STORE PERSISTENCE TESTS ===");

const slugA = "article-intelligence";
const slugB = "card-scanner";
const slugCustom = "custom-future-connector-" + Date.now();

// 1. Initial state is empty
assert(getExecutionState(slugA).result === null, "Initial execution result for slugA is null");
assert(getExecutionState(slugA).error === null, "Initial error for slugA is null");
assert(getExecutionState(slugA).loading === false, "Initial loading for slugA is false");

// 2. Initialize form defaults
ensureFormDefaults(slugA, [
  { name: "article_text", type: "text", default_value: "Sample Article" },
  { name: "include_sentiment", type: "boolean", default_value: true },
]);
assert(getFormState(slugA).values["article_text"] === "Sample Article", "Form defaults initialized");

// 3. User executes API test
startExecution(slugA);
assert(getExecutionState(slugA).loading === true, "Execution starts in loading state");
assert(getExecutionState(slugA).result === null, "No previous result before first run");

// 4. API returns success
const run1Result = { status: 200, ok: true, data: { summary: "Great article", word_count: 50 } };
setExecutionSuccess(slugA, run1Result);
assert(getExecutionState(slugA).loading === false, "Loading finishes on success");
assert(getExecutionState(slugA).result === run1Result, "Result 1 is displayed");
assert(getExecutionState(slugA).error === null, "Error is null on success");

// 5. Input change does NOT clear previous result
setFormValue(slugA, "article_text", "Modified text that has not been executed yet");
assert(getFormState(slugA).values["article_text"] === "Modified text that has not been executed yet", "Form updated with unsaved value");
assert(getExecutionState(slugA).result === run1Result, "Execution result 1 PERSISTS despite input change");
assert(getExecutionState(slugA).loading === false, "Execution loading state untouched by input change");

// 6. Background refresh / ensureFormDefaults does NOT reset result or form
ensureFormDefaults(slugA, [{ name: "article_text", type: "text", default_value: "Original" }]);
assert(getExecutionState(slugA).result === run1Result, "Execution result PERSISTS across connector refresh");
assert(getFormState(slugA).values["article_text"] === "Modified text that has not been executed yet", "Form state PERSISTS across connector refresh");

// 7. Starting a new execution does NOT clear previous result
startExecution(slugA);
assert(getExecutionState(slugA).loading === true, "Second execution is loading");
assert(getExecutionState(slugA).result === run1Result, "Previous result 1 REMAINS VISIBLE during in-flight request");

// 8. Second execution succeeds and replaces old result
const run2Result = { status: 200, ok: true, data: { summary: "Updated summary", word_count: 75 } };
setExecutionSuccess(slugA, run2Result);
assert(getExecutionState(slugA).loading === false, "Second execution finished");
assert(getExecutionState(slugA).result === run2Result, "Result is replaced with run 2");

// 9. Independent connector B execution isolation
startExecution(slugB);
const runBResult = { status: 200, ok: true, data: { name: "John Doe", company: "Acme" } };
setExecutionSuccess(slugB, runBResult);
assert(getExecutionState(slugB).result === runBResult, "Connector B has its own result");
assert(getExecutionState(slugA).result === run2Result, "Connector A result remains intact while Connector B executes");

// 10. Execution failure updates/replaces result with error
startExecution(slugA);
setExecutionError(slugA, "Provider rate limit exceeded", { status: 429, ok: false, data: { error: "Too Many Requests" } });
assert(getExecutionState(slugA).loading === false, "Failed execution finished loading");
assert(getExecutionState(slugA).error === "Provider rate limit exceeded", "Error message recorded");
assert(getExecutionState(slugA).result?.status === 429, "Result updated with failure details");

// 11. Changing inputs still does NOT clear the error
setFormValue(slugA, "article_text", "Another edit");
assert(getExecutionState(slugA).error === "Provider rate limit exceeded", "Error PERSISTS despite input changes");

// 12. Explicit Clear Output removes displayed result and error
clearExecution(slugA);
assert(getExecutionState(slugA).result === null, "Result is null after Clear Output");
assert(getExecutionState(slugA).error === null, "Error is null after Clear Output");
assert(getExecutionState(slugB).result === runBResult, "Connector B result still preserved after clearing Connector A");

// 13. Dynamic future connector test (zero connector-specific conditions)
ensureFormDefaults(slugCustom, [{ name: "dynamic_field", type: "text", default_value: "auto" }]);
startExecution(slugCustom);
const customResult = { status: 200, ok: true, data: { custom_output: "generated" } };
setExecutionSuccess(slugCustom, customResult);
setFormValue(slugCustom, "dynamic_field", "user typed something new");
assert(getExecutionState(slugCustom).result === customResult, "Dynamic connector output persists across input updates");

console.log("=== ALL 13 TEST SCENARIOS PASSED SUCCESSFULLY ===");
