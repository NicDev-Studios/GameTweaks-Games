import { createHash } from 'node:crypto';
import { readdir, readFile, lstat } from 'node:fs/promises';
import { join } from 'node:path';
import process from 'node:process';
import { fileURLToPath, URL } from 'node:url';

const gamesRoot = fileURLToPath(new URL('../games/', import.meta.url));
const entries = await readdir(gamesRoot, { withFileTypes: true });

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
  }

  const modsRoot = join(gameRoot, 'mods');
  const modFiles = await readdir(modsRoot, { withFileTypes: true });
  for (const modFile of modFiles) {
    const relative = `mods/${modFile.name}`;
    if (!modFile.isFile() || !referenced.has(relative)) throw new Error(`Unreferenced mod file: ${relative}`);
  }
}

process.stdout.write(
  `Validated ${entries.filter((entry) => entry.isDirectory()).length} game definition(s).\n`
);
