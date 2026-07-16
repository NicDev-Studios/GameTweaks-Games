import { createHash } from 'node:crypto';
import { readdir, readFile, lstat } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import process from 'node:process';
import { fileURLToPath, URL } from 'node:url';

const rootArgument = process.argv.indexOf('--catalog-root');
const catalogRoot = rootArgument === -1
  ? fileURLToPath(new URL('../', import.meta.url))
  : resolve(process.argv[rootArgument + 1] ?? '');
if (rootArgument !== -1 && !process.argv[rootArgument + 1]) {
  throw new Error('Missing value for --catalog-root');
}
const gamesRoot = join(catalogRoot, 'games');
const entries = await readdir(gamesRoot, { withFileTypes: true });
const sourcePattern = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$/;
const releasePartPattern = /^[A-Za-z0-9._+-]+$/;
const commitPattern = /^[a-f0-9]{40}$/;
const workflowPattern = /^\.github\/workflows\/[A-Za-z0-9._-]+\.ya?ml$/;

function validateSource(definition, expected) {
  const source = definition.source;
  if (definition.official && !source) {
    throw new Error(`Official mod has no source provenance in ${expected}`);
  }
  if (!source) return;
  if (!sourcePattern.test(source.repository) ||
      !releasePartPattern.test(source.tag) || source.tag.length > 180 ||
      !commitPattern.test(source.commit) ||
      !workflowPattern.test(source.workflow) || source.workflow.length > 180 ||
      source.repository !== definition.release.repository ||
      source.tag !== definition.release.tag) {
    throw new Error(`Invalid source provenance in ${expected}`);
  }
}

for (const entry of entries) {
  if (entry.name === '.gitkeep') continue;
  if (!entry.isDirectory() || !/^\d+$/.test(entry.name)) {
    throw new Error(`Invalid entry below games/: ${entry.name}`);
  }
  const gameRoot = join(gamesRoot, entry.name);
  const gamePath = join(gameRoot, 'game.json');
  const game = JSON.parse(await readFile(gamePath, 'utf8'));
  if (String(game.appId) !== entry.name) throw new Error(`App ID mismatch in ${entry.name}`);

  const referenced = new Set();
  for (const reference of game.mods) {
    const expected = `mods/${reference.modId}.json`;
    if (reference.file !== expected || referenced.has(expected)) {
      throw new Error(`Invalid or duplicate mod reference in ${entry.name}: ${reference.file}`);
    }
    referenced.add(expected);
    const definitionPath = join(gameRoot, expected);
    if ((await lstat(definitionPath)).isSymbolicLink()) throw new Error(`Symlink rejected: ${expected}`);
    const raw = await readFile(definitionPath);
    const digest = createHash('sha256').update(raw).digest('hex');
    if (digest !== reference.sha256.toLowerCase()) throw new Error(`Digest mismatch: ${expected}`);
    const definition = JSON.parse(raw);
    if (definition.modId !== reference.modId) throw new Error(`Mod ID mismatch: ${expected}`);
    const release = definition.release;
    if (!release || !sourcePattern.test(release.repository) ||
        !releasePartPattern.test(release.tag) || release.tag.length > 180 ||
        !/^[A-Za-z0-9._+-]+\.zip$/.test(release.asset) || release.asset.length > 180 ||
        !/^[a-f0-9]{64}$/.test(release.sha256)) {
      throw new Error(`Invalid upstream release in ${expected}`);
    }
    validateSource(definition, expected);
  }

  const modsRoot = join(gameRoot, 'mods');
  const modFiles = await readdir(modsRoot, { withFileTypes: true }).catch((error) => {
    if (error.code === 'ENOENT' && referenced.size === 0) return [];
    throw error;
  });
  for (const modFile of modFiles) {
    const relative = `mods/${modFile.name}`;
    if (!modFile.isFile() || !referenced.has(relative)) throw new Error(`Unreferenced mod file: ${relative}`);
  }
}

process.stdout.write(
  `Validated ${entries.filter((entry) => entry.isDirectory()).length} game definition(s).\n`
);
