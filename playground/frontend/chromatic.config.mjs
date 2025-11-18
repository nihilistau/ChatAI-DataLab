import path from 'node:path';

if (!process.env.CHROMATIC_PROJECT_TOKEN) {
  throw new Error(
    'Set CHROMATIC_PROJECT_TOKEN in your environment before running Chromatic snapshots.'
  );
}

export default {
  projectToken: process.env.CHROMATIC_PROJECT_TOKEN,
  buildScriptName: 'storybook:playground',
  storybookBaseDir: path.resolve(process.cwd()),
  exitOnceUploaded: true,
  exitZeroOnChanges: true,
  diagnosticsMode: true,
};
