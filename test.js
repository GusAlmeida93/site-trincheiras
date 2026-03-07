const { JSDOM } = require("jsdom");
const fs = require("fs");
const fileContent = fs.readFileSync("script.js", "utf-8");
const dom = new JSDOM(`<!DOCTYPE html><html><head><script>window.supabase = { createClient: () => {} }</script></head><body><div id="enlist-avatar-grid"></div><button id="enlist-avatar-toggle"></button><div id="enlist-avatar-panel"></div><form id="enlist-form"></form><input id="enlist-name"/><input id="enlist-class"/></body></html>`, {
    runScripts: "dangerously",
    url: "http://localhost/",
    beforeParse(window) {
        window.matchMedia = () => ({ matches: false });
    }
});
try {
    dom.window.eval(fileContent);
    dom.window.eval("if(typeof renderEnlistAvatarOptions === 'function') renderEnlistAvatarOptions();");
    console.log("Successfully evaluated script.js and ran renderEnlistAvatarOptions.");
} catch (e) {
    console.error("Evaluation Error Name:", e.name);
    console.error("Evaluation Error Message:", e.message);
    console.error("Evaluation Error Stack:", e.stack);
}
