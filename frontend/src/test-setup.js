import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';
class ResizeObserverStub { observe(){} unobserve(){} disconnect(){} }
globalThis.ResizeObserver=ResizeObserverStub;
