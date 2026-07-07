import { describe, it, expect, afterEach, vi } from 'vitest';
import { isNetworkError } from './api.js';

describe('isNetworkError', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('returns false for null/undefined', () => {
    expect(isNetworkError(null)).toBe(false);
    expect(isNetworkError(undefined)).toBe(false);
  });

  it('treats a fetch TypeError ("Failed to fetch") as a network error', () => {
    const err = new TypeError('Failed to fetch');
    expect(isNetworkError(err)).toBe(true);
  });

  it('treats status 0 as a network error', () => {
    const err = Object.assign(new Error('boom'), { status: 0 });
    expect(isNetworkError(err)).toBe(true);
  });

  it('does NOT treat a real 4xx/5xx server response as a network error', () => {
    const err404 = Object.assign(new Error('Not found'), { status: 404 });
    const err500 = Object.assign(new Error('Server error'), { status: 500 });
    expect(isNetworkError(err404)).toBe(false);
    expect(isNetworkError(err500)).toBe(false);
  });

  it('treats navigator.onLine === false as a network error regardless of error shape', () => {
    vi.stubGlobal('navigator', { onLine: false });
    const err = Object.assign(new Error('anything'), { status: 500 });
    expect(isNetworkError(err)).toBe(true);
  });
});
