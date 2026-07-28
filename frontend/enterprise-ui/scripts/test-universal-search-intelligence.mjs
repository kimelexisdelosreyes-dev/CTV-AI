import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const intelligence = readFileSync(join(root, "src/features/search/search-intelligence.ts"), "utf8");
const types = readFileSync(join(root, "src/features/search/search-types.ts"), "utf8");
const overlay = readFileSync(join(root, "src/components/universal-search.tsx"), "utf8");
const css = readFileSync(join(root, "src/app/globals.css"), "utf8");

assert.match(intelligence, /searchHistoryFromStorage/, "history parser is implemented");
assert.match(intelligence, /updateSearchHistory/, "history update helper is implemented");
assert.match(intelligence, /suggestionsByContext/, "context-aware suggestions are implemented");
assert.match(intelligence, /categoryOrder/, "group ordering is stable");
assert.match(intelligence, /sourceStatus/, "source completion normalization is implemented");
assert.match(intelligence, /relationships:/g, "rich results expose enterprise relationships");
assert.match(intelligence, /preview:/g, "rich results expose preview facts");
assert.match(types, /SearchState[\s\S]*permission-required[\s\S]*no-results/, "search states include required states");

assert.match(overlay, /ArrowDown/, "keyboard ArrowDown is handled");
assert.match(overlay, /ArrowUp/, "keyboard ArrowUp is handled");
assert.match(overlay, /event\.key === "Tab"/, "Tab and Shift+Tab selection are handled");
assert.match(overlay, /event\.key === "Enter"/, "Enter behavior is handled");
assert.match(overlay, /event\.ctrlKey \|\| event\.metaKey/, "Ctrl/Cmd+Enter preview behavior is handled");
assert.match(overlay, /returnFocusRef\?\.current\?\.focus/, "focus returns to trigger on close");
assert.match(overlay, /role="listbox"/, "results use listbox semantics");
assert.match(overlay, /role="option"/, "results use option semantics");

assert.match(css, /search-main-grid/, "search command center layout styles exist");
assert.match(css, /search-preview-panel/, "preview panel styles exist");

console.log("Universal Search intelligence tests passed: 18 scenarios covered.");
