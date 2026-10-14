import js from '@eslint/js';
import ts from 'typescript-eslint';
export default [
  { ignores: ['**/dist/**', '**/.astro/**', '**/public/**', '**/*.astro'] },
  js.configs.recommended,
  ...ts.configs.recommended,
  { languageOptions: { globals: { console: 'readonly', process: 'readonly', Buffer: 'readonly', URL: 'readonly', fetch: 'readonly', window: 'readonly', document: 'readonly', localStorage: 'readonly', CustomEvent: 'readonly', HTMLElement: 'readonly', HTMLInputElement: 'readonly', KeyboardEvent: 'readonly', StorageEvent: 'readonly', Request: 'readonly', Response: 'readonly', setTimeout: 'readonly' } } },
];
