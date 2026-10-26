// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';
import { TextDecoder, TextEncoder } from 'util';

// react-router 7 は TextEncoder / TextDecoder を使うが、
// CRA のテストで使うブラウザの代わり（jsdom）には入っていない
// → テストのときだけ、Node.js のものを使えるようにする（本物のブラウザには最初からある）
Object.assign(global, { TextDecoder, TextEncoder });
