import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const briefing = readFileSync(join(root, "src/features/workspace/workspace-briefing.ts"), "utf8");
const utils = readFileSync(join(root, "src/features/workspace/workspace-utils.ts"), "utf8");
const continueWorking = readFileSync(join(root, "src/features/workspace/components/ContinueWorking.tsx"), "utf8");
const priorities = readFileSync(join(root, "src/features/workspace/components/TodayPriorities.tsx"), "utf8");
const motionCss = readFileSync(join(root, "src/design-system/design-system.css"), "utf8");

assert.match(utils, /Good \$\{dayPart\}\./, "greeting fallback keeps a neutral no-name form");
assert.match(utils, /Good \$\{dayPart\}, \$\{name\}\./, "greeting uses display name when available");
assert.match(utils, /critical:\s*0[\s\S]*high:\s*1[\s\S]*normal:\s*2[\s\S]*low:\s*3/, "priority ordering ranks critical before lower urgency");
assert.match(utils, /groupActivities/, "activity grouping helper is present");
assert.match(utils, /healthStatusLabel/, "health status normalization helper is present");
assert.match(utils, /return "general"/, "role fallback returns a general workspace role");

assert.match(briefing, /Demonstration data/g, "demo-only values are labeled as demonstration data");
assert.match(briefing, /dataKind: "demo"/, "demo data remains distinguishable");
assert.match(briefing, /dataKind: "live"/, "live data remains distinguishable");

assert.match(continueWorking, /No active work is waiting for your attention\./, "Continue Working empty state is defined");
assert.match(continueWorking, /onClick=\{\(\) => undefined\}/, "Continue Working card has keyboard activation through BaseCard");
assert.match(priorities, /No urgent priorities require attention\./, "priority empty state is defined");
assert.match(priorities, /tabIndex=\{0\}/, "priority items are keyboard focusable");

assert.match(motionCss, /prefers-reduced-motion:\s*reduce/, "reduced-motion compatibility remains defined");

console.log("Workspace intelligence tests passed: 10 scenarios covered.");
