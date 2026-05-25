import { readdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

const heroRoot = join(process.cwd(), "public", "hero");
const folders = ["villages", "nul-campus", "lines"];
const imagePattern = /\.(avif|gif|jpe?g|jpg\.jpeg|png|webp)$/i;

const manifest = {};

for (const folder of folders) {
  try {
    const entries = await readdir(join(heroRoot, folder), { withFileTypes: true });
    manifest[folder] = entries
      .filter((entry) => entry.isFile() && imagePattern.test(entry.name))
      .map((entry) => entry.name)
      .sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }));
  } catch {
    manifest[folder] = [];
  }
}

await writeFile(join(heroRoot, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
console.log("Generated hero image manifest", manifest);
